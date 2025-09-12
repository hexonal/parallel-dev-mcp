"""
Global Session Registry - 全局共享会话注册表

提供系统级的单例会话注册表，确保所有组件使用同一个注册表实例，
避免会话管理和消息系统之间的同步问题。
"""

from .session_registry import SessionRegistry

# 全局单例会话注册表
_global_registry = None

def get_global_registry() -> SessionRegistry:
    """获取全局共享的会话注册表实例"""
    global _global_registry
    if _global_registry is None:
        _global_registry = SessionRegistry()
    return _global_registry

def reset_global_registry():
    """重置全局注册表（主要用于测试）"""
    global _global_registry
    _global_registry = None

def auto_cleanup_stale_sessions():
    """自动清理不存在的会话"""
    import subprocess
    registry = get_global_registry()
    
    try:
        # 获取所有tmux会话
        result = subprocess.run(['tmux', 'list-sessions', '-F', '#{session_name}'], 
                              capture_output=True, text=True, check=True)
        active_tmux_sessions = set(result.stdout.strip().split('\n')) if result.stdout.strip() else set()
    except subprocess.CalledProcessError:
        active_tmux_sessions = set()
    
    # 获取注册表中的所有会话
    registered_sessions = registry.list_all_sessions()
    
    cleaned_sessions = []
    for session_name in list(registered_sessions.keys()):
        # 如果注册的会话在tmux中不存在，则清理
        if session_name not in active_tmux_sessions:
            registry.remove_session(session_name)
            cleaned_sessions.append(session_name)
    
    return {
        "cleaned_count": len(cleaned_sessions),
        "cleaned_sessions": cleaned_sessions,
        "active_tmux_sessions": len(active_tmux_sessions),
        "remaining_registered_sessions": len(registry.list_all_sessions())
    }

def sync_tmux_to_registry():
    """同步tmux会话到注册表"""
    import subprocess
    registry = get_global_registry()
    
    try:
        # 获取所有tmux会话
        result = subprocess.run(['tmux', 'list-sessions', '-F', '#{session_name}'], 
                              capture_output=True, text=True, check=True)
        tmux_sessions = result.stdout.strip().split('\n') if result.stdout.strip() else []
        
        # 只处理parallel开头的会话
        parallel_sessions = [s for s in tmux_sessions if s.startswith('parallel_')]
        
        synced_sessions = []
        for session_name in parallel_sessions:
            if not registry.get_session_info(session_name):
                # 推断会话信息并注册
                session_info = _infer_session_info_from_name(session_name)
                registry.register_session(
                    session_name, 
                    session_info.get("session_type", "unknown"), 
                    session_info.get("project_id"), 
                    session_info.get("task_id")
                )
                synced_sessions.append(session_name)
        
        return {
            "synced_count": len(synced_sessions),
            "synced_sessions": synced_sessions,
            "total_parallel_sessions": len(parallel_sessions)
        }
        
    except subprocess.CalledProcessError:
        return {"synced_count": 0, "error": "tmux not available"}

def _infer_session_info_from_name(session_name: str) -> dict:
    """从会话名称推断会话信息"""
    info = {"project_id": None, "session_type": "unknown", "task_id": None}
    
    # 解析会话名称模式：parallel_{PROJECT_ID}_task_{master|child}_{TASK_ID}
    if session_name.startswith("parallel_") and "_task_" in session_name:
        parts = session_name.split("_")
        if len(parts) >= 4:
            # parallel, PROJECT_ID, task, {master|child}, [TASK_ID]
            info["project_id"] = parts[1]
            if parts[3] == "master":
                info["session_type"] = "master"
            elif parts[3] == "child":
                info["session_type"] = "child"
                if len(parts) > 4:
                    info["task_id"] = "_".join(parts[4:])
    
    return info