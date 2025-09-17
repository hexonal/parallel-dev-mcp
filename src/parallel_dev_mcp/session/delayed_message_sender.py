# -*- coding: utf-8 -*-
"""
延时消息发送器

@description 实现两阶段消息发送机制：先发送消息内容，10秒后发送回车键
"""

import logging
import threading
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable
from enum import Enum, unique
from pydantic import BaseModel, Field, field_validator

# 导入错误恢复和日志系统
from .message_logger import get_message_logger, LogLevel
from .error_recovery import get_error_recovery_manager, RetryConfig, CircuitBreaker

# 配置日志系统
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@unique
class MessageStatus(Enum):
    """消息发送状态枚举"""
    PENDING = "pending"
    MESSAGE_SENT = "message_sent"
    ENTER_SCHEDULED = "enter_scheduled"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MessageRequest(BaseModel):
    """消息发送请求数据模型"""

    session_name: str = Field(..., description="目标会话名称", min_length=1, max_length=200)
    message_content: str = Field(..., description="消息内容", min_length=1, max_length=5000)
    window_index: Optional[int] = Field(None, description="目标窗口索引", ge=0)
    pane_index: Optional[int] = Field(None, description="目标面板索引", ge=0)
    delay_seconds: int = Field(10, description="延时秒数", ge=1, le=300)
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="请求唯一标识")

    @field_validator('session_name')
    @classmethod
    def validate_session_name(cls, v: str) -> str:
        """验证会话名称格式"""
        if not v or not v.strip():
            raise ValueError('会话名称不能为空')
        return v.strip()

    @field_validator('message_content')
    @classmethod
    def validate_message_content(cls, v: str) -> str:
        """验证消息内容"""
        if not v or not v.strip():
            raise ValueError('消息内容不能为空')
        return v.strip()


class MessageStatusInfo(BaseModel):
    """消息状态信息数据模型"""

    request_id: str = Field(..., description="请求ID")
    session_name: str = Field(..., description="会话名称")
    status: MessageStatus = Field(..., description="当前状态")
    message_content: str = Field(..., description="消息内容")
    created_at: datetime = Field(..., description="创建时间")
    message_sent_at: Optional[datetime] = Field(None, description="消息发送时间")
    enter_sent_at: Optional[datetime] = Field(None, description="回车发送时间")
    error_message: Optional[str] = Field(None, description="错误信息")
    delay_seconds: int = Field(..., description="延时秒数")
    retry_count: int = Field(0, description="重试次数")
    total_duration_ms: Optional[float] = Field(None, description="总耗时(毫秒)")


class DelayedMessageSender:
    """
    延时消息发送器

    实现两阶段消息发送：先发送消息内容，延时后发送回车键
    """

    def __init__(self) -> None:
        """初始化延时消息发送器"""
        # 1. 初始化状态追踪
        self._active_messages: Dict[str, MessageStatusInfo] = {}
        self._timers: Dict[str, threading.Timer] = {}
        self._lock = threading.Lock()

        # 2. 初始化错误恢复和日志
        self._message_logger = get_message_logger()
        self._error_recovery = get_error_recovery_manager()
        self._circuit_breaker = CircuitBreaker("delayed_message_sender")

        # 3. 记录初始化信息
        self._message_logger.log(
            LogLevel.INFO,
            "delayed_sender",
            "init",
            "延时消息发送器初始化完成"
        )
        logger.info("延时消息发送器初始化完成")

    def send_delayed_message(
        self,
        request: MessageRequest,
        completion_callback: Optional[Callable[[str, bool], None]] = None
    ) -> Dict[str, Any]:
        """
        发送延时消息

        Args:
            request: 消息发送请求
            completion_callback: 完成回调函数，参数为(request_id, success)

        Returns:
            Dict[str, Any]: 发送操作结果
        """
        # 1. 开始计时
        start_time = self._message_logger.start_timer(f"send_delayed_message_{request.request_id}")

        try:
            # 2. 参数验证已通过Pydantic自动完成

            # 3. 创建状态信息
            status_info = MessageStatusInfo(
                request_id=request.request_id,
                session_name=request.session_name,
                status=MessageStatus.PENDING,
                message_content=request.message_content,
                created_at=datetime.now(),
                delay_seconds=request.delay_seconds
            )

            # 4. 注册状态
            with self._lock:
                self._active_messages[request.request_id] = status_info

            # 5. 记录开始发送
            self._message_logger.log(
                LogLevel.INFO,
                "delayed_sender",
                "send_start",
                f"开始发送延时消息: {request.session_name}",
                request_id=request.request_id,
                session_name=request.session_name,
                data={"delay_seconds": request.delay_seconds}
            )

            # 6. 通过熔断器发送消息内容
            def send_operation() -> Dict[str, Any]:
                return self._send_message_content_with_retry(request)

            message_result = self._circuit_breaker.call(send_operation)

            if not message_result["success"]:
                # 7. 消息发送失败
                self._update_status(request.request_id, MessageStatus.FAILED,
                                  message_result.get("message", "发送失败"))

                self._message_logger.log(
                    LogLevel.ERROR,
                    "delayed_sender",
                    "send_failed",
                    f"消息发送失败: {message_result.get('message', '未知错误')}",
                    request_id=request.request_id,
                    session_name=request.session_name,
                    data={"error": message_result.get("message")}
                )
                return message_result

            # 8. 更新状态为消息已发送
            self._update_status(request.request_id, MessageStatus.MESSAGE_SENT)
            status_info.message_sent_at = datetime.now()

            # 9. 调度回车键发送
            self._schedule_enter_key(request, completion_callback)

            # 10. 记录成功和总耗时
            total_duration = self._message_logger.end_timer(f"send_delayed_message_{request.request_id}", start_time)
            status_info.total_duration_ms = total_duration

            self._message_logger.log(
                LogLevel.INFO,
                "delayed_sender",
                "send_scheduled",
                f"延时消息调度成功: {request.session_name}",
                request_id=request.request_id,
                session_name=request.session_name,
                duration_ms=total_duration
            )

            # 11. 返回成功结果
            logger.info(f"延时消息发送启动成功: {request.request_id}")
            return {
                "success": True,
                "message": "延时消息发送已启动",
                "request_id": request.request_id,
                "session_name": request.session_name,
                "delay_seconds": request.delay_seconds,
                "estimated_completion": (datetime.now() + timedelta(seconds=request.delay_seconds)).isoformat()
            }

        except Exception as e:
            # 12. 异常处理
            self._message_logger.end_timer(f"send_delayed_message_{request.request_id}", start_time)

            self._message_logger.log(
                LogLevel.ERROR,
                "delayed_sender",
                "send_exception",
                f"延时消息发送异常: {str(e)}",
                request_id=request.request_id,
                session_name=request.session_name,
                data={"exception": str(e)}
            )

            logger.error(f"延时消息发送失败: {e}")
            if request.request_id in self._active_messages:
                self._update_status(request.request_id, MessageStatus.FAILED, str(e))

            return {
                "success": False,
                "message": f"延时消息发送失败: {str(e)}",
                "request_id": request.request_id
            }

    def _send_message_content_with_retry(self, request: MessageRequest) -> Dict[str, Any]:
        """使用重试机制发送消息内容"""
        # 1. 配置重试策略
        retry_config = RetryConfig(
            max_retries=2,
            base_delay_ms=500,
            max_delay_ms=5000
        )

        # 2. 定义发送操作
        def send_operation() -> Dict[str, Any]:
            return self._send_message_content(request)

        # 3. 执行带重试的发送
        return self._error_recovery.execute_with_retry(
            operation=send_operation,
            operation_id=f"send_content_{request.request_id}",
            retry_config=retry_config
        )

    def _send_message_content(self, request: MessageRequest) -> Dict[str, Any]:
        """发送消息内容（不包含回车）"""
        try:
            # 1. 导入tmux工具函数
            from ..tmux.tmux_tools import send_keys_to_tmux_session

            # 2. 发送消息内容，不发送回车
            result = send_keys_to_tmux_session(
                session_name=request.session_name,
                keys=request.message_content,
                window_index=request.window_index,
                pane_index=request.pane_index,
                enter=False  # 关键：不发送回车
            )

            return result

        except Exception as e:
            # 3. 处理异常
            logger.error(f"发送消息内容失败: {e}")
            return {
                "success": False,
                "message": f"发送消息内容失败: {str(e)}"
            }

    def _schedule_enter_key(
        self,
        request: MessageRequest,
        completion_callback: Optional[Callable[[str, bool], None]]
    ) -> None:
        """调度回车键发送"""
        try:
            # 1. 更新状态
            self._update_status(request.request_id, MessageStatus.ENTER_SCHEDULED)

            # 2. 创建定时器回调函数
            def send_enter_callback() -> None:
                self._send_enter_key(request, completion_callback)

            # 3. 创建并启动定时器
            timer = threading.Timer(request.delay_seconds, send_enter_callback)

            with self._lock:
                self._timers[request.request_id] = timer

            timer.start()

            logger.info(f"回车键发送已调度: {request.request_id}, 延时 {request.delay_seconds} 秒")

        except Exception as e:
            # 4. 异常处理
            logger.error(f"调度回车键发送失败: {e}")
            self._update_status(request.request_id, MessageStatus.FAILED, str(e))

    def _send_enter_key(
        self,
        request: MessageRequest,
        completion_callback: Optional[Callable[[str, bool], None]]
    ) -> None:
        """发送回车键"""
        # 1. 开始计时
        start_time = self._message_logger.start_timer(f"send_enter_{request.request_id}")

        try:
            # 2. 记录开始发送回车
            self._message_logger.log(
                LogLevel.DEBUG,
                "delayed_sender",
                "enter_start",
                f"开始发送回车键: {request.session_name}",
                request_id=request.request_id,
                session_name=request.session_name
            )

            # 3. 使用重试机制发送回车键
            def enter_operation() -> Dict[str, Any]:
                return self._send_enter_key_direct(request)

            retry_config = RetryConfig(
                max_retries=1,
                base_delay_ms=200,
                max_delay_ms=2000
            )

            result = self._error_recovery.execute_with_retry(
                operation=enter_operation,
                operation_id=f"send_enter_{request.request_id}",
                retry_config=retry_config
            )

            # 4. 处理结果
            duration = self._message_logger.end_timer(f"send_enter_{request.request_id}", start_time)

            if result["success"]:
                self._update_status(request.request_id, MessageStatus.COMPLETED)
                if request.request_id in self._active_messages:
                    self._active_messages[request.request_id].enter_sent_at = datetime.now()

                self._message_logger.log(
                    LogLevel.INFO,
                    "delayed_sender",
                    "enter_success",
                    f"回车键发送成功: {request.session_name}",
                    request_id=request.request_id,
                    session_name=request.session_name,
                    duration_ms=duration
                )
                logger.info(f"延时消息发送完成: {request.request_id}")

                # 5. 调用完成回调
                if completion_callback:
                    completion_callback(request.request_id, True)
            else:
                error_msg = result.get("message", "发送回车键失败")
                self._update_status(request.request_id, MessageStatus.FAILED, error_msg)

                self._message_logger.log(
                    LogLevel.ERROR,
                    "delayed_sender",
                    "enter_failed",
                    f"回车键发送失败: {error_msg}",
                    request_id=request.request_id,
                    session_name=request.session_name,
                    data={"error": error_msg}
                )

                if completion_callback:
                    completion_callback(request.request_id, False)

            # 6. 清理定时器
            self._cleanup_request(request.request_id)

        except Exception as e:
            # 7. 异常处理
            self._message_logger.end_timer(f"send_enter_{request.request_id}", start_time)

            self._message_logger.log(
                LogLevel.ERROR,
                "delayed_sender",
                "enter_exception",
                f"回车键发送异常: {str(e)}",
                request_id=request.request_id,
                session_name=request.session_name,
                data={"exception": str(e)}
            )

            logger.error(f"发送回车键失败: {e}")
            self._update_status(request.request_id, MessageStatus.FAILED, str(e))
            if completion_callback:
                completion_callback(request.request_id, False)
            self._cleanup_request(request.request_id)

    def _send_enter_key_direct(self, request: MessageRequest) -> Dict[str, Any]:
        """直接发送回车键（不包含重试）"""
        try:
            # 1. 导入tmux工具函数
            from ..tmux.tmux_tools import send_keys_to_tmux_session

            # 2. 发送回车键
            result = send_keys_to_tmux_session(
                session_name=request.session_name,
                keys="",  # 空内容
                window_index=request.window_index,
                pane_index=request.pane_index,
                enter=True  # 只发送回车
            )

            return result

        except Exception as e:
            # 3. 处理异常
            logger.error(f"直接发送回车键失败: {e}")
            return {
                "success": False,
                "message": f"发送回车键失败: {str(e)}"
            }

    def get_message_status(self, request_id: str) -> Optional[MessageStatusInfo]:
        """获取消息状态"""
        with self._lock:
            return self._active_messages.get(request_id)

    def cancel_message(self, request_id: str) -> bool:
        """取消消息发送"""
        try:
            with self._lock:
                # 1. 检查消息是否存在
                if request_id not in self._active_messages:
                    return False

                # 2. 取消定时器
                if request_id in self._timers:
                    self._timers[request_id].cancel()

                # 3. 更新状态
                self._update_status(request_id, MessageStatus.CANCELLED)

                # 4. 清理资源
                self._cleanup_request(request_id)

                logger.info(f"消息发送已取消: {request_id}")
                return True

        except Exception as e:
            logger.error(f"取消消息发送失败: {e}")
            return False

    def _update_status(self, request_id: str, status: MessageStatus, error: Optional[str] = None) -> None:
        """更新消息状态"""
        with self._lock:
            if request_id in self._active_messages:
                self._active_messages[request_id].status = status
                if error:
                    self._active_messages[request_id].error_message = error

    def _cleanup_request(self, request_id: str) -> None:
        """清理请求资源"""
        with self._lock:
            # 1. 清理定时器
            if request_id in self._timers:
                del self._timers[request_id]

    def get_all_active_messages(self) -> Dict[str, MessageStatusInfo]:
        """获取所有活跃消息状态"""
        with self._lock:
            return self._active_messages.copy()

    def get_performance_metrics(self) -> Dict[str, Any]:
        """获取性能指标"""
        # 1. 获取日志统计
        metrics_summary = self._message_logger.get_metrics_summary()

        # 2. 获取重试统计
        retry_stats = self._error_recovery.get_retry_statistics()

        # 3. 获取熔断器状态
        circuit_state = self._circuit_breaker.get_state()

        # 4. 计算消息统计
        with self._lock:
            total_messages = len(self._active_messages)
            completed_messages = sum(
                1 for msg in self._active_messages.values()
                if msg.status == MessageStatus.COMPLETED
            )
            failed_messages = sum(
                1 for msg in self._active_messages.values()
                if msg.status == MessageStatus.FAILED
            )

        # 5. 返回综合指标
        return {
            "message_stats": {
                "total_messages": total_messages,
                "completed_messages": completed_messages,
                "failed_messages": failed_messages,
                "success_rate": completed_messages / total_messages if total_messages > 0 else 0
            },
            "performance_metrics": metrics_summary,
            "retry_statistics": retry_stats,
            "circuit_breaker": circuit_state
        }


# 全局延时消息发送器实例
_global_delayed_sender: Optional[DelayedMessageSender] = None


def get_delayed_message_sender() -> DelayedMessageSender:
    """
    获取全局延时消息发送器实例

    Returns:
        DelayedMessageSender: 延时消息发送器实例
    """
    global _global_delayed_sender

    # 1. 初始化全局实例（如果需要）
    if _global_delayed_sender is None:
        _global_delayed_sender = DelayedMessageSender()
        logger.info("初始化全局延时消息发送器实例")

    return _global_delayed_sender