"""
Session Management Layer - 会话级操作

提供细粒度的会话管理能力，从server模块完美融合而来。
适合需要精确控制会话的高级用户。
"""

from .session_manager import (
    create_development_session,
    terminate_session,
    query_session_status,
    list_all_managed_sessions
)

from .message_system import (
    send_message_to_session,
    get_session_messages,
    mark_message_read,
    broadcast_message
)

from .relationship_manager import (
    register_session_relationship,
    query_child_sessions,
    get_session_hierarchy
)

__all__ = [
    # 会话管理
    "create_development_session",
    "terminate_session", 
    "query_session_status",
    "list_all_managed_sessions",
    
    # 消息系统
    "send_message_to_session",
    "get_session_messages",
    "mark_message_read",
    "broadcast_message",
    
    # 关系管理
    "register_session_relationship",
    "query_child_sessions",
    "get_session_hierarchy"
]