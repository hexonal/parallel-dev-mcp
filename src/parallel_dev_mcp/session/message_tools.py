# -*- coding: utf-8 -*-
"""
消息发送MCP工具

@description 提供延时消息发送功能的FastMCP工具接口，实现发送状态追踪和查询
"""

import logging
import threading
from datetime import datetime
from typing import Dict, Any, Optional, List

# 获取FastMCP实例
from ..mcp_instance import mcp
from .delayed_message_sender import (
    MessageRequest, MessageStatus, get_delayed_message_sender
)
from .message_queue_manager import (
    get_message_queue_manager, QueueItemPriority
)

# 配置日志系统
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class MessageTracker:
    """
    消息状态追踪器

    记录每个消息的状态变化历史和详细信息
    """

    def __init__(self) -> None:
        """初始化消息追踪器"""
        # 1. 初始化状态存储
        self._message_history: Dict[str, List[Dict[str, Any]]] = {}
        self._current_status: Dict[str, MessageStatus] = {}
        self._lock = threading.Lock()

        # 2. 记录初始化信息
        logger.info("消息状态追踪器初始化完成")

    def track_status_change(
        self,
        request_id: str,
        old_status: Optional[MessageStatus],
        new_status: MessageStatus,
        additional_info: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        追踪状态变化

        Args:
            request_id: 请求ID
            old_status: 旧状态
            new_status: 新状态
            additional_info: 附加信息
        """
        with self._lock:
            # 1. 初始化历史记录（如果需要）
            if request_id not in self._message_history:
                self._message_history[request_id] = []

            # 2. 记录状态变化
            status_change = {
                "timestamp": datetime.now().isoformat(),
                "old_status": old_status.value if old_status else None,
                "new_status": new_status.value,
                "additional_info": additional_info or {}
            }

            self._message_history[request_id].append(status_change)
            self._current_status[request_id] = new_status

            # 3. 记录日志
            logger.info(f"状态变化追踪: {request_id} {old_status} -> {new_status}")

    def get_message_history(self, request_id: str) -> List[Dict[str, Any]]:
        """获取消息状态变化历史"""
        with self._lock:
            return self._message_history.get(request_id, []).copy()

    def get_current_status(self, request_id: str) -> Optional[MessageStatus]:
        """获取当前状态"""
        with self._lock:
            return self._current_status.get(request_id)

    def get_all_tracked_messages(self) -> Dict[str, MessageStatus]:
        """获取所有追踪的消息状态"""
        with self._lock:
            return self._current_status.copy()


# 全局消息追踪器实例
_global_message_tracker: Optional[MessageTracker] = None


def get_message_tracker() -> MessageTracker:
    """
    获取全局消息追踪器实例

    Returns:
        MessageTracker: 消息追踪器实例
    """
    global _global_message_tracker

    # 1. 初始化全局实例（如果需要）
    if _global_message_tracker is None:
        _global_message_tracker = MessageTracker()
        logger.info("初始化全局消息追踪器实例")

    return _global_message_tracker


@mcp.tool
def send_delayed_message_tool(
    session_name: str,
    message_content: str,
    delay_seconds: int = 10,
    priority: str = "normal",
    window_index: Optional[int] = None,
    pane_index: Optional[int] = None
) -> Dict[str, Any]:
    """
    发送延时消息工具

    将消息添加到延时发送队列，实现两阶段发送机制：先发送消息内容，延时后发送回车键。

    Args:
        session_name: 目标tmux会话名称
        message_content: 要发送的消息内容
        delay_seconds: 延时秒数，默认10秒
        priority: 消息优先级 (low/normal/high/urgent)
        window_index: 目标窗口索引（可选）
        pane_index: 目标面板索引（可选）

    Returns:
        Dict[str, Any]: 发送操作结果，包含队列信息和状态追踪ID
    """
    try:
        # 1. 参数验证
        if not session_name or not session_name.strip():
            return {
                "success": False,
                "error": "会话名称不能为空"
            }

        if not message_content or not message_content.strip():
            return {
                "success": False,
                "error": "消息内容不能为空"
            }

        # 2. 验证优先级
        priority_map = {
            "low": QueueItemPriority.LOW,
            "normal": QueueItemPriority.NORMAL,
            "high": QueueItemPriority.HIGH,
            "urgent": QueueItemPriority.URGENT
        }

        if priority not in priority_map:
            return {
                "success": False,
                "error": f"无效的优先级，必须是: {list(priority_map.keys())}"
            }

        # 3. 创建消息请求
        message_request = MessageRequest(
            session_name=session_name.strip(),
            message_content=message_content.strip(),
            window_index=window_index,
            pane_index=pane_index,
            delay_seconds=max(1, min(delay_seconds, 300))  # 限制在1-300秒
        )

        # 4. 获取队列管理器并添加消息
        queue_manager = get_message_queue_manager()
        queue_result = queue_manager.add_message(
            message_request=message_request,
            priority=priority_map[priority]
        )

        # 5. 初始化状态追踪
        if queue_result["success"]:
            message_tracker = get_message_tracker()
            message_tracker.track_status_change(
                request_id=message_request.request_id,
                old_status=None,
                new_status=MessageStatus.PENDING,
                additional_info={
                    "session_name": session_name,
                    "priority": priority,
                    "delay_seconds": delay_seconds
                }
            )

        # 6. 记录操作
        logger.info(f"延时消息工具调用: {message_request.request_id}, 会话: {session_name}")

        # 7. 返回结果
        return {
            "success": queue_result["success"],
            "message": queue_result.get("message", ""),
            "request_id": message_request.request_id,
            "session_name": session_name,
            "priority": priority,
            "delay_seconds": message_request.delay_seconds,
            "queue_position": queue_result.get("queue_position", 0),
            "estimated_wait_seconds": queue_result.get("estimated_wait_seconds", 0)
        }

    except Exception as e:
        # 8. 异常处理
        logger.error(f"发送延时消息工具异常: {e}")
        return {
            "success": False,
            "error": f"发送延时消息失败: {str(e)}"
        }


@mcp.tool
def get_message_status_tool(request_id: str) -> Dict[str, Any]:
    """
    获取消息状态工具

    查询指定消息的详细状态信息，包括发送进度和状态变化历史。

    Args:
        request_id: 消息请求ID

    Returns:
        Dict[str, Any]: 消息状态详细信息
    """
    try:
        # 1. 参数验证
        if not request_id or not request_id.strip():
            return {
                "success": False,
                "error": "请求ID不能为空"
            }

        request_id = request_id.strip()

        # 2. 获取延时发送器状态
        delayed_sender = get_delayed_message_sender()
        sender_status = delayed_sender.get_message_status(request_id)

        # 3. 获取追踪器历史
        message_tracker = get_message_tracker()
        status_history = message_tracker.get_message_history(request_id)
        current_tracked_status = message_tracker.get_current_status(request_id)

        # 4. 构建结果
        if sender_status is None and not status_history:
            return {
                "success": False,
                "error": f"未找到请求ID: {request_id}"
            }

        result = {
            "success": True,
            "request_id": request_id,
            "status_history": status_history,
            "tracked_status": current_tracked_status.value if current_tracked_status else None
        }

        # 5. 添加延时发送器状态（如果存在）
        if sender_status:
            result.update({
                "session_name": sender_status.session_name,
                "message_content": sender_status.message_content[:100] + "..." if len(sender_status.message_content) > 100 else sender_status.message_content,
                "current_status": sender_status.status.value,
                "created_at": sender_status.created_at.isoformat(),
                "message_sent_at": sender_status.message_sent_at.isoformat() if sender_status.message_sent_at else None,
                "enter_sent_at": sender_status.enter_sent_at.isoformat() if sender_status.enter_sent_at else None,
                "error_message": sender_status.error_message,
                "delay_seconds": sender_status.delay_seconds
            })

        # 6. 记录查询操作
        logger.info(f"查询消息状态: {request_id}")

        return result

    except Exception as e:
        # 7. 异常处理
        logger.error(f"获取消息状态工具异常: {e}")
        return {
            "success": False,
            "error": f"获取消息状态失败: {str(e)}"
        }


@mcp.tool
def get_queue_status_tool() -> Dict[str, Any]:
    """
    获取队列状态工具

    查询当前消息队列的状态和统计信息，包括待处理消息数量、处理进度等。

    Returns:
        Dict[str, Any]: 队列状态统计信息
    """
    try:
        # 1. 获取队列管理器状态
        queue_manager = get_message_queue_manager()
        queue_stats = queue_manager.get_queue_stats()

        # 2. 获取延时发送器状态
        delayed_sender = get_delayed_message_sender()
        active_messages = delayed_sender.get_all_active_messages()

        # 3. 获取追踪器状态
        message_tracker = get_message_tracker()
        tracked_messages = message_tracker.get_all_tracked_messages()

        # 4. 构建结果
        result = {
            "success": True,
            "queue_stats": {
                "total_items": queue_stats.total_items,
                "pending_items": queue_stats.pending_items,
                "processing_sessions": queue_stats.processing_sessions,
                "queue_status": queue_stats.queue_status.value,
                "last_processed_at": queue_stats.last_processed_at.isoformat() if queue_stats.last_processed_at else None,
                "total_processed": queue_stats.total_processed,
                "total_failed": queue_stats.total_failed,
                "queue_max_size": queue_stats.queue_max_size
            },
            "active_messages": {
                "count": len(active_messages),
                "messages": [
                    {
                        "request_id": request_id,
                        "session_name": status.session_name,
                        "status": status.status.value,
                        "created_at": status.created_at.isoformat(),
                        "delay_seconds": status.delay_seconds
                    }
                    for request_id, status in active_messages.items()
                ]
            },
            "tracked_messages": {
                "count": len(tracked_messages),
                "status_summary": {}
            }
        }

        # 5. 统计追踪消息状态分布
        status_summary = {}
        for status in tracked_messages.values():
            status_key = status.value
            status_summary[status_key] = status_summary.get(status_key, 0) + 1

        result["tracked_messages"]["status_summary"] = status_summary

        # 6. 记录查询操作
        logger.info("查询队列状态")

        return result

    except Exception as e:
        # 7. 异常处理
        logger.error(f"获取队列状态工具异常: {e}")
        return {
            "success": False,
            "error": f"获取队列状态失败: {str(e)}"
        }


@mcp.tool
def cancel_message_tool(request_id: str) -> Dict[str, Any]:
    """
    取消消息发送工具

    取消指定的延时消息发送任务。

    Args:
        request_id: 要取消的消息请求ID

    Returns:
        Dict[str, Any]: 取消操作结果
    """
    try:
        # 1. 参数验证
        if not request_id or not request_id.strip():
            return {
                "success": False,
                "error": "请求ID不能为空"
            }

        request_id = request_id.strip()

        # 2. 尝试取消延时发送
        delayed_sender = get_delayed_message_sender()
        cancel_success = delayed_sender.cancel_message(request_id)

        # 3. 更新追踪状态
        if cancel_success:
            message_tracker = get_message_tracker()
            current_status = message_tracker.get_current_status(request_id)
            message_tracker.track_status_change(
                request_id=request_id,
                old_status=current_status,
                new_status=MessageStatus.CANCELLED,
                additional_info={"cancelled_by": "user_request"}
            )

        # 4. 记录操作
        logger.info(f"取消消息发送: {request_id}, 成功: {cancel_success}")

        # 5. 返回结果
        return {
            "success": cancel_success,
            "message": "消息发送已取消" if cancel_success else "取消失败，消息可能已经发送或不存在",
            "request_id": request_id
        }

    except Exception as e:
        # 6. 异常处理
        logger.error(f"取消消息发送工具异常: {e}")
        return {
            "success": False,
            "error": f"取消消息发送失败: {str(e)}"
        }


@mcp.tool
def clear_message_queue_tool() -> Dict[str, Any]:
    """
    清空消息队列工具

    清空所有待处理的消息队列项。

    Returns:
        Dict[str, Any]: 清空操作结果
    """
    try:
        # 1. 获取队列管理器并清空
        queue_manager = get_message_queue_manager()
        clear_result = queue_manager.clear_queue()

        # 2. 记录操作
        logger.info("清空消息队列操作")

        # 3. 返回结果
        return {
            "success": clear_result["success"],
            "message": clear_result["message"],
            "normal_queue_cleared": clear_result.get("normal_queue_cleared", 0),
            "priority_queue_cleared": clear_result.get("priority_queue_cleared", 0)
        }

    except Exception as e:
        # 4. 异常处理
        logger.error(f"清空消息队列工具异常: {e}")
        return {
            "success": False,
            "error": f"清空消息队列失败: {str(e)}"
        }


@mcp.tool
def get_performance_metrics_tool() -> Dict[str, Any]:
    """
    获取性能指标工具

    查询系统性能指标，包括消息统计、重试统计和熔断器状态。

    Returns:
        Dict[str, Any]: 性能指标详细信息
    """
    try:
        # 1. 获取延时发送器指标
        delayed_sender = get_delayed_message_sender()
        sender_metrics = delayed_sender.get_performance_metrics()

        # 2. 获取队列管理器指标
        queue_manager = get_message_queue_manager()
        queue_stats = queue_manager.get_queue_stats()

        # 3. 获取消息追踪器指标
        message_tracker = get_message_tracker()
        tracked_messages = message_tracker.get_all_tracked_messages()

        # 4. 统计消息状态分布
        status_distribution = {}
        for status in tracked_messages.values():
            status_key = status.value
            status_distribution[status_key] = status_distribution.get(status_key, 0) + 1

        # 5. 构建结果
        result = {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "delayed_sender_metrics": sender_metrics,
            "queue_metrics": {
                "total_items": queue_stats.total_items,
                "pending_items": queue_stats.pending_items,
                "processing_sessions": queue_stats.processing_sessions,
                "queue_status": queue_stats.queue_status.value,
                "total_processed": queue_stats.total_processed,
                "total_failed": queue_stats.total_failed,
                "success_rate": queue_stats.total_processed / (queue_stats.total_processed + queue_stats.total_failed) if (queue_stats.total_processed + queue_stats.total_failed) > 0 else 0
            },
            "message_tracker_metrics": {
                "tracked_count": len(tracked_messages),
                "status_distribution": status_distribution
            }
        }

        # 6. 记录查询操作
        logger.info("查询性能指标")

        return result

    except Exception as e:
        # 7. 异常处理
        logger.error(f"获取性能指标工具异常: {e}")
        return {
            "success": False,
            "error": f"获取性能指标失败: {str(e)}"
        }


@mcp.tool
def get_system_logs_tool(
    level: Optional[str] = None,
    component: Optional[str] = None,
    request_id: Optional[str] = None,
    limit: int = 50
) -> Dict[str, Any]:
    """
    获取系统日志工具

    查询系统日志，支持按级别、组件和请求ID过滤。

    Args:
        level: 日志级别过滤 (debug/info/warning/error/critical)
        component: 组件名称过滤
        request_id: 请求ID过滤
        limit: 限制返回数量

    Returns:
        Dict[str, Any]: 日志查询结果
    """
    try:
        # 1. 参数验证
        from .message_logger import get_message_logger, LogLevel

        valid_levels = {level.value for level in LogLevel}
        if level and level not in valid_levels:
            return {
                "success": False,
                "error": f"无效的日志级别，必须是: {list(valid_levels)}"
            }

        # 2. 获取日志记录器
        message_logger = get_message_logger()

        # 3. 转换级别参数
        log_level = LogLevel(level) if level else None

        # 4. 查询日志
        logs = message_logger.get_logs(
            level=log_level,
            component=component,
            request_id=request_id,
            limit=limit
        )

        # 5. 转换为字典格式
        log_entries = [
            {
                "timestamp": log.timestamp.isoformat(),
                "level": log.level.value,
                "component": log.component,
                "operation": log.operation,
                "request_id": log.request_id,
                "session_name": log.session_name,
                "message": log.message,
                "data": log.data,
                "duration_ms": log.duration_ms,
                "error_code": log.error_code
            }
            for log in logs
        ]

        # 6. 记录查询操作
        logger.info(f"查询系统日志: level={level}, component={component}, limit={limit}")

        # 7. 返回结果
        return {
            "success": True,
            "total_count": len(log_entries),
            "filters": {
                "level": level,
                "component": component,
                "request_id": request_id,
                "limit": limit
            },
            "logs": log_entries
        }

    except Exception as e:
        # 8. 异常处理
        logger.error(f"获取系统日志工具异常: {e}")
        return {
            "success": False,
            "error": f"获取系统日志失败: {str(e)}"
        }