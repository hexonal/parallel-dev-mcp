"""
Tmux Session Orchestrator - Main Entry Point

Clean, focused entry point for tmux session management.
Delegates to specialized managers for each concern.
"""

from typing import Dict, Any, List, Optional
from .session_manager import TmuxSessionManager


def mcp_tool(name: str = None, description: str = None):
    """MCP工具装饰器"""
    def decorator(func):
        func.mcp_tool_name = name or func.__name__
        func.mcp_tool_description = description or func.__doc__
        return func
    return decorator


@mcp_tool(
    name="tmux_session_orchestrator",
    description="基于tmux的纯MCP会话编排器，替代所有shell脚本"
)
def tmux_session_orchestrator(
    action: str,  # init|start|status|message|attach|cleanup|list
    project_id: str,
    tasks: Optional[List[str]] = None,
    from_session: Optional[str] = None,
    to_session: Optional[str] = None,
    message: Optional[str] = None,
    session_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    基于tmux的纯MCP会话编排器
    
    替代功能：
    - setup_claude_code.sh -> init action
    - start_master_*.sh -> start action (master sessions)
    - start_child_*.sh -> start action (child sessions) 
    - status_*.sh -> status action
    - cleanup_*.sh -> cleanup action
    - 会话间通信 -> message action
    
    Args:
        action: 操作类型
        project_id: 项目ID
        tasks: 任务列表 (用于init和start)
        from_session: 发送消息的源会话
        to_session: 接收消息的目标会话
        message: 消息内容
        session_type: 会话类型 (用于attach)
    """
    
    try:
        manager = TmuxSessionManager(project_id)
        
        # 使用策略模式处理不同操作
        action_handlers = {
            "init": lambda: manager.init_project(tasks or []),
            "start": lambda: manager.start_all_sessions(tasks or []),
            "status": lambda: manager.get_project_status(),
            "attach": lambda: manager.get_attach_instructions(session_type or "master"),
            "cleanup": lambda: manager.cleanup_project(),
            "list": lambda: manager.list_all_sessions(),
            "message": lambda: _handle_message_action(manager, from_session, to_session, message)
        }
        
        if action not in action_handlers:
            return _build_error_response("Unknown action", action, project_id)
            
        return action_handlers[action]()
        
    except Exception as e:
        return _build_error_response(f"Failed to execute action '{action}'", str(e), project_id, action)


def _handle_message_action(manager, from_session, to_session, message):
    """处理消息操作的私有函数"""
    if not all([from_session, to_session, message]):
        return {"error": "message action requires from_session, to_session, and message"}
    return manager.send_inter_session_message(from_session, to_session, message)


def _build_error_response(error_type: str, error_detail: str, project_id: str, action: str = None):
    """构建标准错误响应"""
    response = {
        "error": f"{error_type}: {error_detail}",
        "project_id": project_id
    }
    
    if action:
        response["action"] = action
    else:
        response["available_actions"] = [
            "init", "start", "status", "message", "attach", "cleanup", "list"
        ]
    
    return response