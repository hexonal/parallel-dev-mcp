"""Session Coordinator MCP服务器

提供会话协调的核心MCP工具，实现主子会话间的通信和状态管理，包含完整的tmux集成功能。
"""

import json
import logging
import subprocess
import shlex
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import defaultdict

# 注意: 这里使用假设的MCP装饰器，实际实现需要根据FastMCP 2.0的具体API调整
try:
    from fastmcp import mcp_tool, MCPServer
except ImportError:
    # 开发阶段的模拟装饰器
    def mcp_tool(name: str = None, description: str = None):
        def decorator(func):
            func._mcp_tool_name = name or func.__name__
            func._mcp_tool_description = description
            return func
        return decorator
    
    class MCPServer:
        def __init__(self, name: str):
            self.name = name

from .session_models import (
    SessionRelationship, SessionStatus, Message, SessionCoordinatorState,
    SessionStatusEnum, MessageType
)
from .session_utils import (
    parse_session_name, validate_session_name, generate_message_id,
    validate_status_transition, calculate_session_health_score
)


class SessionCoordinatorMCP:
    """MCP Session Coordinator服务器实现，集成tmux管理功能"""
    
    def __init__(self, name: str = "session-coordinator"):
        self.server = MCPServer(name)
        self.state = SessionCoordinatorState()
        self.logger = self._setup_logging()
        self.max_message_age_hours = 24  # 消息保留24小时
        self.max_messages_per_session = 100  # 每个会话最多保留100条消息
    
    def _setup_logging(self) -> logging.Logger:
        """设置日志"""
        logger = logging.getLogger("session_coordinator_mcp")
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    # ========== 统一的会话创建和管理工具 ==========
    
    @mcp_tool(
        name="create_development_session",
        description="创建并配置开发会话，包括tmux会话创建和MCP关系注册"
    )
    def create_development_session(
        self,
        session_type: str,
        project_id: str,
        task_id: str = None,
        working_directory: str = None
    ) -> str:
        """创建开发会话
        
        Args:
            session_type: 会话类型 ("master" 或 "child")
            project_id: 项目ID
            task_id: 任务ID (子会话必需)
            working_directory: 工作目录 (默认为当前目录)
            
        Returns:
            创建结果的JSON字符串
        """
        try:
            # 🛡️ 安全检查：防止子会话创建嵌套会话
            caller_check = self._check_caller_permissions("create_session")
            if not caller_check["allowed"]:
                return json.dumps({
                    "success": False,
                    "error": caller_check["reason"],
                    "security_violation": True,
                    "caller_info": {
                        "session": caller_check.get("caller_session"),
                        "type": caller_check.get("caller_type"),
                        "operation": caller_check.get("operation")
                    }
                })
            
            # 验证参数
            if session_type not in ["master", "child"]:
                return json.dumps({
                    "success": False,
                    "error": f"无效的会话类型: {session_type}。必须是 'master' 或 'child'"
                })
            
            if session_type == "child" and not task_id:
                return json.dumps({
                    "success": False,
                    "error": "子会话必须指定task_id"
                })
            
            # 设置工作目录
            if not working_directory:
                working_directory = os.getcwd()
            
            # 生成会话名称
            if session_type == "master":
                session_name = f"master_project_{project_id}"
            else:
                session_name = f"child_{project_id}_task_{task_id}"
            
            # 检查会话是否已存在
            if self._tmux_session_exists(session_name):
                return json.dumps({
                    "success": False,
                    "error": f"tmux会话已存在: {session_name}"
                })
            
            # 创建tmux会话
            tmux_result = self._create_tmux_session(
                session_name=session_name,
                working_directory=working_directory,
                session_type=session_type,
                project_id=project_id,
                task_id=task_id
            )
            
            if not tmux_result["success"]:
                return json.dumps(tmux_result)
            
            # 注册MCP会话关系
            mcp_result = self._register_session_for_tmux(
                session_name=session_name,
                session_type=session_type,
                project_id=project_id,
                task_id=task_id
            )
            
            # 合并结果
            result = {
                "success": True,
                "session_name": session_name,
                "session_type": session_type,
                "project_id": project_id,
                "task_id": task_id,
                "tmux_info": tmux_result,
                "mcp_registration": mcp_result,
                "connect_command": f"tmux attach-session -t {session_name}"
            }
            
            self.logger.info(f"创建开发会话成功: {session_name} ({session_type})")
            
            return json.dumps(result, indent=2)
            
        except Exception as e:
            error_msg = f"创建开发会话失败: {str(e)}"
            self.logger.error(error_msg)
            return json.dumps({"success": False, "error": error_msg})
    
    @mcp_tool(
        name="terminate_session",
        description="终止会话，清理tmux会话和MCP状态"
    )
    def terminate_session(self, session_name: str) -> str:
        """终止会话
        
        Args:
            session_name: 会话名称
            
        Returns:
            终止结果的JSON字符串
        """
        try:
            # 🛡️ 安全检查：防止子会话终止其他会话
            caller_check = self._check_caller_permissions("terminate_session")
            if not caller_check["allowed"]:
                return json.dumps({
                    "success": False,
                    "error": caller_check["reason"],
                    "security_violation": True,
                    "caller_info": {
                        "session": caller_check.get("caller_session"),
                        "type": caller_check.get("caller_type"),
                        "operation": caller_check.get("operation")
                    }
                })
            
            # 清理MCP状态
            mcp_cleanup = self._cleanup_mcp_session(session_name)
            
            # 终止tmux会话
            tmux_cleanup = self._kill_tmux_session(session_name)
            
            result = {
                "success": True,
                "session_name": session_name,
                "mcp_cleanup": mcp_cleanup,
                "tmux_cleanup": tmux_cleanup
            }
            
            self.logger.info(f"会话终止完成: {session_name}")
            
            return json.dumps(result, indent=2)
            
        except Exception as e:
            error_msg = f"终止会话失败: {str(e)}"
            self.logger.error(error_msg)
            return json.dumps({"success": False, "error": error_msg})
    
    @mcp_tool(
        name="get_session_terminal_info",
        description="获取会话的终端和tmux详细信息"
    )
    def get_session_terminal_info(self, session_name: str = None) -> str:
        """获取会话终端信息
        
        Args:
            session_name: 会话名称，为空时返回所有MCP管理的会话
            
        Returns:
            会话终端信息的JSON字符串
        """
        try:
            if session_name:
                # 查询单个会话
                tmux_info = self._get_tmux_session_info(session_name)
                mcp_info = self._get_mcp_session_info(session_name)
                
                result = {
                    "session_name": session_name,
                    "tmux_info": tmux_info,
                    "mcp_info": mcp_info,
                    "connect_command": f"tmux attach-session -t {session_name}" if tmux_info.get("exists") else None
                }
            else:
                # 查询所有会话
                all_sessions = list(self.state.active_sessions.keys())
                result = {
                    "total_sessions": len(all_sessions),
                    "sessions": {}
                }
                
                for name in all_sessions:
                    tmux_info = self._get_tmux_session_info(name)
                    mcp_info = self._get_mcp_session_info(name)
                    
                    result["sessions"][name] = {
                        "tmux_info": tmux_info,
                        "mcp_info": mcp_info,
                        "connect_command": f"tmux attach-session -t {name}" if tmux_info.get("exists") else None
                    }
            
            return json.dumps(result, indent=2)
            
        except Exception as e:
            error_msg = f"获取会话终端信息失败: {str(e)}"
            self.logger.error(error_msg)
            return json.dumps({"success": False, "error": error_msg})
    
    # ========== 传统的会话注册和关系管理 (保留兼容性) ==========
    
    @mcp_tool(
        name="register_session_relationship",
        description="注册主子会话的关系，建立会话间的通信链路"
    )
    def register_session_relationship(
        self, 
        parent_session: str, 
        child_session: str, 
        task_id: str,
        project_id: str = None
    ) -> str:
        """注册会话关系
        
        Args:
            parent_session: 父会话名称
            child_session: 子会话名称  
            task_id: 任务ID
            project_id: 项目ID (可选，会从会话名称解析)
            
        Returns:
            注册结果消息
        """
        try:
            # 验证会话名称格式
            parent_valid, parent_error = validate_session_name(parent_session)
            if not parent_valid:
                return f"父会话名称无效: {parent_error}"
            
            child_valid, child_error = validate_session_name(child_session)
            if not child_valid:
                return f"子会话名称无效: {child_error}"
            
            # 解析会话信息
            parent_info = parse_session_name(parent_session)
            child_info = parse_session_name(child_session)
            
            if not parent_info or parent_info["role"] != "master":
                return f"父会话必须是master类型: {parent_session}"
            
            if not child_info or child_info["role"] != "child":
                return f"子会话必须是child类型: {child_session}"
            
            # 验证项目ID一致性
            if parent_info["project_id"] != child_info["project_id"]:
                return f"父子会话的project_id不一致: {parent_info['project_id']} != {child_info['project_id']}"
            
            # 创建关系记录
            relationship = SessionRelationship(
                parent_session=parent_session,
                child_session=child_session,
                task_id=task_id,
                project_id=child_info["project_id"]
            )
            
            self.state.session_relationships[child_session] = relationship
            
            # 初始化消息队列
            if child_session not in self.state.session_messages:
                self.state.session_messages[child_session] = []
            if parent_session not in self.state.session_messages:
                self.state.session_messages[parent_session] = []
            
            self.logger.info(f"注册会话关系: {child_session} -> {parent_session} (任务: {task_id})")
            
            return f"会话关系注册成功: {child_session} -> {parent_session} (任务: {task_id})"
            
        except Exception as e:
            error_msg = f"注册会话关系失败: {str(e)}"
            self.logger.error(error_msg)
            return error_msg
    
    # ========== 会话状态管理 ==========
    
    @mcp_tool(
        name="report_session_status",
        description="子会话上报状态，自动路由到父会话"
    )
    def report_session_status(
        self,
        session_name: str,
        status: str,
        progress: int = 0,
        details: str = ""
    ) -> str:
        """报告会话状态
        
        Args:
            session_name: 会话名称
            status: 状态值
            progress: 进度百分比 (0-100)
            details: 详细信息
            
        Returns:
            处理结果消息
        """
        try:
            # 验证状态值
            try:
                status_enum = SessionStatusEnum(status)
            except ValueError:
                return f"无效的状态值: {status}。有效值: {[s.value for s in SessionStatusEnum]}"
            
            # 验证进度范围
            if not (0 <= progress <= 100):
                return f"进度值必须在0-100之间: {progress}"
            
            # 检查状态转换合法性
            current_session = self.state.active_sessions.get(session_name)
            if current_session:
                valid, error_msg = validate_status_transition(
                    current_session.status, status_enum
                )
                if not valid:
                    self.logger.warning(f"状态转换警告: {error_msg}")
            
            # 更新会话状态
            session_status = SessionStatus(
                session_name=session_name,
                status=status_enum,
                progress=progress,
                details=details
            )
            
            self.state.active_sessions[session_name] = session_status
            
            # 如果是子会话且状态重要，自动通知父会话
            if status_enum in [SessionStatusEnum.COMPLETED, SessionStatusEnum.BLOCKED, SessionStatusEnum.ERROR]:
                parent_session = self.state.get_parent_session(session_name)
                if parent_session:
                    message_content = {
                        "type": "STATUS_NOTIFICATION",
                        "child_session": session_name,
                        "status": status,
                        "progress": progress,
                        "details": details,
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    self._send_internal_message(
                        from_session=session_name,
                        to_session=parent_session,
                        message_type=MessageType.STATUS_UPDATE,
                        content=json.dumps(message_content)
                    )
            
            self.logger.info(f"会话状态更新: {session_name} -> {status} ({progress}%)")
            
            return f"状态已更新: {session_name} -> {status} ({progress}%)"
            
        except Exception as e:
            error_msg = f"状态上报失败: {str(e)}"
            self.logger.error(error_msg)
            return error_msg
    
    # ========== 会话查询功能 ==========
    
    @mcp_tool(
        name="get_child_sessions",
        description="主会话获取所有子会话的状态信息"
    )
    def get_child_sessions(self, parent_session: str) -> str:
        """获取子会话列表和状态
        
        Args:
            parent_session: 父会话名称
            
        Returns:
            JSON格式的子会话列表
        """
        try:
            children = self.state.get_child_sessions(parent_session)
            
            result = []
            for child_session in children:
                child_status = self.state.active_sessions.get(child_session)
                relationship = self.state.session_relationships.get(child_session)
                
                child_info = {
                    "session_name": child_session,
                    "task_id": relationship.task_id if relationship else "unknown",
                    "status": child_status.status.value if child_status else "UNKNOWN",
                    "progress": child_status.progress if child_status else 0,
                    "details": child_status.details if child_status else "",
                    "last_update": child_status.last_update.isoformat() if child_status else "",
                    "health_score": calculate_session_health_score(
                        child_status.to_dict() if child_status else {}
                    )
                }
                result.append(child_info)
            
            self.logger.info(f"查询子会话: {parent_session} -> {len(result)}个子会话")
            
            return json.dumps({
                "parent_session": parent_session,
                "child_count": len(result),
                "children": result,
                "query_time": datetime.now().isoformat()
            }, indent=2)
            
        except Exception as e:
            error_msg = f"查询子会话失败: {str(e)}"
            self.logger.error(error_msg)
            return json.dumps({"error": error_msg})
    
    @mcp_tool(
        name="query_session_status", 
        description="查询指定会话或所有会话的状态"
    )
    def query_session_status(self, session_name: str = None) -> str:
        """查询会话状态
        
        Args:
            session_name: 会话名称，为空时返回所有会话状态
            
        Returns:
            JSON格式的状态信息
        """
        try:
            if session_name:
                # 查询单个会话
                session_status = self.state.active_sessions.get(session_name)
                if not session_status:
                    return json.dumps({"error": f"会话不存在: {session_name}"})
                
                result = session_status.to_dict()
                result["health_score"] = calculate_session_health_score(result)
                
            else:
                # 查询所有会话
                result = {
                    "total_sessions": len(self.state.active_sessions),
                    "sessions": {}
                }
                
                for name, status in self.state.active_sessions.items():
                    status_dict = status.to_dict()
                    status_dict["health_score"] = calculate_session_health_score(status_dict)
                    result["sessions"][name] = status_dict
            
            return json.dumps(result, indent=2)
            
        except Exception as e:
            error_msg = f"查询会话状态失败: {str(e)}"
            self.logger.error(error_msg)
            return json.dumps({"error": error_msg})
    
    # ========== 会话消息传递 ==========
    
    @mcp_tool(
        name="send_message_to_session",
        description="向指定会话发送消息"
    )
    def send_message_to_session(
        self,
        from_session: str,
        to_session: str, 
        message: str,
        message_type: str = "INSTRUCTION"
    ) -> str:
        """发送消息到指定会话
        
        Args:
            from_session: 发送方会话
            to_session: 接收方会话
            message: 消息内容
            message_type: 消息类型
            
        Returns:
            发送结果
        """
        try:
            # 验证消息类型
            try:
                msg_type = MessageType(message_type)
            except ValueError:
                return f"无效的消息类型: {message_type}。有效值: {[t.value for t in MessageType]}"
            
            result = self._send_internal_message(from_session, to_session, msg_type, message)
            
            self.logger.info(f"消息发送: {from_session} -> {to_session} ({message_type})")
            
            return result
            
        except Exception as e:
            error_msg = f"消息发送失败: {str(e)}"
            self.logger.error(error_msg)
            return error_msg
    
    @mcp_tool(
        name="get_session_messages",
        description="获取发给当前会话的未读消息"
    )
    def get_session_messages(self, session_name: str) -> str:
        """获取会话消息
        
        Args:
            session_name: 会话名称
            
        Returns:
            JSON格式的消息列表
        """
        try:
            messages = self.state.session_messages.get(session_name, [])
            unread_messages = [msg for msg in messages if not msg.is_read]
            
            # 标记消息为已读
            for msg in unread_messages:
                msg.is_read = True
            
            result = {
                "session_name": session_name,
                "unread_count": len(unread_messages),
                "messages": [msg.to_dict() for msg in unread_messages],
                "query_time": datetime.now().isoformat()
            }
            
            self.logger.info(f"获取消息: {session_name} -> {len(unread_messages)}条未读")
            
            return json.dumps(result, indent=2)
            
        except Exception as e:
            error_msg = f"获取消息失败: {str(e)}"
            self.logger.error(error_msg)
            return json.dumps({"error": error_msg})
    
    # ========== tmux内部操作方法 ==========
    
    def _tmux_session_exists(self, session_name: str) -> bool:
        """检查tmux会话是否存在"""
        try:
            result = subprocess.run(
                ["tmux", "has-session", "-t", session_name],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def _create_tmux_session(
        self,
        session_name: str,
        working_directory: str,
        session_type: str,
        project_id: str,
        task_id: str = None
    ) -> Dict[str, Any]:
        """创建tmux会话"""
        try:
            # 构建tmux创建命令
            cmd = [
                "tmux", "new-session", "-d",
                "-s", session_name,
                "-c", working_directory
            ]
            
            # 执行创建命令
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                return {
                    "success": False,
                    "error": f"tmux会话创建失败: {result.stderr}"
                }
            
            # 设置会话环境变量
            env_vars = {
                "MCP_SESSION_NAME": session_name,
                "MCP_SESSION_TYPE": session_type,
                "MCP_PROJECT_ID": project_id,
                "MCP_TASK_ID": task_id or "",
                "MCP_COORDINATOR_ACTIVE": "true"
            }
            
            for var_name, var_value in env_vars.items():
                if var_value:  # 只设置非空值
                    subprocess.run([
                        "tmux", "set-environment", "-t", session_name,
                        var_name, var_value
                    ])
            
            # 发送欢迎消息到会话
            welcome_msg = f"echo '🚀 MCP开发会话已启动: {session_name}'"
            subprocess.run([
                "tmux", "send-keys", "-t", session_name,
                welcome_msg, "C-m"
            ])
            
            return {
                "success": True,
                "session_name": session_name,
                "working_directory": working_directory,
                "environment_vars": env_vars
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"创建tmux会话异常: {str(e)}"
            }
    
    def _kill_tmux_session(self, session_name: str) -> Dict[str, Any]:
        """终止tmux会话"""
        try:
            if not self._tmux_session_exists(session_name):
                return {
                    "success": True,
                    "message": f"tmux会话不存在: {session_name}"
                }
            
            result = subprocess.run(
                ["tmux", "kill-session", "-t", session_name],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                return {
                    "success": False,
                    "error": f"终止tmux会话失败: {result.stderr}"
                }
            
            return {
                "success": True,
                "message": f"tmux会话已终止: {session_name}"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"终止tmux会话异常: {str(e)}"
            }
    
    def _get_tmux_session_info(self, session_name: str) -> Dict[str, Any]:
        """获取tmux会话信息"""
        try:
            if not self._tmux_session_exists(session_name):
                return {
                    "exists": False,
                    "session_name": session_name
                }
            
            # 获取会话基本信息
            result = subprocess.run([
                "tmux", "display-message", "-t", session_name, "-p",
                "#{session_name}:#{session_created}:#{session_windows}:#{session_attached}"
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                parts = result.stdout.strip().split(':')
                return {
                    "exists": True,
                    "session_name": parts[0],
                    "created_time": parts[1],
                    "window_count": int(parts[2]),
                    "attached": parts[3] == "1"
                }
            else:
                return {
                    "exists": False,
                    "error": result.stderr
                }
                
        except Exception as e:
            return {
                "exists": False,
                "error": str(e)
            }
    
    def _register_session_for_tmux(
        self,
        session_name: str,
        session_type: str,
        project_id: str,
        task_id: str = None
    ) -> Dict[str, Any]:
        """为tmux会话注册MCP关系"""
        try:
            if session_type == "master":
                # 主会话只需要初始化状态
                session_status = SessionStatus(
                    session_name=session_name,
                    status=SessionStatusEnum.STARTED,
                    progress=0,
                    details=f"主会话已启动，项目: {project_id}"
                )
                self.state.active_sessions[session_name] = session_status
                
                # 初始化消息队列
                if session_name not in self.state.session_messages:
                    self.state.session_messages[session_name] = []
                
                return {
                    "success": True,
                    "message": f"主会话已注册: {session_name}",
                    "session_type": "master"
                }
            else:
                # 子会话需要找到父会话并注册关系
                parent_session = f"master_project_{project_id}"
                
                # 如果父会话不存在，先创建父会话的MCP状态
                if parent_session not in self.state.active_sessions:
                    parent_status = SessionStatus(
                        session_name=parent_session,
                        status=SessionStatusEnum.STARTED,
                        progress=0,
                        details=f"自动创建的主会话，项目: {project_id}"
                    )
                    self.state.active_sessions[parent_session] = parent_status
                    if parent_session not in self.state.session_messages:
                        self.state.session_messages[parent_session] = []
                
                # 注册子会话关系
                relationship = SessionRelationship(
                    parent_session=parent_session,
                    child_session=session_name,
                    task_id=task_id,
                    project_id=project_id
                )
                
                self.state.session_relationships[session_name] = relationship
                
                # 初始化子会话状态
                session_status = SessionStatus(
                    session_name=session_name,
                    status=SessionStatusEnum.STARTED,
                    progress=0,
                    details=f"子会话已启动，任务: {task_id}"
                )
                self.state.active_sessions[session_name] = session_status
                
                # 初始化消息队列
                if session_name not in self.state.session_messages:
                    self.state.session_messages[session_name] = []
                
                return {
                    "success": True,
                    "message": f"子会话已注册: {session_name} -> {parent_session}",
                    "session_type": "child",
                    "parent_session": parent_session
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"注册MCP会话失败: {str(e)}"
            }
    
    def _cleanup_mcp_session(self, session_name: str) -> Dict[str, Any]:
        """清理MCP会话状态"""
        try:
            cleaned = []
            
            # 清理会话状态
            if session_name in self.state.active_sessions:
                del self.state.active_sessions[session_name]
                cleaned.append("session_status")
            
            # 清理会话关系
            if session_name in self.state.session_relationships:
                del self.state.session_relationships[session_name]
                cleaned.append("session_relationship")
            
            # 清理子会话关系（如果是父会话）
            children_to_remove = []
            for child_name, relationship in self.state.session_relationships.items():
                if relationship.parent_session == session_name:
                    children_to_remove.append(child_name)
            
            for child_name in children_to_remove:
                del self.state.session_relationships[child_name]
                if child_name in self.state.active_sessions:
                    del self.state.active_sessions[child_name]
                cleaned.append(f"child_session_{child_name}")
            
            # 清理消息队列
            if session_name in self.state.session_messages:
                message_count = len(self.state.session_messages[session_name])
                del self.state.session_messages[session_name]
                cleaned.append(f"messages_{message_count}")
            
            return {
                "success": True,
                "cleaned_items": cleaned,
                "children_removed": len(children_to_remove)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"清理MCP会话状态异常: {str(e)}"
            }
    
    def _get_mcp_session_info(self, session_name: str) -> Dict[str, Any]:
        """获取MCP会话信息"""
        try:
            info = {
                "session_registered": session_name in self.state.active_sessions,
                "has_relationship": session_name in self.state.session_relationships,
                "message_count": len(self.state.session_messages.get(session_name, []))
            }
            
            # 添加状态信息
            if session_name in self.state.active_sessions:
                status = self.state.active_sessions[session_name]
                info.update({
                    "status": status.status.value,
                    "progress": status.progress,
                    "last_update": status.last_update.isoformat(),
                    "details": status.details
                })
            
            # 添加关系信息
            if session_name in self.state.session_relationships:
                relationship = self.state.session_relationships[session_name]
                info.update({
                    "parent_session": relationship.parent_session,
                    "task_id": relationship.task_id,
                    "project_id": relationship.project_id
                })
            
            return info
            
        except Exception as e:
            return {
                "error": f"获取MCP会话信息异常: {str(e)}"
            }
    
    # ========== 安全和权限控制 ==========
    
    def _check_caller_permissions(self, operation: str) -> Dict[str, Any]:
        """检查调用者权限，防止会话嵌套和权限滥用
        
        Args:
            operation: 操作类型 ("create_session", "terminate_session")
            
        Returns:
            权限检查结果
        """
        try:
            # 检查当前环境是否在子会话中
            session_type = os.environ.get("MCP_SESSION_TYPE")
            session_name = os.environ.get("MCP_SESSION_NAME")
            
            if session_type == "child":
                # 子会话权限限制
                restricted_operations = ["create_session", "terminate_session"]
                
                if operation in restricted_operations:
                    self.logger.warning(
                        f"安全违规：子会话 {session_name} 尝试执行受限操作 {operation}"
                    )
                    return {
                        "allowed": False,
                        "reason": f"安全限制：子会话不能执行 {operation} 操作，防止会话嵌套和权限滥用",
                        "caller_session": session_name,
                        "caller_type": session_type,
                        "operation": operation
                    }
            
            # 检查会话深度（额外保护）
            if session_name and "child" in session_name and operation == "create_session":
                # 即使环境变量检查通过，也要防止深度嵌套
                return {
                    "allowed": False,
                    "reason": "安全限制：检测到潜在的会话嵌套，禁止从子会话创建新会话",
                    "caller_session": session_name,
                    "operation": operation
                }
            
            return {
                "allowed": True,
                "reason": "权限检查通过",
                "caller_session": session_name or "外部调用者",
                "caller_type": session_type or "external"
            }
            
        except Exception as e:
            # 权限检查异常时，默认允许（避免阻塞正常使用）
            self.logger.error(f"权限检查异常: {str(e)}")
            return {
                "allowed": True,
                "reason": "权限检查异常，默认允许",
                "error": str(e)
            }
    
    # ========== 内部辅助方法 ==========
    
    def _send_internal_message(
        self,
        from_session: str,
        to_session: str,
        message_type: MessageType,
        content: str
    ) -> str:
        """内部消息发送方法"""
        message = Message(
            message_id=generate_message_id(),
            from_session=from_session,
            to_session=to_session,
            message_type=message_type,
            content=content
        )
        
        if to_session not in self.state.session_messages:
            self.state.session_messages[to_session] = []
        
        self.state.session_messages[to_session].append(message)
        
        # 限制消息队列大小
        messages = self.state.session_messages[to_session]
        if len(messages) > self.max_messages_per_session:
            self.state.session_messages[to_session] = messages[-self.max_messages_per_session:]
        
        return f"消息已发送到 {to_session} (ID: {message.message_id})"
    
    def cleanup_old_data(self):
        """清理过期数据"""
        cutoff_time = datetime.now() - timedelta(hours=self.max_message_age_hours)
        
        # 清理过期消息
        total_removed = 0
        for session_name, messages in self.state.session_messages.items():
            original_count = len(messages)
            self.state.session_messages[session_name] = [
                msg for msg in messages if msg.created_at > cutoff_time
            ]
            removed = original_count - len(self.state.session_messages[session_name])
            total_removed += removed
        
        if total_removed > 0:
            self.logger.info(f"清理过期消息: {total_removed}条")
        
        self.state.last_cleanup = datetime.now()
    
    def get_server_stats(self) -> Dict[str, Any]:
        """获取服务器统计信息"""
        total_messages = sum(len(msgs) for msgs in self.state.session_messages.values())
        
        return {
            "active_relationships": len(self.state.session_relationships),
            "active_sessions": len(self.state.active_sessions),
            "total_messages": total_messages,
            "last_cleanup": self.state.last_cleanup.isoformat(),
            "uptime_seconds": (datetime.now() - self.state.last_cleanup).total_seconds()
        }
    
    # ========== 会话列表工具 ==========
    
    @mcp_tool(
        name="list_all_sessions",
        description="列出所有MCP管理的会话，包括tmux状态和会话关系"
    )
    def list_all_sessions(self) -> str:
        """列出所有会话
        
        Returns:
            所有会话的JSON格式列表，包括详细状态信息
        """
        try:
            # 获取所有MCP注册的会话
            mcp_sessions = list(self.state.active_sessions.keys())
            
            # 获取所有tmux会话
            tmux_sessions = self._get_all_tmux_sessions()
            
            # 合并会话列表
            all_sessions = set(mcp_sessions + tmux_sessions)
            
            result = {
                "total_sessions": len(all_sessions),
                "mcp_managed": len(mcp_sessions),
                "tmux_running": len(tmux_sessions),
                "sessions": []
            }
            
            for session_name in sorted(all_sessions):
                # 获取MCP信息
                mcp_info = self._get_mcp_session_info(session_name)
                
                # 获取tmux信息
                tmux_info = self._get_tmux_session_info(session_name)
                
                # 判断会话类型
                session_type = "unknown"
                if "master" in session_name:
                    session_type = "master"
                elif "child" in session_name:
                    session_type = "child"
                
                # 获取项目ID和任务ID
                project_id = "unknown"
                task_id = None
                
                if mcp_info.get("project_id"):
                    project_id = mcp_info["project_id"]
                    task_id = mcp_info.get("task_id")
                else:
                    # 从会话名称解析
                    import re
                    if session_type == "master":
                        match = re.match(r"master_project_(.+)", session_name)
                        if match:
                            project_id = match.group(1)
                    elif session_type == "child":
                        match = re.match(r"child_(.+)_task_(.+)", session_name)
                        if match:
                            project_id = match.group(1)
                            task_id = match.group(2)
                
                session_info = {
                    "session_name": session_name,
                    "session_type": session_type,
                    "project_id": project_id,
                    "task_id": task_id,
                    "mcp_status": {
                        "registered": mcp_info.get("session_registered", False),
                        "status": mcp_info.get("status", "UNKNOWN"),
                        "progress": mcp_info.get("progress", 0),
                        "details": mcp_info.get("details", ""),
                        "last_update": mcp_info.get("last_update", ""),
                        "message_count": mcp_info.get("message_count", 0),
                        "has_relationship": mcp_info.get("has_relationship", False)
                    },
                    "tmux_status": {
                        "exists": tmux_info.get("exists", False),
                        "created_time": tmux_info.get("created_time", ""),
                        "window_count": tmux_info.get("window_count", 0),
                        "attached": tmux_info.get("attached", False)
                    },
                    "connect_command": f"tmux attach-session -t {session_name}" if tmux_info.get("exists") else None
                }
                
                # 添加父子关系信息
                if session_type == "child" and mcp_info.get("parent_session"):
                    session_info["parent_session"] = mcp_info["parent_session"]
                elif session_type == "master":
                    # 查找子会话
                    children = self.state.get_child_sessions(session_name)
                    session_info["child_sessions"] = children
                    session_info["child_count"] = len(children)
                
                result["sessions"].append(session_info)
            
            # 添加统计信息
            master_count = sum(1 for s in result["sessions"] if s["session_type"] == "master")
            child_count = sum(1 for s in result["sessions"] if s["session_type"] == "child")
            active_count = sum(1 for s in result["sessions"] if s["tmux_status"]["exists"])
            
            result["statistics"] = {
                "master_sessions": master_count,
                "child_sessions": child_count,
                "unknown_sessions": len(result["sessions"]) - master_count - child_count,
                "active_tmux_sessions": active_count,
                "mcp_only_sessions": len(mcp_sessions) - active_count,
                "query_time": datetime.now().isoformat()
            }
            
            self.logger.info(f"列出所有会话: 总计{len(all_sessions)}个会话")
            
            return json.dumps(result, indent=2)
            
        except Exception as e:
            error_msg = f"列出会话失败: {str(e)}"
            self.logger.error(error_msg)
            return json.dumps({"success": False, "error": error_msg})
    
    def _get_all_tmux_sessions(self) -> List[str]:
        """获取所有tmux会话名称"""
        try:
            result = subprocess.run(
                ["tmux", "list-sessions", "-F", "#{session_name}"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                sessions = result.stdout.strip().split('\n')
                # 过滤掉空行
                return [s for s in sessions if s.strip()]
            else:
                return []
                
        except Exception as e:
            self.logger.error(f"获取tmux会话列表失败: {str(e)}")
            return []


# 创建全局实例
session_coordinator = SessionCoordinatorMCP()