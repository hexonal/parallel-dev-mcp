"""
Tmux Session Orchestrator - Main Entry Point

Clean, focused entry point for tmux session management.
Delegates to specialized managers for each concern.
"""

from typing import Dict, Any, List, Optional
import os
import subprocess
from .session_manager import TmuxSessionManager
from .._internal import SessionNaming, ResponseBuilder, TmuxExecutor


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


def _validate_launch_prerequisites(project_id: str, task_id: str, 
                                 working_directory: str, 
                                 mcp_config_path: str) -> Dict[str, Any]:
    """验证启动Claude的前置条件
    
    Args:
        project_id: 项目ID
        task_id: 任务ID
        working_directory: 工作目录路径
        mcp_config_path: MCP配置文件路径
        
    Returns:
        Dict[str, Any]: 验证结果
    """
    session_name = SessionNaming.child_session(project_id, task_id)
    
    # 验证工作目录存在
    if not os.path.exists(working_directory):
        return ResponseBuilder.not_found_error("working directory", working_directory)
    
    # 验证MCP配置文件存在  
    if not os.path.exists(mcp_config_path):
        return ResponseBuilder.not_found_error("MCP config file", mcp_config_path)
    
    # 检查tmux会话是否存在
    if not TmuxExecutor.session_exists(session_name):
        return ResponseBuilder.not_found_error("tmux session", session_name)
    
    return ResponseBuilder.success(session_name=session_name)


def _build_claude_command(mcp_config_path: str, skip_permissions: bool, 
                         continue_session: bool) -> str:
    """构建Claude启动命令
    
    Args:
        mcp_config_path: MCP配置文件路径
        skip_permissions: 是否跳过权限检查
        continue_session: 是否继续会话
        
    Returns:
        str: Claude启动命令
    """
    cmd_parts = ["claude"]
    
    if skip_permissions:
        cmd_parts.append("--dangerously-skip-permissions")
    
    if continue_session:
        cmd_parts.append("--continue")
    
    cmd_parts.extend(["--mcp-config", mcp_config_path])
    
    return " ".join(cmd_parts)


def _execute_claude_launch(session_name: str, working_directory: str,
                          claude_command: str, project_id: str, task_id: str,
                          mcp_config_path: str) -> Dict[str, Any]:
    """执行Claude启动操作
    
    Args:
        session_name: 会话名称
        working_directory: 工作目录
        claude_command: Claude启动命令
        project_id: 项目ID
        task_id: 任务ID  
        mcp_config_path: MCP配置路径
        
    Returns:
        Dict[str, Any]: 执行结果
    """
    # 1. 切换工作目录
    cd_result = TmuxExecutor.change_directory(session_name, working_directory)
    if not cd_result["success"]:
        return ResponseBuilder.error(
            f"切换工作目录失败: {cd_result.get('error', '')}",
            session_name=session_name,
            working_directory=working_directory
        )
    
    # 2. 启动Claude
    launch_result = TmuxExecutor.send_command(session_name, claude_command)
    if not launch_result["success"]:
        return ResponseBuilder.error(
            f"启动Claude失败: {launch_result.get('error', '')}",
            session_name=session_name,
            claude_command=claude_command
        )
    
    # 3. 返回成功响应
    return ResponseBuilder.session_result(
        session_name=session_name,
        project_id=project_id,
        task_id=task_id,
        working_directory=working_directory,
        mcp_config_path=mcp_config_path,
        claude_command=claude_command,
        message=f"Claude已在会话 {session_name} 中启动",
        next_steps=[
            f"使用 'tmux attach -t {session_name}' 连接到会话",
            "或使用tmux_session_orchestrator的attach操作"
        ]
    )


@mcp_tool(
    name="launch_claude_in_session",
    description="在指定tmux会话中启动Claude，支持工作目录切换"
)
def launch_claude_in_session(
    project_id: str,
    task_id: str,
    working_directory: str,
    mcp_config_path: str = None,
    skip_permissions: bool = None,
    continue_session: bool = False
) -> Dict[str, Any]:
    """在tmux子会话中启动Claude - 支持worktree分支切换

    Args:
        project_id: 项目ID
        task_id: 任务ID
        working_directory: 工作目录路径（worktree分支目录）
        mcp_config_path: MCP配置文件路径（可从MCP_CONFIG_PATH环境变量获取）
        skip_permissions: 是否跳过权限检查（可从DANGEROUSLY_SKIP_PERMISSIONS环境变量获取，默认False）
        continue_session: 是否继续会话（默认False）
    """
    try:
        import os

        # 从环境变量获取配置参数（如果未提供）
        if mcp_config_path is None:
            mcp_config_path = os.environ.get('MCP_CONFIG_PATH')
            if not mcp_config_path:
                return ResponseBuilder.validation_error(
                    "mcp_config_path", "None",
                    "MCP配置路径必须提供，或设置MCP_CONFIG_PATH环境变量"
                )

        if skip_permissions is None:
            skip_permissions = os.environ.get('DANGEROUSLY_SKIP_PERMISSIONS', 'false').lower() == 'true'

        # 1. 验证前置条件
        validation_result = _validate_launch_prerequisites(
            project_id, task_id, working_directory, mcp_config_path)
        if not validation_result["success"]:
            return validation_result
            
        session_name = validation_result["session_name"]
        
        # 2. 构建命令
        claude_command = _build_claude_command(
            mcp_config_path, skip_permissions, continue_session)
        
        # 3. 执行启动
        return _execute_claude_launch(
            session_name, working_directory, claude_command,
            project_id, task_id, mcp_config_path)
            
    except Exception as e:
        return ResponseBuilder.error(
            f"启动Claude失败: {str(e)}",
            session_name=SessionNaming.child_session(project_id, task_id),
            project_id=project_id,
            task_id=task_id
        )