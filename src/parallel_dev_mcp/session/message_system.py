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

# 使用全局共享的注册中心组件
from .._internal.global_registry import get_global_registry
# 使用优化的消息发送器
from .._internal.tmux_message_sender import TmuxMessageSender
from .._internal import SessionNaming
import threading
from datetime import datetime
import os
from ..session.prompts import master_message, child_message

# MCP工具装饰器
def mcp_tool(name: str = None, description: str = None):
    """MCP工具装饰器"""
    def decorator(func):
        func.mcp_tool_name = name or func.__name__
        func.mcp_tool_description = description or func.__doc__
        return func
    return decorator

# 全局共享会话注册中心
_session_registry = get_global_registry()


def _parse_iso(ts: str) -> datetime | None:
    """解析 ISO 时间，失败返回 None（≤50行）"""
    try:
        return datetime.fromisoformat(ts)
    except Exception:
        return None


def _master_for_session(session_name: str) -> str | None:
    """根据会话名推导主会话（≤50行）"""
    info = SessionNaming.parse_session_name(session_name)
    pid = info.get("project_id")
    if not pid:
        return None
    return session_name if info.get("session_type") == "master" else SessionNaming.master_session(pid)


def _schedule_master_continue(session_name: str, reset_iso: str) -> None:
    """当命中限流时，定时向主会话发送“继续”指令（≤50行）"""
    dt = _parse_iso(reset_iso)
    master = _master_for_session(session_name)
    if not dt or not master:
        return
    delay = max(0.0, (dt - datetime.now()).total_seconds())
    message = os.environ.get("CONTINUE_MESSAGE", "continue")

    def _job():
        try:
            # 使用 direct 文本发送“继续”指令到主会话
            TmuxMessageSender.send_message_raw(master, message)
        except Exception:
            pass

    t = threading.Timer(delay, _job)
    t.daemon = True
    t.start()

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

@mcp_tool(
    name="send_tmux_message_optimized",
    description="使用优化方式向tmux会话发送消息（无引号、无echo、分步发送）"
)
def send_tmux_message_optimized(
    session_name: str,
    message: str,
    message_type: str = "direct",
    event_name: str = None,
    auto_hi_enabled: bool = False
) -> Dict[str, Any]:
    """
    使用优化的发送器向tmux会话发送消息

    **核心优化**:
    - 不使用引号包装消息
    - 不使用echo命令
    - 分两次send-keys：内容 + 回车
    - 避免特殊字符转义问题

    Args:
        session_name: 目标tmux会话名称
        message: 要发送的消息内容
        message_type: 消息类型 ("direct", "command", "text")
        event_name: 业务事件名称（如 "SessionEnd"），用于触发自动 hi 逻辑
        auto_hi_enabled: 是否启用自动 hi 逻辑（默认关闭）

    Returns:
        Dict[str, Any]: 发送结果
    """
    try:
        # 根据消息类型选择发送方法
        if message_type == "command":
            result = TmuxMessageSender.send_command_input(session_name, message)
        elif message_type == "text":
            result = TmuxMessageSender.send_text_input(session_name, message)
        else:  # "direct" 或其他
            result = TmuxMessageSender.send_message_raw(session_name, message)

        auto_hi_sent = False
        auto_hi_reason = None

        if result.get("success"):
            # 仅当是特定事件（如 SessionEnd）且启用时，执行频率统计与自动 hi 触发
            if auto_hi_enabled and (event_name or "").lower() == "sessionend":
                count = TmuxMessageSender._record_session_end_call()
                if TmuxMessageSender._should_trigger_auto_hi():
                    hi_result = TmuxMessageSender.send_auto_hi(session_name)
                    if hi_result.get("success"):
                        auto_hi_sent = True
                        auto_hi_reason = "High frequency calls detected - compact phase optimization"
                        TmuxMessageSender._reset_frequency_tracker()
            return {
                "success": True,
                "session_name": session_name,
                "message_type": message_type,
                "message_length": len(message),
                "message_preview": message[:50] + "..." if len(message) > 50 else message,
                "method": "optimized_tmux_sender",
                "timestamp": datetime.now().isoformat(),
                **({"auto_hi_sent": True, "auto_hi_reason": auto_hi_reason} if auto_hi_sent else {})
            }
        else:
            # 如果是网关限流导致的跳过，直接透出关键信息
            if result.get("action") == "skipped_due_to_limit":
                return {
                    "success": False,
                    "error": result.get("error"),
                    "session_name": session_name,
                    "limit_triggered": True,
                    "limit_reset_time": result.get("limit_reset_time"),
                    "action": "skipped_due_to_limit"
                }
            # 命中限流：调度“继续”指令到主会话
            if result.get("limit_triggered") and result.get("limit_reset_time"):
                _schedule_master_continue(session_name, result.get("limit_reset_time"))
            return {
                "success": False,
                "error": f"优化发送失败: {result.get('error', 'Unknown error')}",
                "session_name": session_name,
                "original_error": result.get("error")
            }

    except Exception as e:
        return {
            "success": False,
            "error": f"优化发送异常: {str(e)}",
            "session_name": session_name,
            "exception_type": type(e).__name__
        }

@mcp_tool(
    name="broadcast_tmux_message",
    description="向项目所有相关tmux会话广播消息"
)
def broadcast_tmux_message(
    project_id: str,
    message: str,
    include_master: bool = True,
    include_children: bool = True
) -> Dict[str, Any]:
    """
    向项目的所有相关tmux会话广播消息

    Args:
        project_id: 项目ID
        message: 广播消息内容
        include_master: 是否包含主会话
        include_children: 是否包含子会话

    Returns:
        Dict[str, Any]: 广播结果统计
    """
    try:
        result = TmuxMessageSender.broadcast_to_project_sessions(
            project_id, message, include_master, include_children
        )

        if result.get("success"):
            return {
                "success": True,
                "operation": "broadcast_tmux_message",
                "project_id": project_id,
                "message_length": len(message),
                "broadcast_summary": {
                    "total_sessions": result.get("total_sessions", 0),
                    "success_count": result.get("success_count", 0),
                    "failed_count": result.get("failed_count", 0),
                    "success_rate": result.get("success_rate", "0%")
                },
                "target_sessions": result.get("target_sessions", []),
                "failed_sessions": result.get("failed_sessions", []),
                "include_master": include_master,
                "include_children": include_children,
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "success": False,
                "error": f"广播失败: {result.get('error', 'Unknown error')}",
                "project_id": project_id,
                "original_error": result.get("error")
            }

    except Exception as e:
        return {
            "success": False,
            "error": f"广播异常: {str(e)}",
            "project_id": project_id,
            "exception_type": type(e).__name__
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
@mcp_tool(
    name="send_tmux_message_prompted",
    description="基于@mcp.prompt模板生成消息并发送（≤50行）"
)
def send_tmux_message_prompted(
    session_name: str,
    task: str | None = None,
    substitute: bool = False,
    message_type: str = "direct"
) -> Dict[str, Any]:
    """根据会话类型选择主/子模板，插入 {task}（可选），再发送。"""
    try:
        s_type = SessionNaming.get_session_type(session_name)
        msgs = master_message(task=task, substitute=substitute) if s_type == "master" else child_message(task=task, substitute=substitute)
        # 模板缺失则跳过，不影响业务
        if not msgs:
            return {
                "success": True,
                "skipped": True,
                "reason": "template_missing",
                "session_name": session_name,
                "session_type": s_type,
            }
        content = (msgs[0].get("content") if isinstance(msgs, list) and msgs else "") or ""
        if message_type == "command":
            return TmuxMessageSender.send_command_input(session_name, content)
        elif message_type == "text":
            return TmuxMessageSender.send_text_input(session_name, content)
        res = TmuxMessageSender.send_message_raw(session_name, content)
        # 模板路径下也可能触发限流，调度“继续”
        if res and not res.get("success") and res.get("limit_triggered") and res.get("limit_reset_time"):
            _schedule_master_continue(session_name, res.get("limit_reset_time"))
        return res
    except Exception as e:
        return {"success": False, "error": f"模板发送失败: {str(e)}", "session_name": session_name}
