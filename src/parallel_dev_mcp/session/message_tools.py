# -*- coding: utf-8 -*-
"""
消息发送MCP工具

@description 提供延时消息发送功能的FastMCP工具接口，实现发送状态追踪和查询
"""

import logging
# 移除threading导入 - 不再需要复杂的锁机制
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


# 简化设计：移除复杂的MessageTracker，使用简单日志记录即可


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

        # 5. 简单日志记录（替代复杂状态追踪）
        if queue_result["success"]:
            logger.info(f"延时消息已添加到队列: {message_request.request_id}, 会话: {session_name}, 优先级: {priority}, 延时: {delay_seconds}秒")

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


# 移除 get_message_status_tool - 过度设计，使用简单日志即可


# 移除 get_queue_status_tool - 队列简单时不需要专门工具


# 移除 cancel_message_tool - 使用场景有限


# 移除 clear_message_queue_tool - 使用频率极低


# 移除 get_performance_metrics_tool - 可合并到系统状态工具中


# 移除 get_system_logs_tool - 直接查看日志文件更简单