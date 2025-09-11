"""Session Coordinator MCP服务器

提供会话协调的核心MCP工具，实现主子会话间的通信和状态管理。
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
    """MCP Session Coordinator服务器实现"""
    
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
    
    # ========== 会话注册和关系管理 ==========
    
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
    
    # ========== tmux会话管理 ==========
    
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