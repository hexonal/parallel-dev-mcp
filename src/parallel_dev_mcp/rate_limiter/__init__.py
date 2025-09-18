# -*- coding: utf-8 -*-
"""
限流与继续执行机制模块

@description 实现30秒频率限流和5小时限制检测与自动重试机制
"""

from .rate_limiter_manager import RateLimiterManager, RateLimitConfig, RateLimitStatus
from .message_detector import FiveHourLimitDetector, LimitDetectionResult, LimitType
from .auto_retry_scheduler import AutoRetryScheduler, RetryConfig, RetryTask, RetryStatus, RetryStrategy
from .message_sender import DelayedMessageSender, MessageSendRequest, MessageSendResult, DelayConfig, MessagePriority, MessageStatus
from .state_manager import StateManager, StateConfig, StateSnapshot, StateType
from .control_interface import ControlInterface, ComponentStatus, SystemStatus, ComponentType, SystemHealth

__all__ = [
    # 限流管理器
    "RateLimiterManager",
    "RateLimitConfig",
    "RateLimitStatus",

    # 消息检测器
    "FiveHourLimitDetector",
    "LimitDetectionResult",
    "LimitType",

    # 自动重试调度器
    "AutoRetryScheduler",
    "RetryConfig",
    "RetryTask",
    "RetryStatus",
    "RetryStrategy",

    # 延迟消息发送器
    "DelayedMessageSender",
    "MessageSendRequest",
    "MessageSendResult",
    "DelayConfig",
    "MessagePriority",
    "MessageStatus",

    # 状态管理器
    "StateManager",
    "StateConfig",
    "StateSnapshot",
    "StateType",

    # 控制接口
    "ControlInterface",
    "ComponentStatus",
    "SystemStatus",
    "ComponentType",
    "SystemHealth"
]