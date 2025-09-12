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