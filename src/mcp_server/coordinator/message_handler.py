"""
Message Handler - Clean inter-session communication

Focused on message passing and communication protocols.
Separated from session management concerns.
"""

import json
from typing import Dict, Any, List
from datetime import datetime
from .session_registry import SessionRegistry


class MessageHandler:
    """消息处理器 - 纯通信逻辑"""
    
    def __init__(self, registry: SessionRegistry):
        self.registry = registry
    
    def send_message(self, from_session: str, to_session: str, 
                    message: str, message_type: str = "general") -> Dict[str, Any]:
        """发送消息"""
        try:
            # 验证会话存在
            if not self._validate_sessions(from_session, to_session):
                return {"success": False, "error": "Invalid session names"}
            
            # 创建消息对象
            message_obj = self._create_message(from_session, to_session, message, message_type)
            
            # 添加到接收方消息队列
            self.registry.add_message_to_session(to_session, message_obj)
            
            # 更新发送方活动时间
            self.registry.update_session_activity(from_session)
            
            return {
                "success": True,
                "message_id": message_obj["id"],
                "from_session": from_session,
                "to_session": to_session,
                "timestamp": message_obj["timestamp"],
                "delivery_status": "delivered"
            }
            
        except Exception as e:
            return {"success": False, "error": f"Message send failed: {str(e)}"}
    
    def get_messages(self, session_name: str, unread_only: bool = True) -> Dict[str, Any]:
        """获取会话消息"""
        try:
            if not self._session_exists(session_name):
                return {"success": False, "error": "Session not found"}
            
            messages = self.registry.get_session_messages(session_name, unread_only)
            
            return {
                "success": True,
                "session_name": session_name,
                "message_count": len(messages),
                "messages": messages,
                "unread_only": unread_only,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {"success": False, "error": f"Get messages failed: {str(e)}"}
    
    def mark_message_read(self, session_name: str, message_id: str) -> Dict[str, Any]:
        """标记消息为已读"""
        try:
            if not self._session_exists(session_name):
                return {"success": False, "error": "Session not found"}
            
            self.registry.mark_message_as_read(session_name, message_id)
            
            return {
                "success": True,
                "session_name": session_name,
                "message_id": message_id,
                "marked_read_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {"success": False, "error": f"Mark read failed: {str(e)}"}
    
    def broadcast_message(self, from_session: str, message: str, 
                         target_type: str = "children") -> Dict[str, Any]:
        """广播消息"""
        try:
            if not self._session_exists(from_session):
                return {"success": False, "error": "Sender session not found"}
            
            targets = self._get_broadcast_targets(from_session, target_type)
            if not targets:
                return {"success": False, "error": "No target sessions found"}
            
            results = []
            for target in targets:
                result = self.send_message(from_session, target, message, "broadcast")
                results.append({
                    "target": target,
                    "success": result.get("success", False),
                    "message_id": result.get("message_id")
                })
            
            success_count = sum(1 for r in results if r["success"])
            
            return {
                "success": success_count > 0,
                "from_session": from_session,
                "target_type": target_type,
                "targets_found": len(targets),
                "successful_deliveries": success_count,
                "delivery_results": results,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {"success": False, "error": f"Broadcast failed: {str(e)}"}
    
    def get_conversation_history(self, session1: str, session2: str) -> Dict[str, Any]:
        """获取两个会话间的对话历史"""
        try:
            if not all([self._session_exists(session1), self._session_exists(session2)]):
                return {"success": False, "error": "One or both sessions not found"}
            
            # 获取双向消息
            messages1 = self.registry.get_session_messages(session1, unread_only=False)
            messages2 = self.registry.get_session_messages(session2, unread_only=False)
            
            # 筛选相关消息
            conversation = []
            
            for msg in messages1:
                if msg.get("from") == session2 or msg.get("to") == session2:
                    conversation.append(msg)
            
            for msg in messages2:
                if msg.get("from") == session1 or msg.get("to") == session1:
                    conversation.append(msg)
            
            # 按时间排序
            conversation.sort(key=lambda x: x.get("timestamp", ""))
            
            return {
                "success": True,
                "session1": session1,
                "session2": session2,
                "conversation_length": len(conversation),
                "conversation": conversation,
                "retrieved_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {"success": False, "error": f"Get conversation failed: {str(e)}"}
    
    def cleanup_old_messages(self, max_age_hours: int = 48) -> Dict[str, Any]:
        """清理旧消息"""
        try:
            current_time = datetime.now()
            cleaned_count = 0
            
            for session_name in list(self.registry.session_messages.keys()):
                messages = self.registry.session_messages[session_name]
                original_count = len(messages)
                
                # 过滤旧消息
                filtered_messages = []
                for msg in messages:
                    try:
                        msg_time = datetime.fromisoformat(msg.get("timestamp", ""))
                        age_hours = (current_time - msg_time).total_seconds() / 3600
                        if age_hours <= max_age_hours:
                            filtered_messages.append(msg)
                    except:
                        # 保留无效时间戳的消息
                        filtered_messages.append(msg)
                
                self.registry.session_messages[session_name] = filtered_messages
                cleaned_count += original_count - len(filtered_messages)
            
            return {
                "success": True,
                "cleaned_messages": cleaned_count,
                "max_age_hours": max_age_hours,
                "cleanup_time": current_time.isoformat()
            }
            
        except Exception as e:
            return {"success": False, "error": f"Cleanup failed: {str(e)}"}
    
    # === 私有辅助方法 ===
    
    def _validate_sessions(self, from_session: str, to_session: str) -> bool:
        """验证会话存在"""
        return self._session_exists(from_session) and self._session_exists(to_session)
    
    def _session_exists(self, session_name: str) -> bool:
        """检查会话是否存在"""
        return session_name in self.registry.active_sessions
    
    def _create_message(self, from_session: str, to_session: str, 
                       message: str, message_type: str) -> Dict[str, Any]:
        """创建消息对象"""
        return {
            "id": f"msg_{int(datetime.now().timestamp() * 1000)}",
            "from": from_session,
            "to": to_session,
            "message": message,
            "type": message_type,
            "timestamp": datetime.now().isoformat(),
            "read": False
        }
    
    def _get_broadcast_targets(self, from_session: str, target_type: str) -> List[str]:
        """获取广播目标"""
        if target_type == "children":
            return self.registry.get_child_sessions(from_session)
        elif target_type == "parent":
            parent = self.registry.get_parent_session(from_session)
            return [parent] if parent else []
        elif target_type == "siblings":
            parent = self.registry.get_parent_session(from_session)
            if parent:
                siblings = self.registry.get_child_sessions(parent)
                return [s for s in siblings if s != from_session]
            return []
        else:
            return []