# -*- coding: utf-8 -*-
"""
延迟消息发送器

@description 提供带有延迟机制的消息发送功能，支持队列管理和批量发送
"""

import asyncio
import logging
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Callable, Any, Union
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum, unique
import uuid
import json

# 配置日志系统
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@unique
class MessagePriority(Enum):
    """消息优先级枚举"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


@unique
class MessageStatus(Enum):
    """消息状态枚举"""
    PENDING = "pending"
    QUEUED = "queued"
    SENDING = "sending"
    SENT = "sent"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MessageSendRequest(BaseModel):
    """消息发送请求数据模型"""

    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="消息ID")
    content: str = Field(..., description="消息内容", min_length=1)
    target: str = Field(..., description="发送目标（会话ID、端点等）")
    delay_seconds: float = Field(0.0, description="延迟秒数", ge=0, le=3600)
    priority: MessagePriority = Field(MessagePriority.NORMAL, description="消息优先级")
    max_retries: int = Field(3, description="最大重试次数", ge=0, le=10)
    timeout_seconds: float = Field(30.0, description="发送超时秒数", ge=1, le=300)
    metadata: Dict[str, Any] = Field(default_factory=dict, description="附加元数据")
    scheduled_time: Optional[datetime] = Field(None, description="预定发送时间")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")

    model_config = ConfigDict(
        # json_encoders deprecated in V2 - datetime fields will use default serialization
    )


class MessageSendResult(BaseModel):
    """消息发送结果数据模型"""

    message_id: str = Field(..., description="消息ID")
    status: MessageStatus = Field(..., description="发送状态")
    success: bool = Field(False, description="是否发送成功")
    sent_at: Optional[datetime] = Field(None, description="发送时间")
    response_data: Optional[Dict[str, Any]] = Field(None, description="响应数据")
    error_message: Optional[str] = Field(None, description="错误消息")
    attempt_count: int = Field(0, description="尝试次数", ge=0)
    total_delay_seconds: float = Field(0.0, description="总延迟时间", ge=0)
    execution_time_ms: float = Field(0.0, description="执行时间（毫秒）", ge=0)

    model_config = ConfigDict(
        # json_encoders deprecated in V2 - datetime fields will use default serialization
    )


class DelayConfig(BaseModel):
    """延迟配置数据模型"""

    default_delay_seconds: float = Field(10.0, description="默认延迟秒数", ge=0, le=300)
    max_queue_size: int = Field(1000, description="最大队列大小", ge=10, le=10000)
    batch_size: int = Field(10, description="批量处理大小", ge=1, le=100)
    processing_interval_seconds: float = Field(1.0, description="处理间隔秒数", ge=0.1, le=60)
    max_concurrent_sends: int = Field(5, description="最大并发发送数", ge=1, le=50)
    queue_persistence_enabled: bool = Field(True, description="是否启用队列持久化")
    queue_storage_path: str = Field(".message_queue.json", description="队列存储文件路径")
    auto_retry_enabled: bool = Field(True, description="是否启用自动重试")

    model_config = ConfigDict()


class DelayedMessageSender:
    """
    延迟消息发送器

    提供延迟发送、队列管理、批量处理等功能
    """

    def __init__(self, config: Optional[DelayConfig] = None) -> None:
        """
        初始化延迟消息发送器

        Args:
            config: 延迟配置
        """
        # 1. 设置配置
        self.config = config or DelayConfig()

        # 2. 初始化消息队列
        self.message_queue: List[MessageSendRequest] = []
        self.sending_queue: Dict[str, MessageSendRequest] = {}
        self.results_history: Dict[str, MessageSendResult] = {}

        # 3. 初始化线程控制
        self.queue_lock = threading.RLock()
        self.is_running = False
        self.processor_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()

        # 4. 初始化发送器
        self.send_callback: Optional[Callable[[MessageSendRequest], MessageSendResult]] = None
        self.concurrent_sends = 0
        self.concurrent_lock = threading.Lock()

        # 5. 初始化存储
        if self.config.queue_persistence_enabled:
            self.storage_path = Path(self.config.queue_storage_path)
            self._load_queue()

        # 6. 记录初始化信息
        logger.info(f"延迟消息发送器初始化: 默认延迟={self.config.default_delay_seconds}秒")

    def send_message(self, request: MessageSendRequest) -> str:
        """
        发送消息（加入队列）

        Args:
            request: 消息发送请求

        Returns:
            str: 消息ID
        """
        # 1. 设置预定发送时间
        if request.delay_seconds > 0:
            request.scheduled_time = datetime.now() + timedelta(seconds=request.delay_seconds)
        elif not request.scheduled_time:
            request.scheduled_time = datetime.now()

        # 2. 检查队列容量
        with self.queue_lock:
            if len(self.message_queue) >= self.config.max_queue_size:
                logger.warning(f"消息队列已满: {len(self.message_queue)}")
                raise ValueError("消息队列已满")

            # 3. 添加到队列
            self.message_queue.append(request)
            self.message_queue.sort(key=lambda msg: msg.scheduled_time or datetime.now())

        # 4. 保存队列
        if self.config.queue_persistence_enabled:
            self._save_queue()

        # 5. 记录入队信息
        logger.info(f"消息已加入队列: {request.message_id}, 延迟: {request.delay_seconds}秒")

        # 6. 返回消息ID
        return request.message_id

    def send_delayed_message(
        self,
        content: str,
        target: str,
        delay_seconds: Optional[float] = None,
        priority: MessagePriority = MessagePriority.NORMAL,
        **kwargs
    ) -> str:
        """
        便捷方法：发送延迟消息

        Args:
            content: 消息内容
            target: 发送目标
            delay_seconds: 延迟秒数，None使用默认值
            priority: 消息优先级
            **kwargs: 其他参数

        Returns:
            str: 消息ID
        """
        # 1. 创建发送请求
        request = MessageSendRequest(
            content=content,
            target=target,
            delay_seconds=delay_seconds or self.config.default_delay_seconds,
            priority=priority,
            max_retries=kwargs.get("max_retries", 3),
            timeout_seconds=kwargs.get("timeout_seconds", 30.0),
            metadata=kwargs.get("metadata", {})
        )

        # 2. 发送消息
        return self.send_message(request)

    def send_immediate_message(
        self,
        content: str,
        target: str,
        priority: MessagePriority = MessagePriority.HIGH,
        **kwargs
    ) -> str:
        """
        便捷方法：立即发送消息

        Args:
            content: 消息内容
            target: 发送目标
            priority: 消息优先级
            **kwargs: 其他参数

        Returns:
            str: 消息ID
        """
        # 1. 发送无延迟消息
        return self.send_delayed_message(
            content=content,
            target=target,
            delay_seconds=0.0,
            priority=priority,
            **kwargs
        )

    def cancel_message(self, message_id: str) -> bool:
        """
        取消消息发送

        Args:
            message_id: 消息ID

        Returns:
            bool: 是否取消成功
        """
        # 1. 在队列中查找
        with self.queue_lock:
            for i, msg in enumerate(self.message_queue):
                if msg.message_id == message_id:
                    # 2. 从队列移除
                    self.message_queue.pop(i)

                    # 3. 记录取消结果
                    result = MessageSendResult(
                        message_id=message_id,
                        status=MessageStatus.CANCELLED,
                        success=False
                    )
                    self.results_history[message_id] = result

                    # 4. 保存队列
                    if self.config.queue_persistence_enabled:
                        self._save_queue()

                    # 5. 记录取消信息
                    logger.info(f"取消消息: {message_id}")
                    return True

        # 6. 未找到消息
        logger.warning(f"取消消息失败: 消息不存在 {message_id}")
        return False

    def start_processor(self, send_callback: Callable[[MessageSendRequest], MessageSendResult]) -> None:
        """
        启动消息处理器

        Args:
            send_callback: 发送回调函数
        """
        # 1. 检查是否已运行
        if self.is_running:
            logger.warning("消息处理器已在运行")
            return

        # 2. 设置回调函数
        self.send_callback = send_callback

        # 3. 启动处理器线程
        self.is_running = True
        self.stop_event.clear()
        self.processor_thread = threading.Thread(target=self._processor_loop, daemon=True)
        self.processor_thread.start()

        # 4. 记录启动信息
        logger.info("延迟消息处理器已启动")

    def stop_processor(self) -> None:
        """停止消息处理器"""
        # 1. 设置停止标志
        if not self.is_running:
            logger.info("消息处理器未运行")
            return

        # 2. 停止处理器
        self.is_running = False
        self.stop_event.set()

        # 3. 等待线程结束
        if self.processor_thread and self.processor_thread.is_alive():
            self.processor_thread.join(timeout=5.0)

        # 4. 记录停止信息
        logger.info("延迟消息处理器已停止")

    def get_queue_status(self) -> Dict[str, Any]:
        """
        获取队列状态

        Returns:
            Dict[str, Any]: 队列状态信息
        """
        # 1. 统计队列信息
        with self.queue_lock:
            total_messages = len(self.message_queue)
            sending_messages = len(self.sending_queue)

            # 2. 按优先级统计
            priority_counts = {}
            for priority in MessagePriority:
                count = sum(1 for msg in self.message_queue if msg.priority == priority)
                priority_counts[priority.value] = count

            # 3. 统计下一个发送时间
            next_send_time = None
            if self.message_queue:
                next_send_time = min(
                    msg.scheduled_time for msg in self.message_queue
                    if msg.scheduled_time
                )

        # 4. 统计结果历史
        status_counts = {}
        for status in MessageStatus:
            count = sum(1 for result in self.results_history.values() if result.status == status)
            status_counts[status.value] = count

        # 5. 返回状态信息
        return {
            "queue_size": total_messages,
            "sending_count": sending_messages,
            "priority_counts": priority_counts,
            "status_counts": status_counts,
            "next_send_time": next_send_time.isoformat() if next_send_time else None,
            "is_running": self.is_running,
            "concurrent_sends": self.concurrent_sends,
            "max_queue_size": self.config.max_queue_size,
            "config": self.config.model_dump()
        }

    def get_message_result(self, message_id: str) -> Optional[MessageSendResult]:
        """
        获取消息发送结果

        Args:
            message_id: 消息ID

        Returns:
            Optional[MessageSendResult]: 发送结果
        """
        # 1. 返回结果
        return self.results_history.get(message_id)

    def clear_history(self, older_than_hours: int = 24) -> int:
        """
        清理历史记录

        Args:
            older_than_hours: 清理多少小时前的记录

        Returns:
            int: 清理的记录数量
        """
        # 1. 计算过期时间
        cutoff_time = datetime.now() - timedelta(hours=older_than_hours)

        # 2. 过滤需要清理的记录
        old_results = []
        for message_id, result in self.results_history.items():
            if (result.sent_at and result.sent_at < cutoff_time):
                old_results.append(message_id)

        # 3. 删除旧记录
        for message_id in old_results:
            del self.results_history[message_id]

        # 4. 记录清理信息
        cleanup_count = len(old_results)
        if cleanup_count > 0:
            logger.info(f"清理历史记录: {cleanup_count} 条")

        # 5. 返回清理数量
        return cleanup_count

    def _processor_loop(self) -> None:
        """消息处理器主循环"""
        # 1. 主循环
        while self.is_running and not self.stop_event.is_set():
            try:
                # 2. 处理待发送消息
                self._process_pending_messages()

                # 3. 等待下次处理
                self.stop_event.wait(self.config.processing_interval_seconds)

            except Exception as e:
                # 4. 处理循环异常
                logger.error(f"消息处理器循环异常: {e}")
                self.stop_event.wait(5)  # 异常后短暂等待

    def _process_pending_messages(self) -> None:
        """处理待发送消息"""
        # 1. 获取当前时间
        current_time = datetime.now()

        # 2. 查找需要发送的消息
        messages_to_send = []
        with self.queue_lock:
            for i in range(min(self.config.batch_size, len(self.message_queue))):
                msg = self.message_queue[i]
                if msg.scheduled_time and msg.scheduled_time <= current_time:
                    # 3. 检查并发限制
                    with self.concurrent_lock:
                        if self.concurrent_sends < self.config.max_concurrent_sends:
                            messages_to_send.append(msg)
                            self.concurrent_sends += 1

        # 4. 发送消息
        for msg in messages_to_send:
            # 5. 从队列移除并加入发送队列
            with self.queue_lock:
                if msg in self.message_queue:
                    self.message_queue.remove(msg)
                self.sending_queue[msg.message_id] = msg

            # 6. 异步发送消息
            threading.Thread(target=self._send_message_async, args=(msg,), daemon=True).start()

    def _send_message_async(self, request: MessageSendRequest) -> None:
        """
        异步发送消息

        Args:
            request: 消息发送请求
        """
        start_time = time.time()
        result = None

        try:
            # 1. 执行发送回调
            if self.send_callback:
                result = self.send_callback(request)
            else:
                # 2. 默认发送结果
                result = MessageSendResult(
                    message_id=request.message_id,
                    status=MessageStatus.FAILED,
                    success=False,
                    error_message="未设置发送回调函数"
                )

            # 3. 设置执行时间
            result.execution_time_ms = (time.time() - start_time) * 1000

        except Exception as e:
            # 4. 处理发送异常
            result = MessageSendResult(
                message_id=request.message_id,
                status=MessageStatus.FAILED,
                success=False,
                error_message=str(e),
                execution_time_ms=(time.time() - start_time) * 1000
            )
            logger.error(f"发送消息异常: {request.message_id}, 错误: {e}")

        finally:
            # 5. 清理发送队列
            with self.queue_lock:
                if request.message_id in self.sending_queue:
                    del self.sending_queue[request.message_id]

            # 6. 减少并发计数
            with self.concurrent_lock:
                self.concurrent_sends -= 1

            # 7. 保存结果
            if result:
                self.results_history[request.message_id] = result

            # 8. 处理重试逻辑
            if (result and not result.success and
                self.config.auto_retry_enabled and
                result.attempt_count < request.max_retries):
                self._schedule_retry(request, result)

    def _schedule_retry(self, request: MessageSendRequest, last_result: MessageSendResult) -> None:
        """
        安排重试发送

        Args:
            request: 原始请求
            last_result: 上次发送结果
        """
        # 1. 创建重试请求
        retry_request = request.model_copy()
        retry_request.message_id = str(uuid.uuid4())  # 新的消息ID
        retry_request.delay_seconds = min(30, (last_result.attempt_count + 1) * 10)  # 递增延迟

        # 2. 更新尝试次数
        last_result.attempt_count += 1

        # 3. 重新加入队列
        self.send_message(retry_request)

        # 4. 记录重试信息
        logger.info(f"安排重试: 原ID={request.message_id}, 新ID={retry_request.message_id}")

    def _load_queue(self) -> None:
        """从文件加载队列数据"""
        try:
            # 1. 检查文件是否存在
            if not self.storage_path.exists():
                return

            # 2. 读取文件内容
            content = self.storage_path.read_text(encoding='utf-8')
            data = json.loads(content)

            # 3. 解析队列数据
            for msg_data in data.get('queue', []):
                msg = MessageSendRequest(**msg_data)
                self.message_queue.append(msg)

            # 4. 记录加载信息
            logger.info(f"加载消息队列: {len(self.message_queue)} 条消息")

        except Exception as e:
            # 5. 处理加载异常
            logger.warning(f"加载消息队列失败: {e}")

    def _save_queue(self) -> None:
        """保存队列数据到文件"""
        try:
            # 1. 序列化队列数据
            queue_data = [msg.model_dump() for msg in self.message_queue]
            data = {"queue": queue_data, "updated_at": datetime.now().isoformat()}

            # 2. 写入文件
            self.storage_path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding='utf-8'
            )

        except Exception as e:
            # 3. 处理保存异常
            logger.error(f"保存消息队列失败: {e}")