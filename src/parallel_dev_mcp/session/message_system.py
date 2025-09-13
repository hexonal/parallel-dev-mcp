"""
Message System - 会话消息管理
从coordinator的消息处理能力完美融合而来，提供会话间通信能力。
每个函数都是独立的MCP工具，Claude可以直接调用。
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
import uuid

# 复用已重构的注册中心组件
from .._internal.session_registry import SessionRegistry

# MCP工具装饰器
def mcp_tool(name: str = None, description: str = None):
    """MCP工具装饰器"""
    def decorator(func):
        func.mcp_tool_name = name or func.__name__
        func.mcp_tool_description = description or func.__doc__
        return func
    return decorator

# 全局会话注册中心
_session_registry = SessionRegistry()

@mcp_tool(
    name="send_message_to_session",
    description="向指定会话发送消息，支持会话间通信"
)
def send_message_to_session(
    session_name: str,
    message_content: str,
    sender_session: str = None,
    message_type: str = "info",
    priority: str = "normal"
) -> Dict[str, Any]:
    """
    发送消息到会话 - 会话间通信核心功能
    
    Args:
        session_name: 目标会话名称
        message_content: 消息内容
        sender_session: 发送者会话名称
        message_type: 消息类型 (info/warning/error/command)
        priority: 消息优先级 (low/normal/high/urgent)
    """
    try:
        # 检查目标会话是否存在
        session_info = _session_registry.get_session_info(session_name)
        if not session_info:
            return {
                "success": False,
                "error": f"目标会话不存在: {session_name}"
            }
        
        # 构建消息对象
        message = {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "sender": sender_session or "system",
            "recipient": session_name,
            "type": message_type,
            "priority": priority,
            "content": message_content,
            "read": False,
            "delivered": True
        }
        
        # 添加消息到会话
        _session_registry.add_message_to_session(session_name, message)
        
        # 如果是命令类型消息，可能需要特殊处理
        if message_type == "command":
            command_result = _handle_command_message(session_name, message_content)
            message["command_result"] = command_result
        
        result = {
            "success": True,
            "message_id": message["id"],
            "session_name": session_name,
            "sender": message["sender"],
            "type": message_type,
            "priority": priority,
            "timestamp": message["timestamp"]
        }
        
        return result
        
    except Exception as e:
        return {
            "success": False,
            "error": f"发送消息失败: {str(e)}"
        }

@mcp_tool(
    name="get_session_messages",
    description="获取会话消息，支持未读消息过滤和分页"
)
def get_session_messages(
    session_name: str,
    unread_only: bool = False,
    message_type: str = None,
    limit: int = None,
    offset: int = 0
) -> Dict[str, Any]:
    """
    获取会话消息 - 消息检索和过滤
    
    Args:
        session_name: 会话名称
        unread_only: 只获取未读消息
        message_type: 消息类型过滤
        limit: 消息数量限制
        offset: 消息偏移量（用于分页）
    """
    try:
        # 检查会话是否存在
        session_info = _session_registry.get_session_info(session_name)
        if not session_info:
            return {
                "success": False,
                "error": f"会话不存在: {session_name}"
            }
        
        # 获取消息列表
        messages = _session_registry.get_session_messages(session_name, unread_only)
        
        # 按消息类型过滤
        if message_type:
            messages = [msg for msg in messages if msg.get("type") == message_type]
        
        # 按优先级排序（urgent > high > normal > low）
        priority_order = {"urgent": 0, "high": 1, "normal": 2, "low": 3}
        messages.sort(key=lambda x: (
            priority_order.get(x.get("priority", "normal"), 2),
            x.get("timestamp", "")
        ))
        
        # 分页处理
        total_count = len(messages)
        if limit:
            messages = messages[offset:offset + limit]
        
        # 统计信息
        unread_count = sum(1 for msg in messages if not msg.get("read", False))
        type_counts = {}
        for msg in messages:
            msg_type = msg.get("type", "unknown")
            type_counts[msg_type] = type_counts.get(msg_type, 0) + 1
        
        result = {
            "success": True,
            "session_name": session_name,
            "messages": messages,
            "total_count": total_count,
            "returned_count": len(messages),
            "unread_count": unread_count,
            "type_counts": type_counts,
            "filters": {
                "unread_only": unread_only,
                "message_type": message_type,
                "limit": limit,
                "offset": offset
            }
        }
        
        return result
        
    except Exception as e:
        return {
            "success": False,
            "error": f"获取会话消息失败: {str(e)}"
        }

@mcp_tool(
    name="mark_message_read",
    description="标记消息为已读状态"
)
def mark_message_read(
    session_name: str,
    message_id: str = None,
    mark_all: bool = False
) -> Dict[str, Any]:
    """
    标记消息已读 - 消息状态管理
    
    Args:
        session_name: 会话名称
        message_id: 消息ID（单个消息）
        mark_all: 标记所有消息为已读
    """
    try:
        # 检查会话是否存在
        session_info = _session_registry.get_session_info(session_name)
        if not session_info:
            return {
                "success": False,
                "error": f"会话不存在: {session_name}"
            }
        
        if mark_all:
            # 标记所有消息为已读
            messages = _session_registry.get_session_messages(session_name)
            marked_count = 0
            
            for message in messages:
                if not message.get("read", False):
                    _session_registry.mark_message_as_read(session_name, message["id"])
                    marked_count += 1
            
            result = {
                "success": True,
                "session_name": session_name,
                "action": "mark_all_read",
                "marked_count": marked_count,
                "total_messages": len(messages)
            }
        
        elif message_id:
            # 标记单个消息为已读
            _session_registry.mark_message_as_read(session_name, message_id)
            
            result = {
                "success": True,
                "session_name": session_name,
                "action": "mark_single_read",
                "message_id": message_id
            }
        
        else:
            return {
                "success": False,
                "error": "必须指定message_id或设置mark_all=True"
            }
        
        return result
        
    except Exception as e:
        return {
            "success": False,
            "error": f"标记消息已读失败: {str(e)}"
        }


# === 内部辅助函数 ===

def _handle_command_message(session_name: str, command: str) -> Dict[str, Any]:
    """处理命令类型消息"""
    try:
        # 简单的命令处理逻辑
        command_lower = command.lower().strip()
        
        if command_lower == "status":
            session_info = _session_registry.get_session_info(session_name)
            return {
                "command": "status",
                "result": "success",
                "data": session_info.to_dict() if session_info else None
            }
        
        elif command_lower == "ping":
            return {
                "command": "ping",
                "result": "success",
                "response": "pong",
                "timestamp": datetime.now().isoformat()
            }
        
        elif command_lower.startswith("echo "):
            echo_text = command[5:]
            return {
                "command": "echo",
                "result": "success",
                "response": echo_text
            }
        
        else:
            return {
                "command": command,
                "result": "unknown",
                "message": "Unknown command"
            }
    
    except Exception as e:
        return {
            "command": command,
            "result": "error",
            "error": str(e)
        }

def _match_session_pattern(session_names: List[str], pattern: str) -> List[str]:
    """根据模式匹配会话名称"""
    import fnmatch
    
    matched = []
    for name in session_names:
        if fnmatch.fnmatch(name, pattern):
            matched.append(name)
    
    return matched