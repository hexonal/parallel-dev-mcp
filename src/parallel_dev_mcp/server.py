"""
FastMCP Server for Parallel Development MCP Tools
完美融合的四层MCP工具架构服务器
"""

from fastmcp import FastMCP
from typing import Dict, Any, List, Optional
import json
import os
from pathlib import Path

# 导入四层架构的所有工具
from .tmux.orchestrator import tmux_session_orchestrator  
from .session.session_manager import create_development_session, terminate_session, query_session_status, list_all_managed_sessions
from .session.message_system import send_message_to_session, get_session_messages, mark_message_read, broadcast_message
from .session.relationship_manager import register_session_relationship, query_child_sessions, get_session_hierarchy
from .monitoring.health_monitor import check_system_health, diagnose_session_issues, get_performance_metrics
from .monitoring.status_dashboard import get_system_dashboard, generate_status_report, export_system_metrics  
from .orchestrator.project_orchestrator import orchestrate_project_workflow, manage_project_lifecycle, coordinate_parallel_tasks

# 读取环境变量配置
MCP_CONFIG = os.environ.get('MCP_CONFIG')
HOOKS_MCP_CONFIG = os.environ.get('HOOKS_MCP_CONFIG')
PROJECT_ROOT = os.environ.get('PROJECT_ROOT', os.getcwd())
HOOKS_CONFIG_DIR = os.environ.get('HOOKS_CONFIG_DIR', os.path.join(PROJECT_ROOT, 'config/hooks'))
DANGEROUSLY_SKIP_PERMISSIONS = os.environ.get('DANGEROUSLY_SKIP_PERMISSIONS', 'false').lower() == 'true'

# 确保关键目录存在
Path(HOOKS_CONFIG_DIR).mkdir(parents=True, exist_ok=True)

# 创建FastMCP服务器实例
mcp = FastMCP("Parallel Development MCP - 完美融合四层架构")

# === 🔧 TMUX LAYER - 基础会话编排 ===

@mcp.tool
def tmux_orchestrator(action: str, project_id: str, tasks: List[str]) -> Dict[str, Any]:
    """
    Tmux会话编排 - 基础会话管理
    
    Args:
        action: 操作类型 (init, start, status, cleanup)
        project_id: 项目ID
        tasks: 任务列表
    """
    try:
        result = tmux_session_orchestrator(action, project_id, tasks)
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}

# === 📋 SESSION LAYER - 细粒度会话管理 ===

@mcp.tool  
def create_session(project_id: str, session_type: str, task_id: Optional[str] = None) -> Dict[str, Any]:
    """
    创建开发会话 - Session层细粒度管理
    
    Args:
        project_id: 项目ID
        session_type: 会话类型 (master, child)
        task_id: 任务ID (子会话必需)
    """
    try:
        result = create_development_session(project_id, session_type, task_id)
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}

@mcp.tool
def send_session_message(from_session: str, to_session: str, message: str) -> Dict[str, Any]:
    """发送消息到会话"""
    try:
        result = send_message_to_session(from_session, to_session, message)
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}

@mcp.tool
def get_session_status(session_name: str) -> Dict[str, Any]:
    """查询会话状态"""
    try:
        result = query_session_status(session_name)
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}

@mcp.tool
def list_sessions() -> Dict[str, Any]:
    """列出所有管理的会话"""
    try:
        result = list_all_managed_sessions()
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}

@mcp.tool
def get_messages(session_name: str) -> Dict[str, Any]:
    """获取会话消息"""
    try:
        result = get_session_messages(session_name)
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}

@mcp.tool
def register_relationship(parent_session: str, child_session: str, task_id: str, project_id: str) -> Dict[str, Any]:
    """注册会话关系"""
    try:
        result = register_session_relationship(parent_session, child_session, task_id, project_id)
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}

# === 📊 MONITORING LAYER - 系统监控和诊断 ===

@mcp.tool
def system_health_check(include_detailed_metrics: bool = False) -> Dict[str, Any]:
    """
    系统健康检查 - Monitoring层监控功能
    
    Args:
        include_detailed_metrics: 包含详细指标
    """
    try:
        result = check_system_health(include_detailed_metrics)
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}

@mcp.tool
def diagnose_issues(session_name: str) -> Dict[str, Any]:
    """诊断会话问题"""
    try:
        result = diagnose_session_issues(session_name)
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}

@mcp.tool
def performance_metrics() -> Dict[str, Any]:
    """获取性能指标"""
    try:
        result = get_performance_metrics()
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}

@mcp.tool
def system_dashboard(include_trends: bool = False) -> Dict[str, Any]:
    """获取系统仪表板"""
    try:
        result = get_system_dashboard(include_trends)
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}

@mcp.tool
def status_report() -> Dict[str, Any]:
    """生成状态报告"""
    try:
        result = generate_status_report()
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}

# === 🎯 ORCHESTRATOR LAYER - 项目级编排和管理 ===

@mcp.tool
def project_workflow(project_id: str, workflow_type: str, tasks: List[str], parallel_execution: bool = False) -> Dict[str, Any]:
    """
    项目工作流编排 - Orchestrator层项目管理
    
    Args:
        project_id: 项目ID
        workflow_type: 工作流类型 (development, testing, deployment)
        tasks: 任务列表
        parallel_execution: 并行执行
    """
    try:
        result = orchestrate_project_workflow(project_id, workflow_type, tasks, parallel_execution)
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}

@mcp.tool
def project_lifecycle(project_id: str, phase: str) -> Dict[str, Any]:
    """项目生命周期管理"""
    try:
        result = manage_project_lifecycle(project_id, phase)
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}

@mcp.tool
def coordinate_tasks(project_id: str, tasks: List[str]) -> Dict[str, Any]:
    """
    并行任务协调
    
    Args:
        project_id: 项目ID
        tasks: 任务名称列表，将自动转换为任务对象
    """
    try:
        # 将字符串任务列表转换为任务对象列表
        task_objects = []
        for i, task_name in enumerate(tasks):
            task_objects.append({
                "id": f"{project_id}_task_{i+1}",
                "name": task_name,
                "dependencies": [],  # 简单场景无依赖
                "commands": [f"echo 'Executing task: {task_name}'"]
            })
        
        result = coordinate_parallel_tasks(project_id, task_objects)
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}



@mcp.tool  
def get_environment_config() -> Dict[str, Any]:
    """获取当前MCP服务器的环境配置"""
    try:
        config = {
            "hooks_mcp_config": HOOKS_MCP_CONFIG,
            "project_root": PROJECT_ROOT,
            "hooks_config_dir": HOOKS_CONFIG_DIR,
            "dangerously_skip_permissions": DANGEROUSLY_SKIP_PERMISSIONS,
            "working_directory": os.getcwd()
        }
        return {"success": True, "data": config}
    except Exception as e:
        return {"success": False, "error": str(e)}



def main():
    """主入口函数 - 基于环境变量的简化启动"""
    import sys
    
    # 从环境变量读取配置（与uvx兼容）
    continue_on_error = os.environ.get('CONTINUE_ON_ERROR', 'false').lower() == 'true'
    
    # 启动服务器
    try:
        mcp.run()
    except Exception as e:
        if not continue_on_error:
            sys.stderr.write(f"Server error: {e}\n")
            sys.exit(1)
        else:
            sys.stderr.write(f"Warning: {e}\n")

if __name__ == "__main__":
    main()