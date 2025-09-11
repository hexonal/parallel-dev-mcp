"""Session Coordinator MCP Server

MCP服务器用于管理并行开发会话间的通信和状态协调。
"""

__version__ = "0.1.0"
__author__ = "Parallel Dev MCP"

from .session_coordinator import SessionCoordinatorMCP
from .session_models import SessionRelationship, SessionStatus, Message

__all__ = [
    "SessionCoordinatorMCP",
    "SessionRelationship", 
    "SessionStatus",
    "Message"
]