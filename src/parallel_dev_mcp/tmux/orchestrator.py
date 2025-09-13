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


@mcp_tool(
    name="launch_claude_in_session",
    description="在指定tmux会话中启动Claude，支持工作目录切换"
)
def launch_claude_in_session(
    project_id: str,
    task_id: str,
    working_directory: str,
    mcp_config_path: str,
    skip_permissions: bool = True,
    continue_session: bool = True
) -> Dict[str, Any]:
    """
    在tmux子会话中启动Claude - 支持worktree分支切换
    
    Args:
        project_id: 项目ID
        task_id: 任务ID  
        working_directory: 工作目录路径（worktree分支目录）
        mcp_config_path: MCP配置文件路径
        skip_permissions: 是否跳过权限检查（默认True）
        continue_session: 是否继续会话（默认True）
    """
    import subprocess
    import os
    
    try:
        # 构建会话名称
        session_name = f"parallel_{project_id}_task_child_{task_id}"
        
        # 验证工作目录存在
        if not os.path.exists(working_directory):
            return {
                "success": False,
                "error": f"工作目录不存在: {working_directory}",
                "session_name": session_name,
                "working_directory": working_directory
            }
        
        # 验证MCP配置文件存在
        if not os.path.exists(mcp_config_path):
            return {
                "success": False,
                "error": f"MCP配置文件不存在: {mcp_config_path}",
                "session_name": session_name,
                "mcp_config_path": mcp_config_path
            }
        
        # 检查tmux会话是否存在
        check_session_cmd = ["tmux", "has-session", "-t", session_name]
        session_exists = subprocess.run(check_session_cmd, capture_output=True, text=True).returncode == 0
        
        if not session_exists:
            return {
                "success": False,
                "error": f"tmux会话不存在: {session_name}",
                "session_name": session_name,
                "hint": "请先使用tmux_session_orchestrator创建会话"
            }
        
        # 1. 发送cd命令切换到工作目录
        cd_cmd = ["tmux", "send-keys", "-t", session_name, f"cd {working_directory}", "Enter"]
        cd_result = subprocess.run(cd_cmd, capture_output=True, text=True)
        
        if cd_result.returncode != 0:
            return {
                "success": False,
                "error": f"切换工作目录失败: {cd_result.stderr}",
                "session_name": session_name,
                "working_directory": working_directory
            }
        
        # 2. 构建claude启动命令
        claude_cmd_parts = ["claude"]
        
        if skip_permissions:
            claude_cmd_parts.append("--dangerously-skip-permissions")
        
        if continue_session:
            claude_cmd_parts.append("--continue")
        
        claude_cmd_parts.extend(["--mcp-config", mcp_config_path])
        
        claude_cmd = " ".join(claude_cmd_parts)
        
        # 3. 发送claude启动命令
        launch_cmd = ["tmux", "send-keys", "-t", session_name, claude_cmd, "Enter"]
        launch_result = subprocess.run(launch_cmd, capture_output=True, text=True)
        
        if launch_result.returncode != 0:
            return {
                "success": False,
                "error": f"启动Claude失败: {launch_result.stderr}",
                "session_name": session_name,
                "claude_command": claude_cmd
            }
        
        # 成功响应
        return {
            "success": True,
            "session_name": session_name,
            "project_id": project_id,
            "task_id": task_id,
            "working_directory": working_directory,
            "mcp_config_path": mcp_config_path,
            "claude_command": claude_cmd,
            "message": f"Claude已在会话 {session_name} 中启动",
            "next_steps": [
                f"使用 'tmux attach -t {session_name}' 连接到会话",
                "或使用tmux_session_orchestrator的attach操作"
            ]
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"启动Claude失败: {str(e)}",
            "session_name": f"parallel_{project_id}_task_child_{task_id}",
            "project_id": project_id,
            "task_id": task_id
        }