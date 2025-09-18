# -*- coding: utf-8 -*-
"""
频率限流器实现

@description 实现调用频率跟踪和限流功能，防止高频调用并支持自动消息触发
"""

import logging
import time
from collections import deque
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

# 配置日志系统
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class RateLimiterConfig(BaseModel):
    """
    频率限流器配置数据模型

    定义滑动窗口算法的参数和限流规则
    """

    window_seconds: int = Field(30, description="滑动窗口时间长度（秒）", ge=1, le=3600)
    threshold: int = Field(1, description="窗口内允许的最大调用次数", ge=1, le=100)
    auto_message_enabled: bool = Field(True, description="是否启用自动消息触发")
    message_send_cost_seconds: int = Field(
        12, description="消息发送的时间成本（秒）", ge=1, le=60
    )

    model_config = ConfigDict(
        # 1. 启用JSON编码器
        # json_encoders deprecated in V2,
        # 2. 示例数据
        json_schema_extra={
            "example": {
                "window_seconds": 30,
                "threshold": 1,
                "auto_message_enabled": True,
                "message_send_cost_seconds": 12,
            }
        },
    )


class CallFrequencyTracker:
    """
    调用频率跟踪器

    使用滑动窗口算法跟踪调用频率，支持自动消息触发和频率限流
    """

    def __init__(self, config: Optional[RateLimiterConfig] = None) -> None:
        """
        初始化调用频率跟踪器

        Args:
            config: 频率限流器配置实例，如果为 None 则使用默认配置
        """
        # 1. 设置配置参数
        if config is None:
            config = RateLimiterConfig()
        self.config = config

        # 2. 初始化调用时间戳队列
        self._call_timestamps: deque[float] = deque()

        # 3. 记录初始化信息
        logger.info(
            f"调用频率跟踪器初始化: 窗口={self.config.window_seconds}秒, "
            f"阈值={self.config.threshold}次"
        )

    def record_call(self, event_type: str = "SessionEnd") -> None:
        """
        记录调用事件

        记录当前时间戳到调用队列中，并清理过期的时间戳

        Args:
            event_type: 事件类型，用于日志记录
        """
        # 1. 获取当前时间戳
        current_time = time.time()

        # 2. 添加到调用队列
        self._call_timestamps.append(current_time)

        # 3. 清理过期的时间戳
        self._cleanup_expired_timestamps(current_time)

        # 4. 记录调用信息
        logger.info(
            f"记录调用事件: {event_type}, "
            f"当前窗口内调用次数: {len(self._call_timestamps)}/{self.config.threshold}"
        )

    def should_trigger_auto_message(self) -> bool:
        """
        检测是否应该触发自动消息

        根据当前窗口内的调用频率判断是否需要发送自动 'hi' 消息

        Returns:
            bool: 如果应该触发自动消息则返回 True
        """
        # 1. 检查自动消息是否启用
        if not self.config.auto_message_enabled:
            return False

        # 2. 清理过期的时间戳
        current_time = time.time()
        self._cleanup_expired_timestamps(current_time)

        # 3. 检查调用频率是否超过阈值
        call_count = len(self._call_timestamps)
        should_trigger = call_count > self.config.threshold

        # 4. 记录检测结果
        if should_trigger:
            logger.warning(
                f"检测到高频调用: {call_count}次 > {self.config.threshold}次, "
                f"触发自动消息发送"
            )
        else:
            logger.debug(f"调用频率正常: {call_count}次 <= {self.config.threshold}次")

        # 5. 返回检测结果
        return should_trigger

    def reset(self) -> None:
        """
        重置跟踪器状态

        清空所有调用时间戳，避免循环触发自动消息
        """
        # 1. 记录重置前的状态
        call_count = len(self._call_timestamps)

        # 2. 清空调用队列
        self._call_timestamps.clear()

        # 3. 记录重置信息
        logger.info(f"调用频率跟踪器已重置: 清空 {call_count} 个时间戳")

    def get_current_call_count(self) -> int:
        """
        获取当前窗口内的调用次数

        Returns:
            int: 当前窗口内的调用次数
        """
        # 1. 清理过期的时间戳
        current_time = time.time()
        self._cleanup_expired_timestamps(current_time)

        # 2. 返回当前调用次数
        return len(self._call_timestamps)

    def get_next_allowed_call_time(self) -> Optional[float]:
        """
        获取下次允许调用的时间

        计算基于当前窗口状态，下次可以进行调用的时间戳

        Returns:
            Optional[float]: 下次允许调用的时间戳，如果当前可以调用则返回 None
        """
        # 1. 清理过期的时间戳
        current_time = time.time()
        self._cleanup_expired_timestamps(current_time)

        # 2. 检查当前是否可以调用
        if len(self._call_timestamps) < self.config.threshold:
            return None

        # 3. 计算最早的调用时间戳
        if self._call_timestamps:
            earliest_timestamp = self._call_timestamps[0]
            next_allowed_time = earliest_timestamp + self.config.window_seconds
            return next_allowed_time

        # 4. 如果队列为空，当前时间即可调用
        return None

    def _cleanup_expired_timestamps(self, current_time: float) -> None:
        """
        清理过期的时间戳

        移除窗口时间之外的旧时间戳

        Args:
            current_time: 当前时间戳
        """
        # 1. 计算窗口起始时间
        window_start = current_time - self.config.window_seconds

        # 2. 移除过期的时间戳
        while self._call_timestamps and self._call_timestamps[0] < window_start:
            expired_timestamp = self._call_timestamps.popleft()
            logger.debug(f"移除过期时间戳: {expired_timestamp}")


def create_default_tracker() -> CallFrequencyTracker:
    """
    创建默认配置的频率跟踪器

    返回使用默认配置的调用频率跟踪器实例

    Returns:
        CallFrequencyTracker: 配置好的频率跟踪器实例
    """
    # 1. 创建默认配置
    default_config = RateLimiterConfig(
        window_seconds=30,
        threshold=1,
        auto_message_enabled=True,
        message_send_cost_seconds=12,
    )

    # 2. 创建跟踪器实例
    tracker = CallFrequencyTracker(default_config)

    # 3. 记录创建信息
    logger.info("默认频率跟踪器创建成功")

    # 4. 返回跟踪器实例
    return tracker
