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
from .session.session_manager import create_development_session, terminate_session, query_session_status, list_all_managed_sessions, register_existing_session
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

# 全局配置数据存储（供工具函数访问）
LOADED_CONFIG = None

# 确保关键目录存在
Path(HOOKS_CONFIG_DIR).mkdir(parents=True, exist_ok=True)

def get_loaded_config() -> Optional[Dict[str, Any]]:
    """获取已加载的MCP配置数据"""
    return LOADED_CONFIG

def get_config_value(key: str, default: Any = None) -> Any:
    """从加载的配置中获取指定键的值"""
    if LOADED_CONFIG and isinstance(LOADED_CONFIG, dict):
        return LOADED_CONFIG.get(key, default)
    return default

# 创建FastMCP服务器实例
mcp = FastMCP("Parallel Development MCP - 完美融合四层架构")

# === 🤖 自动会话扫描和注册 ===

def auto_scan_and_register_sessions():
    """启动时自动扫描现有tmux会话并注册到MCP系统"""
    import subprocess
    import re
    from .session.session_manager import register_existing_session
    from ._internal.global_registry import get_global_registry
    
    try:
        # 获取所有tmux会话
        result = subprocess.run(['tmux', 'list-sessions', '-F', '#{session_name}'], 
                              capture_output=True, text=True, check=True)
        tmux_sessions = result.stdout.strip().split('\n') if result.stdout.strip() else []
        
        # 过滤parallel开头的会话
        parallel_sessions = [s for s in tmux_sessions if s.startswith('parallel_')]
        
        if not parallel_sessions:
            print("🔍 未发现parallel相关的tmux会话")
            return {"scanned": 0, "registered": 0}
        
        print(f"🔍 发现 {len(parallel_sessions)} 个parallel会话，开始自动注册...")
        
        registered_count = 0
        for session_name in parallel_sessions:
            try:
                # 调用注册函数
                result = register_existing_session(session_name)
                if result.get("success"):
                    registered_count += 1
                    session_type = result.get("session_type", "unknown")
                    project_id = result.get("project_id", "unknown")
                    print(f"✅ 注册成功: {session_name} [{session_type}] -> {project_id}")
                else:
                    print(f"⚠️  注册失败: {session_name} - {result.get('error', '未知错误')}")
            except Exception as e:
                print(f"❌ 注册异常: {session_name} - {str(e)}")
        
        print(f"🎯 自动扫描完成: 扫描 {len(parallel_sessions)} 个会话，成功注册 {registered_count} 个")
        return {"scanned": len(parallel_sessions), "registered": registered_count}
        
    except subprocess.CalledProcessError:
        print("⚠️  tmux未运行或无可用会话")
        return {"scanned": 0, "registered": 0}
    except Exception as e:
        print(f"❌ 自动扫描失败: {str(e)}")
        return {"scanned": 0, "registered": 0, "error": str(e)}

def auto_bind_master_session():
    """自动绑定主会话 - 基于当前tmux会话或PROJECT_ID环境变量"""
    import subprocess
    import os
    from ._internal.global_registry import get_global_registry
    
    try:
        # 从环境变量或当前会话名获取项目ID
        project_id = os.environ.get('PROJECT_ID')
        if not project_id:
            project_id = PROJECT_ROOT.split('/')[-1] if PROJECT_ROOT != os.getcwd() else 'unknown'
        
        # 获取当前tmux会话
        current_session = None
        try:
            result = subprocess.run(['tmux', 'display-message', '-p', '#{session_name}'], 
                                  capture_output=True, text=True, check=True)
            current_session = result.stdout.strip()
        except subprocess.CalledProcessError:
            print("⚠️  未在tmux环境中运行")
        
        # 确定主会话名称
        master_session = None
        if current_session and current_session.endswith('_task_master'):
            master_session = current_session
            # 从会话名提取project_id
            if current_session.startswith('parallel_'):
                parts = current_session.split('_')
                if len(parts) >= 4:
                    project_id = parts[1]
        elif project_id != 'unknown':
            master_session = f"parallel_{project_id}_task_master"
        
        if not master_session:
            return {"bound": False, "reason": "无法确定主会话"}
        
        # 检查主会话是否存在
        try:
            subprocess.run(['tmux', 'has-session', '-t', master_session], 
                         check=True, capture_output=True)
        except subprocess.CalledProcessError:
            return {"bound": False, "reason": f"主会话不存在: {master_session}"}
        
        # 注册主会话（如果尚未注册）
        registry = get_global_registry()
        if not registry.get_session_info(master_session):
            registry.register_session(master_session, "master", project_id)
        
        # 设置全局主会话绑定
        global BOUND_MASTER_SESSION, BOUND_PROJECT_ID
        BOUND_MASTER_SESSION = master_session
        BOUND_PROJECT_ID = project_id
        
        print(f"🎯 主会话自动绑定成功: {master_session} (项目: {project_id})")
        return {"bound": True, "master_session": master_session, "project_id": project_id}
        
    except Exception as e:
        print(f"❌ 主会话绑定失败: {str(e)}")
        return {"bound": False, "error": str(e)}

# 全局绑定状态
BOUND_MASTER_SESSION = None
BOUND_PROJECT_ID = None

# 延迟启动标志
_startup_initialized = False

def initialize_startup():
    """延迟启动初始化 - 避免干扰FastMCP工具注册"""
    global _startup_initialized
    if not _startup_initialized:
        print("🚀 Parallel-Dev-MCP启动中...")
        
        # 先清理过期会话
        from ._internal.global_registry import auto_cleanup_stale_sessions, sync_tmux_to_registry
        cleanup_result = auto_cleanup_stale_sessions()
        if cleanup_result["cleaned_count"] > 0:
            print(f"🧹 清理了 {cleanup_result['cleaned_count']} 个过期会话")
        
        # 同步tmux会话到注册表
        sync_result = sync_tmux_to_registry()
        if sync_result["synced_count"] > 0:
            print(f"🔄 同步了 {sync_result['synced_count']} 个会话到注册表")
        
        # 主会话绑定
        master_bind_result = auto_bind_master_session()
        print(f"📋 启动完成 - 清理: {cleanup_result['cleaned_count']} | 同步: {sync_result['synced_count']} | 绑定: {master_bind_result.get('bound', False)}")
        _startup_initialized = True

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
        # 首次工具调用时初始化启动逻辑
        initialize_startup()
        
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
    """发送消息到会话（自动使用绑定主会话作为发送者）"""
    try:
        # 首次工具调用时初始化启动逻辑
        initialize_startup()
        
        # 如果from_session为空或与绑定主会话匹配，使用绑定的主会话
        actual_sender = from_session
        if not from_session or from_session == BOUND_MASTER_SESSION:
            actual_sender = BOUND_MASTER_SESSION or "system"
        
        # 修复参数顺序：send_message_to_session需要(session_name, message_content, sender_session)
        result = send_message_to_session(
            session_name=to_session,
            message_content=message,
            sender_session=actual_sender
        )
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
    """列出当前项目的子会话（过滤主会话和其他项目会话）"""
    try:
        # 首次工具调用时初始化启动逻辑
        initialize_startup()
        
        # 获取所有会话
        all_sessions_result = list_all_managed_sessions()
        
        # 过滤只显示当前项目的子会话
        if BOUND_PROJECT_ID and all_sessions_result.get("success"):
            filtered_sessions = {}
            all_mcp_sessions = all_sessions_result.get("mcp_managed_sessions", {})
            
            for session_name, session_info in all_mcp_sessions.items():
                # 只保留当前项目的子会话
                if (session_info.get("session_type") == "child" and 
                    session_info.get("project_id") == BOUND_PROJECT_ID):
                    filtered_sessions[session_name] = session_info
            
            # 构建返回结果
            result = {
                "success": True,
                "mcp_managed_sessions": filtered_sessions,
                "tmux_sessions": all_sessions_result.get("tmux_sessions", []),
                "total_mcp_sessions": len(filtered_sessions),
                "total_tmux_sessions": all_sessions_result.get("total_tmux_sessions", 0),
                "query_time": all_sessions_result.get("query_time"),
                "filtered_for_project": BOUND_PROJECT_ID,
                "bound_master_session": BOUND_MASTER_SESSION
            }
            return {"success": True, "data": result}
        else:
            # 未绑定项目时，返回原始结果
            return {"success": True, "data": all_sessions_result}
            
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
        # 首次工具调用时初始化启动逻辑
        initialize_startup()
        
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
            "mcp_config_path": MCP_CONFIG,
            "loaded_config_data": LOADED_CONFIG,  # 实际加载的配置数据
            "hooks_mcp_config": HOOKS_MCP_CONFIG,
            "project_root": PROJECT_ROOT,
            "hooks_config_dir": HOOKS_CONFIG_DIR,
            "dangerously_skip_permissions": DANGEROUSLY_SKIP_PERMISSIONS,
            "working_directory": os.getcwd(),
            "config_loaded": LOADED_CONFIG is not None
        }
        return {"success": True, "data": config}
    except Exception as e:
        return {"success": False, "error": str(e)}



def main():
    """主入口函数 - 基于环境变量的简化启动"""
    import sys
    import json
    
    # 从环境变量读取配置（与uvx兼容）
    continue_on_error = os.environ.get('CONTINUE_ON_ERROR', 'false').lower() == 'true'
    
    # 如果指定了MCP配置文件，尝试加载到全局变量
    global LOADED_CONFIG
    if MCP_CONFIG and os.path.exists(MCP_CONFIG):
        try:
            with open(MCP_CONFIG, 'r') as f:
                LOADED_CONFIG = json.load(f)
            print(f"✅ MCP配置已加载到全局变量: {MCP_CONFIG}", file=sys.stderr)
        except Exception as e:
            print(f"⚠️  MCP配置加载失败: {e}", file=sys.stderr)
            LOADED_CONFIG = None
    elif MCP_CONFIG:
        print(f"⚠️  MCP配置文件不存在: {MCP_CONFIG}", file=sys.stderr)
        LOADED_CONFIG = None
    
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