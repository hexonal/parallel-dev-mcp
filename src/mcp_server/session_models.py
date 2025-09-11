"""会话协调系统的数据模型定义

定义了会话关系、状态和消息的数据结构，为MCP服务器提供类型安全的数据操作。
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum


class SessionRole(Enum):
    """会话角色枚举"""
    MASTER = "master"
    CHILD = "child"


class SessionStatusEnum(Enum):
    """会话状态枚举"""
    UNKNOWN = "UNKNOWN"
    STARTING = "STARTING"
    STARTED = "STARTED"
    WORKING = "WORKING"
    COMPLETED = "COMPLETED"
    BLOCKED = "BLOCKED"
    ERROR = "ERROR"
    TERMINATED = "TERMINATED"


class MessageType(Enum):
    """消息类型枚举"""
    STATUS_UPDATE = "STATUS_UPDATE"
    TASK_COMPLETED = "TASK_COMPLETED"
    INSTRUCTION = "INSTRUCTION"
    QUERY = "QUERY"
    RESPONSE = "RESPONSE"
    ERROR = "ERROR"


@dataclass
class SessionRelationship:
    """会话关系数据模型"""
    parent_session: str
    child_session: str
    task_id: str
    project_id: str
    created_at: datetime = field(default_factory=datetime.now)
    is_active: bool = True


@dataclass
class SessionStatus:
    """会话状态数据模型"""
    session_name: str
    status: SessionStatusEnum
    progress: int = 0
    details: str = ""
    last_update: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "session_name": self.session_name,
            "status": self.status.value,
            "progress": self.progress,
            "details": self.details,
            "last_update": self.last_update.isoformat(),
            "metadata": self.metadata
        }


@dataclass
class Message:
    """会话间消息数据模型"""
    message_id: str
    from_session: str
    to_session: str
    message_type: MessageType
    content: str
    created_at: datetime = field(default_factory=datetime.now)
    is_read: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "message_id": self.message_id,
            "from_session": self.from_session,
            "to_session": self.to_session,
            "message_type": self.message_type.value,
            "content": self.content,
            "created_at": self.created_at.isoformat(),
            "is_read": self.is_read,
            "metadata": self.metadata
        }


@dataclass
class SessionCoordinatorState:
    """MCP服务器状态数据模型"""
    session_relationships: Dict[str, SessionRelationship] = field(default_factory=dict)
    active_sessions: Dict[str, SessionStatus] = field(default_factory=dict)
    session_messages: Dict[str, List[Message]] = field(default_factory=dict)
    last_cleanup: datetime = field(default_factory=datetime.now)
    
    def get_child_sessions(self, parent_session: str) -> List[str]:
        """获取指定父会话的所有子会话"""
        children = []
        for child_name, relationship in self.session_relationships.items():
            if (relationship.parent_session == parent_session and 
                relationship.is_active):
                children.append(child_name)
        return children
    
    def get_parent_session(self, child_session: str) -> Optional[str]:
        """获取指定子会话的父会话"""
        relationship = self.session_relationships.get(child_session)
        return relationship.parent_session if relationship else None