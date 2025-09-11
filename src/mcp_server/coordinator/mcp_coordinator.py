"""
MCP Coordinator - Clean session coordination with modular architecture

Main MCP tools interface using specialized components.
Each tool delegates to appropriate specialized manager.
"""

import json
import logging
import os
import subprocess
from datetime import datetime
from typing import Dict, Any, List

from .session_registry import SessionRegistry
from .status_monitor import calculate_session_health_score
from .message_handler import MessageHandler
from .tmux_integration import TmuxIntegration
from .status_monitor import StatusMonitor


def mcp_tool(name: str = None, description: str = None):
    """MCP工具装饰器"""
    def decorator(func):
        func.mcp_tool_name = name or func.__name__
        func.mcp_tool_description = description or func.__doc__
        return func
    return decorator


class SessionCoordinatorMCP:
    """重构后的会话协调器 - 清洁的模块化架构"""
    
    def __init__(self, name: str = "session-coordinator"):
        self.name = name
        self.logger = self._setup_logging()
        
        # 组件初始化
        self.registry = SessionRegistry()
        self.message_handler = MessageHandler(self.registry)
        self.tmux_integration = TmuxIntegration(self.registry, self.logger)
        self.status_monitor = StatusMonitor(self.registry)
        
        self.logger.info(f"Session Coordinator '{name}' 初始化完成")
    
    def _setup_logging(self) -> logging.Logger:
        """设置日志系统"""
        logger = logging.getLogger(f"session_coordinator_mcp_{self.name}")
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        
        return logger
    
    # === 核心会话管理MCP工具 ===
    
    @mcp_tool(
        name="create_development_session",
        description="创建开发会话，支持tmux集成和环境配置"
    )
    def create_development_session(
        self, 
        project_id: str, 
        session_type: str = "master",
        task_id: str = None,
        working_directory: str = None
    ) -> str:
        """创建开发会话"""
        try:
            # 安全检查
            caller_check = self._check_caller_permissions("create_session")
            if not caller_check["allowed"]:
                return json.dumps({
                    "success": False,
                    "error": caller_check["reason"],
                    "security_violation": True
                })
            
            # 参数验证
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
            
            # 生成会话名称
            if session_type == "master":
                session_name = f"master_project_{project_id}"
            else:
                session_name = f"child_{project_id}_task_{task_id}"
            
            # 检查会话是否已存在
            if session_name in self.registry.active_sessions:
                return json.dumps({
                    "success": False,
                    "error": f"会话已存在: {session_name}"
                })
            
            # 创建tmux会话 
            tmux_result = self._create_tmux_session(session_name, working_directory, session_type, project_id, task_id)
            if not tmux_result["success"]:
                return json.dumps(tmux_result)
            
            # 注册到MCP系统
            self.registry.register_session(session_name, session_type, project_id, task_id)
            
            # 建立父子关系
            if session_type == "child":
                master_session = f"master_project_{project_id}"
                self.registry.register_relationship(master_session, session_name)
            
            result = {
                "success": True,
                "session_name": session_name,
                "session_type": session_type,
                "project_id": project_id,
                "task_id": task_id,
                "tmux_info": tmux_result,
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
        """终止会话"""
        try:
            # 安全检查
            caller_check = self._check_caller_permissions("terminate_session")
            if not caller_check["allowed"]:
                return json.dumps({
                    "success": False,
                    "error": caller_check["reason"],
                    "security_violation": True
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
    
    # === 会话关系管理MCP工具 ===
    
    @mcp_tool(
        name="register_session_relationship",
        description="注册主子会话的关系，建立会话间的通信链路"
    )
    def register_session_relationship(self, parent_session: str, child_session: str, task_id: str = None) -> str:
        """注册会话关系"""
        try:
            success = self.registry.register_relationship(parent_session, child_session)
            
            if success:
                self.logger.info(f"注册会话关系: {child_session} -> {parent_session} (任务: {task_id})")
            
            return json.dumps({
                "parent_session": parent_session,
                "child_session": child_session,
                "task_id": task_id,
                "registration_success": success,
                "timestamp": datetime.now().isoformat()
            }, indent=2)
            
        except Exception as e:
            error_msg = f"注册会话关系失败: {str(e)}"
            self.logger.error(error_msg)
            return json.dumps({"error": error_msg})
    
    @mcp_tool(
        name="query_child_sessions",
        description="查询指定父会话的所有子会话"
    )
    def query_child_sessions(self, parent_session: str) -> str:
        """查询子会话"""
        try:
            child_sessions = self.registry.get_child_sessions(parent_session)
            result = []
            
            for child_session in child_sessions:
                session_info = self.registry.get_session_info(child_session)
                if session_info:
                    child_info = session_info.to_dict()
                    child_info["health_score"] = calculate_session_health_score(child_info)
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
        """查询会话状态"""
        return json.dumps(self.status_monitor.get_detailed_session_status(session_name), indent=2)
    
    # === 消息传递MCP工具 ===
    
    @mcp_tool(
        name="send_message_to_session",
        description="向指定会话发送消息"
    )
    def send_message_to_session(self, from_session: str, to_session: str, message: str, message_type: str = "general") -> str:
        """发送消息到会话"""
        try:
            result = self.message_handler.send_message(from_session, to_session, message, message_type)
            
            if result["success"]:
                self.logger.info(f"消息发送: {from_session} -> {to_session}")
            
            return json.dumps(result, indent=2)
            
        except Exception as e:
            error_msg = f"发送消息失败: {str(e)}"
            self.logger.error(error_msg)
            return json.dumps({"success": False, "error": error_msg})
    
    @mcp_tool(
        name="get_session_messages",
        description="获取会话的消息"
    )
    def get_session_messages(self, session_name: str, unread_only: bool = True) -> str:
        """获取会话消息"""
        try:
            result = self.message_handler.get_messages(session_name, unread_only)
            
            if result["success"]:
                unread_messages = len([msg for msg in result.get("messages", []) if not msg.get("read", False)])
                self.logger.info(f"获取消息: {session_name} -> {len(result.get('messages', []))}条消息，{unread_messages}条未读")
            
            return json.dumps(result, indent=2)
            
        except Exception as e:
            error_msg = f"获取消息失败: {str(e)}"
            self.logger.error(error_msg)
            return json.dumps({"success": False, "error": error_msg})
    
    # === Tmux集成MCP工具 ===
    
    @mcp_tool(
        name="tmux_project_init",
        description="初始化tmux项目，替代setup_claude_code.sh"
    )
    def tmux_project_init(self, project_id: str, tasks: str) -> str:
        """初始化tmux项目"""
        return json.dumps(self.tmux_integration.init_project(project_id, tasks))
    
    @mcp_tool(
        name="tmux_project_start",
        description="启动所有tmux会话，替代start_master_*.sh和start_child_*.sh"
    )
    def tmux_project_start(self, project_id: str, tasks: str = None) -> str:
        """启动tmux项目"""
        return json.dumps(self.tmux_integration.start_project(project_id, tasks))
    
    @mcp_tool(
        name="tmux_project_status",
        description="获取tmux项目完整状态，替代status_*.sh"
    )
    def tmux_project_status(self, project_id: str) -> str:
        """获取tmux项目状态"""
        return json.dumps(self.tmux_integration.get_project_status(project_id))
    
    @mcp_tool(
        name="tmux_project_cleanup",
        description="清理tmux项目环境，替代cleanup_*.sh"
    )
    def tmux_project_cleanup(self, project_id: str) -> str:
        """清理tmux项目"""
        return json.dumps(self.tmux_integration.cleanup_project(project_id))
    
    @mcp_tool(
        name="tmux_session_attach_info",
        description="获取tmux会话连接信息"
    )
    def tmux_session_attach_info(self, project_id: str, session_type: str = "master") -> str:
        """获取tmux会话连接信息"""
        return json.dumps(self.tmux_integration.get_session_attach_info(project_id, session_type))
    
    # === 系统监控MCP工具 ===
    
    @mcp_tool(
        name="get_system_health",
        description="获取系统整体健康状态"
    )
    def get_system_health(self) -> str:
        """获取系统健康状态"""
        return json.dumps(self.status_monitor.get_system_health(), indent=2)
    
    @mcp_tool(
        name="get_performance_metrics",
        description="获取系统性能指标"
    )
    def get_performance_metrics(self) -> str:
        """获取性能指标"""
        return json.dumps(self.status_monitor.get_performance_metrics(), indent=2)
    
    @mcp_tool(
        name="run_diagnostic_checks",
        description="运行系统诊断检查"
    )
    def run_diagnostic_checks(self) -> str:
        """运行诊断检查"""
        return json.dumps(self.status_monitor.run_diagnostic_checks(), indent=2)
    
    @mcp_tool(
        name="list_all_managed_sessions",
        description="列出所有MCP管理的会话"
    )
    def list_all_managed_sessions(self) -> str:
        """列出所有管理的会话"""
        try:
            all_sessions = self.registry.list_all_sessions()
            tmux_sessions = self._get_all_tmux_sessions()
            
            result = {
                "mcp_managed_sessions": {name: info.to_dict() for name, info in all_sessions.items()},
                "tmux_sessions": tmux_sessions,
                "total_mcp_sessions": len(all_sessions),
                "total_tmux_sessions": len(tmux_sessions),
                "query_time": datetime.now().isoformat()
            }
            
            self.logger.info(f"列出所有会话: 总计{len(all_sessions)}个MCP会话，{len(tmux_sessions)}个tmux会话")
            
            return json.dumps(result, indent=2)
            
        except Exception as e:
            error_msg = f"列出会话失败: {str(e)}"
            self.logger.error(error_msg)
            return json.dumps({"success": False, "error": error_msg})
    
    # === 私有辅助方法 ===
    
    def _check_caller_permissions(self, operation: str) -> Dict[str, Any]:
        """检查调用者权限"""
        # 简化权限检查 - 在实际部署中可以增强
        return {"allowed": True, "operation": operation}
    
    def _create_tmux_session(self, session_name: str, working_directory: str, 
                           session_type: str, project_id: str, task_id: str) -> Dict[str, Any]:
        """创建tmux会话"""
        try:
            working_directory = working_directory or os.getcwd()
            
            # 基本环境变量
            env_vars = {
                'PROJECT_ID': project_id,
                'SESSION_ROLE': session_type
            }
            
            if task_id:
                env_vars['TASK_ID'] = task_id
            
            # 创建tmux会话
            cmd = ['tmux', 'new-session', '-d', '-s', session_name, '-c', working_directory]
            
            # 添加环境变量
            for key, value in env_vars.items():
                cmd.extend(['-e', f'{key}={value}'])
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                return {
                    "success": True,
                    "session_name": session_name,
                    "working_directory": working_directory,
                    "environment": env_vars
                }
            else:
                return {
                    "success": False,
                    "error": f"tmux session creation failed: {result.stderr}"
                }
                
        except Exception as e:
            return {"success": False, "error": f"tmux session creation error: {str(e)}"}
    
    def _kill_tmux_session(self, session_name: str) -> Dict[str, Any]:
        """终止tmux会话"""
        try:
            result = subprocess.run(['tmux', 'kill-session', '-t', session_name], 
                                  capture_output=True, text=True)
            
            return {
                "success": result.returncode == 0,
                "session_name": session_name,
                "output": result.stdout if result.returncode == 0 else result.stderr
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _cleanup_mcp_session(self, session_name: str) -> Dict[str, Any]:
        """清理MCP会话状态"""
        try:
            # 移除会话注册
            removed = self.registry.remove_session(session_name)
            
            return {
                "success": removed,
                "session_name": session_name,
                "removed_from_registry": removed
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _get_all_tmux_sessions(self) -> List[str]:
        """获取所有tmux会话名称"""
        try:
            result = subprocess.run(['tmux', 'list-sessions', '-F', '#{session_name}'], 
                                  capture_output=True, text=True)
            
            if result.returncode == 0:
                return result.stdout.strip().split('\n') if result.stdout.strip() else []
            else:
                return []
                
        except Exception:
            return []


# 创建全局实例，保持向后兼容
session_coordinator = SessionCoordinatorMCP()