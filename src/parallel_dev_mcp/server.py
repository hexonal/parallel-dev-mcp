"""
FastMCP Server for Parallel Development MCP Tools
优化后的三层MCP工具架构服务器 - 移除过度设计，专注核心功能
"""

from fastmcp import FastMCP
from typing import Dict, Any, List, Optional
import json
import os
from pathlib import Path

# 导入优化后的三层架构核心工具 - 仅用于服务器启动逻辑，不包含MCP工具
from .tmux.orchestrator import tmux_session_orchestrator  # 仅用于启动逻辑
from .session.session_manager import create_development_session, terminate_session, query_session_status, list_all_managed_sessions, register_existing_session
from .session.message_system import send_message_to_session, get_session_messages, mark_message_read
from .session.relationship_manager import register_session_relationship, query_child_sessions
from .monitoring.health_monitor import check_system_health

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
mcp = FastMCP("Parallel Development MCP - 优化三层架构")

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

# === MCP工具已移至对应模块 ===
# 
# 🔧 TMUX LAYER: tmux/orchestrator.py
# - tmux_session_orchestrator
# - launch_claude_in_session
#
# 📋 SESSION LAYER: session/模块中
# - create_development_session (session/session_manager.py)
# - send_message_to_session (session/message_system.py)
# - get_session_messages (session/message_system.py) 
# - mark_message_read (session/message_system.py)
# - register_session_relationship (session/relationship_manager.py)
# - query_child_sessions (session/relationship_manager.py)
# - get_session_hierarchy (session/relationship_manager.py)
# - find_session_path (session/relationship_manager.py)
# - terminate_session (session/session_manager.py)
# - query_session_status (session/session_manager.py)
# - list_all_managed_sessions (session/session_manager.py)
# - register_existing_session (session/session_manager.py)
#
# 📊 MONITORING LAYER: monitoring/health_monitor.py
# - check_system_health
#
# 👨‍💼 CONFIG LAYER: _internal/config_tools.py
# - get_environment_config



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