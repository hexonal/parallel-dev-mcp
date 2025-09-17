# -*- coding: utf-8 -*-
"""
消息队列管理器

@description 管理并发消息队列，处理多个发送请求的排队和调度
"""

import logging
import threading
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, Set
from enum import Enum, unique
from collections import deque
from pydantic import BaseModel, Field, field_validator

from .delayed_message_sender import MessageRequest, get_delayed_message_sender

# 配置日志系统
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@unique
class QueueItemPriority(Enum):
    """队列项优先级枚举"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


@unique
class QueueStatus(Enum):
    """队列状态枚举"""
    IDLE = "idle"
    PROCESSING = "processing"
    FULL = "full"
    ERROR = "error"


class QueueItem(BaseModel):
    """队列项数据模型"""

    item_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="队列项ID")
    message_request: MessageRequest = Field(..., description="消息发送请求")
    priority: QueueItemPriority = Field(QueueItemPriority.NORMAL, description="优先级")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    session_key: str = Field(..., description="会话标识")
    retry_count: int = Field(0, description="重试次数", ge=0)
    max_retries: int = Field(3, description="最大重试次数", ge=0, le=10)

    def __init__(self, **data: Any) -> None:
        # 1. 自动生成session_key
        if 'session_key' not in data and 'message_request' in data:
            request = data['message_request']
            if isinstance(request, MessageRequest):
                data['session_key'] = request.session_name
            elif isinstance(request, dict):
                data['session_key'] = request.get('session_name', 'unknown')

        super().__init__(**data)

    @field_validator('session_key')
    @classmethod
    def validate_session_key(cls, v: str) -> str:
        """验证会话标识"""
        if not v or not v.strip():
            raise ValueError('会话标识不能为空')
        return v.strip()


class QueueStats(BaseModel):
    """队列统计信息数据模型"""

    total_items: int = Field(0, description="总队列项数", ge=0)
    pending_items: int = Field(0, description="待处理项数", ge=0)
    processing_sessions: int = Field(0, description="正在处理的会话数", ge=0)
    queue_status: QueueStatus = Field(QueueStatus.IDLE, description="队列状态")
    last_processed_at: Optional[datetime] = Field(None, description="最后处理时间")
    total_processed: int = Field(0, description="总处理数", ge=0)
    total_failed: int = Field(0, description="总失败数", ge=0)
    queue_max_size: int = Field(1000, description="队列最大容量")


class MessageQueueManager:
    """
    消息队列管理器

    提供FIFO消息队列管理，支持优先级和并发控制
    """

    def __init__(self, max_queue_size: int = 1000, max_concurrent_sessions: int = 10) -> None:
        """
        初始化消息队列管理器

        Args:
            max_queue_size: 队列最大容量
            max_concurrent_sessions: 最大并发会话数
        """
        # 1. 初始化队列配置
        self.max_queue_size = max_queue_size
        self.max_concurrent_sessions = max_concurrent_sessions

        # 2. 初始化队列存储
        self._queue: deque[QueueItem] = deque()
        self._priority_queue: deque[QueueItem] = deque()
        self._processing_sessions: Set[str] = set()

        # 3. 初始化统计信息
        self._stats = QueueStats(queue_max_size=max_queue_size)

        # 4. 初始化线程安全机制
        self._lock = threading.Lock()
        self._processing_lock = threading.Lock()

        # 5. 初始化处理状态
        self._is_processing = False
        self._stop_processing = False

        # 6. 获取延时发送器
        self._delayed_sender = get_delayed_message_sender()

        # 7. 记录初始化信息
        logger.info(f"消息队列管理器初始化完成: 最大队列={max_queue_size}, 最大并发={max_concurrent_sessions}")

    def add_message(self, message_request: MessageRequest, priority: QueueItemPriority = QueueItemPriority.NORMAL) -> Dict[str, Any]:
        """
        添加消息到队列

        Args:
            message_request: 消息发送请求
            priority: 消息优先级

        Returns:
            Dict[str, Any]: 添加操作结果
        """
        try:
            with self._lock:
                # 1. 检查队列容量
                if len(self._queue) + len(self._priority_queue) >= self.max_queue_size:
                    self._stats.queue_status = QueueStatus.FULL
                    return {
                        "success": False,
                        "message": "队列已满，无法添加新消息",
                        "queue_size": len(self._queue) + len(self._priority_queue),
                        "max_size": self.max_queue_size
                    }

                # 2. 创建队列项
                queue_item = QueueItem(
                    message_request=message_request,
                    priority=priority,
                    session_key=message_request.session_name
                )

                # 3. 根据优先级添加到对应队列
                if priority in [QueueItemPriority.HIGH, QueueItemPriority.URGENT]:
                    self._priority_queue.append(queue_item)
                else:
                    self._queue.append(queue_item)

                # 4. 更新统计信息
                self._stats.total_items = len(self._queue) + len(self._priority_queue)
                self._stats.pending_items = self._stats.total_items - len(self._processing_sessions)

                # 5. 启动队列处理（如果未启动）
                self._start_processing_if_needed()

                # 6. 记录添加操作
                logger.info(f"消息已添加到队列: {queue_item.item_id}, 会话: {message_request.session_name}")

                # 7. 返回成功结果
                return {
                    "success": True,
                    "message": "消息已添加到队列",
                    "item_id": queue_item.item_id,
                    "session_name": message_request.session_name,
                    "priority": priority.value,
                    "queue_position": self._calculate_queue_position(queue_item),
                    "estimated_wait_seconds": self._estimate_wait_time(queue_item)
                }

        except Exception as e:
            # 8. 异常处理
            logger.error(f"添加消息到队列失败: {e}")
            self._stats.queue_status = QueueStatus.ERROR
            return {
                "success": False,
                "message": f"添加消息到队列失败: {str(e)}"
            }

    def process_queue(self) -> None:
        """异步处理队列中的消息"""
        try:
            with self._processing_lock:
                # 1. 检查是否正在处理
                if self._is_processing:
                    return

                self._is_processing = True
                self._stop_processing = False

            # 2. 启动处理循环
            logger.info("开始处理消息队列")
            self._stats.queue_status = QueueStatus.PROCESSING

            while not self._stop_processing:
                try:
                    # 3. 获取下一个可处理的消息
                    queue_item = self._get_next_processable_item()

                    if queue_item is None:
                        # 4. 队列为空或无可处理项，暂停处理
                        self._stats.queue_status = QueueStatus.IDLE
                        break

                    # 5. 处理消息
                    self._process_queue_item(queue_item)

                except Exception as e:
                    # 6. 处理异常
                    logger.error(f"处理队列项异常: {e}")
                    self._stats.total_failed += 1

        except Exception as e:
            # 7. 处理循环异常
            logger.error(f"队列处理循环异常: {e}")
            self._stats.queue_status = QueueStatus.ERROR

        finally:
            # 8. 清理处理状态
            with self._processing_lock:
                self._is_processing = False

            logger.info("队列处理循环结束")

    def _get_next_processable_item(self) -> Optional[QueueItem]:
        """获取下一个可处理的队列项"""
        with self._lock:
            # 1. 检查并发限制
            if len(self._processing_sessions) >= self.max_concurrent_sessions:
                return None

            # 2. 优先处理高优先级队列
            if self._priority_queue:
                for _ in range(len(self._priority_queue)):
                    item = self._priority_queue.popleft()
                    if item.session_key not in self._processing_sessions:
                        self._processing_sessions.add(item.session_key)
                        return item
                    else:
                        # 会话正在处理，重新放回队列末尾
                        self._priority_queue.append(item)

            # 3. 处理普通优先级队列
            if self._queue:
                for _ in range(len(self._queue)):
                    item = self._queue.popleft()
                    if item.session_key not in self._processing_sessions:
                        self._processing_sessions.add(item.session_key)
                        return item
                    else:
                        # 会话正在处理，重新放回队列末尾
                        self._queue.append(item)

            # 4. 无可处理项
            return None

    def _process_queue_item(self, queue_item: QueueItem) -> None:
        """处理单个队列项"""
        try:
            # 1. 创建完成回调
            def completion_callback(request_id: str, success: bool) -> None:
                self._on_message_completed(queue_item, success)

            # 2. 发送延时消息
            result = self._delayed_sender.send_delayed_message(
                queue_item.message_request,
                completion_callback
            )

            # 3. 检查发送结果
            if not result["success"]:
                # 发送失败，立即完成处理
                self._on_message_completed(queue_item, False)

        except Exception as e:
            # 4. 异常处理
            logger.error(f"处理队列项失败: {queue_item.item_id}, 错误: {e}")
            self._on_message_completed(queue_item, False)

    def _on_message_completed(self, queue_item: QueueItem, success: bool) -> None:
        """消息完成回调处理"""
        try:
            with self._lock:
                # 1. 释放会话锁定
                self._processing_sessions.discard(queue_item.session_key)

                # 2. 更新统计信息
                self._stats.processing_sessions = len(self._processing_sessions)
                self._stats.last_processed_at = datetime.now()

                if success:
                    self._stats.total_processed += 1
                    logger.info(f"消息处理成功: {queue_item.item_id}")
                else:
                    self._stats.total_failed += 1
                    logger.warning(f"消息处理失败: {queue_item.item_id}")

                # 3. 更新队列状态
                total_items = len(self._queue) + len(self._priority_queue)
                self._stats.total_items = total_items
                self._stats.pending_items = total_items - len(self._processing_sessions)

                # 4. 检查是否需要继续处理
                if total_items > 0 and len(self._processing_sessions) < self.max_concurrent_sessions:
                    self._continue_processing()

        except Exception as e:
            logger.error(f"完成回调处理异常: {e}")

    def _calculate_queue_position(self, queue_item: QueueItem) -> int:
        """计算队列位置"""
        with self._lock:
            # 1. 计算在优先级队列中的位置
            if queue_item.priority in [QueueItemPriority.HIGH, QueueItemPriority.URGENT]:
                return len(self._priority_queue)

            # 2. 计算在普通队列中的位置（需要加上优先级队列长度）
            return len(self._priority_queue) + len(self._queue)

    def _estimate_wait_time(self, queue_item: QueueItem) -> int:
        """估算等待时间（秒）"""
        # 1. 基础等待时间（假设每个消息处理需要15秒：消息发送+10秒延时+处理时间）
        base_processing_time = 15

        # 2. 计算队列位置
        position = self._calculate_queue_position(queue_item)

        # 3. 考虑并发处理能力
        estimated_seconds = (position // self.max_concurrent_sessions) * base_processing_time

        return max(estimated_seconds, 0)

    def _start_processing_if_needed(self) -> None:
        """启动队列处理（如果需要）"""
        if not self._is_processing and (self._queue or self._priority_queue):
            # 在新线程中启动处理
            processing_thread = threading.Thread(target=self.process_queue, daemon=True)
            processing_thread.start()

    def _continue_processing(self) -> None:
        """继续处理队列"""
        if not self._is_processing:
            self._start_processing_if_needed()

    def get_queue_stats(self) -> QueueStats:
        """获取队列统计信息"""
        with self._lock:
            # 1. 更新当前统计
            self._stats.total_items = len(self._queue) + len(self._priority_queue)
            self._stats.pending_items = self._stats.total_items - len(self._processing_sessions)
            self._stats.processing_sessions = len(self._processing_sessions)

            return self._stats.model_copy()

    def clear_queue(self) -> Dict[str, Any]:
        """清空队列"""
        try:
            with self._lock:
                # 1. 清空队列
                normal_count = len(self._queue)
                priority_count = len(self._priority_queue)

                self._queue.clear()
                self._priority_queue.clear()

                # 2. 重置统计信息
                self._stats.total_items = 0
                self._stats.pending_items = 0
                self._stats.queue_status = QueueStatus.IDLE

                # 3. 记录清空操作
                total_cleared = normal_count + priority_count
                logger.info(f"队列已清空，移除 {total_cleared} 个项目")

                return {
                    "success": True,
                    "message": f"队列已清空，移除 {total_cleared} 个项目",
                    "normal_queue_cleared": normal_count,
                    "priority_queue_cleared": priority_count
                }

        except Exception as e:
            logger.error(f"清空队列失败: {e}")
            return {
                "success": False,
                "message": f"清空队列失败: {str(e)}"
            }

    def stop_processing(self) -> None:
        """停止队列处理"""
        self._stop_processing = True
        logger.info("队列处理停止请求已发送")


# 全局消息队列管理器实例
_global_queue_manager: Optional[MessageQueueManager] = None


def get_message_queue_manager() -> MessageQueueManager:
    """
    获取全局消息队列管理器实例

    Returns:
        MessageQueueManager: 消息队列管理器实例
    """
    global _global_queue_manager

    # 1. 初始化全局实例（如果需要）
    if _global_queue_manager is None:
        _global_queue_manager = MessageQueueManager(
            max_queue_size=1000,
            max_concurrent_sessions=10
        )
        logger.info("初始化全局消息队列管理器实例")

    return _global_queue_manager