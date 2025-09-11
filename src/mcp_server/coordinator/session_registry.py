"""
Session Registry - Clean session relationship management

Focused on session registration and relationship tracking.
No mixing of concerns with other functionality.
"""

import json
from typing import Dict, Any, List
from datetime import datetime


class SessionInfo:
    """会话信息数据类"""
    def __init__(self, name: str, session_type: str = "unknown", 
                 project_id: str = None, task_id: str = None):
        self.name = name
        self.session_type = session_type
        self.project_id = project_id
        self.task_id = task_id
        self.created_at = datetime.now()
        self.last_activity = datetime.now()
        self.message_count = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "session_type": self.session_type,
            "project_id": self.project_id,
            "task_id": self.task_id,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "message_count": self.message_count
        }


class SessionRegistry:
    """会话注册中心 - 纯会话关系管理"""
    
    def __init__(self):
        self.active_sessions: Dict[str, SessionInfo] = {}
        self.session_relationships: Dict[str, List[str]] = {}
        self.session_messages: Dict[str, List[Dict[str, Any]]] = {}
        self.last_cleanup = datetime.now()
    
    def register_session(self, name: str, session_type: str = "unknown", 
                        project_id: str = None, task_id: str = None) -> bool:
        """注册新会话"""
        if name in self.active_sessions:
            return False
        
        self.active_sessions[name] = SessionInfo(name, session_type, project_id, task_id)
        self.session_messages[name] = []
        return True
    
    def register_relationship(self, parent_session: str, child_session: str) -> bool:
        """注册会话关系"""
        if parent_session not in self.session_relationships:
            self.session_relationships[parent_session] = []
        
        if child_session not in self.session_relationships[parent_session]:
            self.session_relationships[parent_session].append(child_session)
            return True
        
        return False
    
    def get_child_sessions(self, parent_session: str) -> List[str]:
        """获取子会话列表"""
        return self.session_relationships.get(parent_session, [])
    
    def get_parent_session(self, child_session: str) -> str:
        """获取父会话"""
        for parent, children in self.session_relationships.items():
            if child_session in children:
                return parent
        return None
    
    def get_session_info(self, session_name: str) -> SessionInfo:
        """获取会话信息"""
        return self.active_sessions.get(session_name)
    
    def list_all_sessions(self) -> Dict[str, SessionInfo]:
        """列出所有会话"""
        return self.active_sessions.copy()
    
    def remove_session(self, session_name: str) -> bool:
        """移除会话"""
        if session_name in self.active_sessions:
            del self.active_sessions[session_name]
            
        if session_name in self.session_messages:
            del self.session_messages[session_name]
            
        # 移除会话关系
        if session_name in self.session_relationships:
            del self.session_relationships[session_name]
        
        # 从父子关系中移除
        for parent, children in self.session_relationships.items():
            if session_name in children:
                children.remove(session_name)
        
        return True
    
    def update_session_activity(self, session_name: str):
        """更新会话活动时间"""
        if session_name in self.active_sessions:
            self.active_sessions[session_name].last_activity = datetime.now()
    
    def add_message_to_session(self, session_name: str, message: Dict[str, Any]):
        """添加消息到会话"""
        if session_name not in self.session_messages:
            self.session_messages[session_name] = []
        
        self.session_messages[session_name].append(message)
        
        if session_name in self.active_sessions:
            self.active_sessions[session_name].message_count += 1
            self.update_session_activity(session_name)
    
    def get_session_messages(self, session_name: str, unread_only: bool = False) -> List[Dict[str, Any]]:
        """获取会话消息"""
        messages = self.session_messages.get(session_name, [])
        
        if unread_only:
            messages = [msg for msg in messages if not msg.get('read', False)]
        
        return messages
    
    def mark_message_as_read(self, session_name: str, message_id: str):
        """标记消息为已读"""
        if session_name in self.session_messages:
            for message in self.session_messages[session_name]:
                if message.get('id') == message_id:
                    message['read'] = True
                    break
    
    def get_registry_stats(self) -> Dict[str, Any]:
        """获取注册中心统计信息"""
        total_messages = sum(len(messages) for messages in self.session_messages.values())
        
        return {
            "total_sessions": len(self.active_sessions),
            "total_relationships": len(self.session_relationships),
            "total_messages": total_messages,
            "last_cleanup": self.last_cleanup.isoformat(),
            "session_types": self._get_session_type_stats()
        }
    
    def _get_session_type_stats(self) -> Dict[str, int]:
        """获取会话类型统计"""
        type_stats = {}
        for session in self.active_sessions.values():
            session_type = session.session_type
            type_stats[session_type] = type_stats.get(session_type, 0) + 1
        return type_stats
    
    def cleanup_inactive_sessions(self, max_inactive_hours: int = 24) -> List[str]:
        """清理非活跃会话"""
        current_time = datetime.now()
        inactive_sessions = []
        
        for session_name, session_info in list(self.active_sessions.items()):
            inactive_duration = current_time - session_info.last_activity
            if inactive_duration.total_seconds() > max_inactive_hours * 3600:
                inactive_sessions.append(session_name)
                self.remove_session(session_name)
        
        self.last_cleanup = current_time
        return inactive_sessions