# -*- coding: utf-8 -*-
"""
错误恢复系统

@description 提供重试机制、熔断器和错误恢复策略
"""

import time
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable, List
from enum import Enum, unique
from pydantic import BaseModel, Field
from dataclasses import dataclass

from .message_logger import get_message_logger, LogLevel

logger = get_message_logger()


@unique
class RetryStrategy(Enum):
    """重试策略枚举"""
    FIXED_DELAY = "fixed_delay"
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"


@unique
class CircuitState(Enum):
    """熔断器状态枚举"""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class RetryConfig:
    """重试配置"""
    max_retries: int = 3
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF
    base_delay_ms: int = 1000
    max_delay_ms: int = 30000
    backoff_multiplier: float = 2.0
    jitter: bool = True


class CircuitBreakerConfig(BaseModel):
    """熔断器配置数据模型"""

    failure_threshold: int = Field(5, description="失败阈值")
    success_threshold: int = Field(3, description="成功阈值")
    timeout_ms: int = Field(60000, description="超时时间(毫秒)")
    half_open_max_calls: int = Field(3, description="半开状态最大调用数")


class RetryAttempt(BaseModel):
    """重试尝试记录"""

    attempt_number: int = Field(..., description="尝试次数")
    timestamp: datetime = Field(default_factory=datetime.now, description="时间戳")
    success: bool = Field(..., description="是否成功")
    error_message: Optional[str] = Field(None, description="错误信息")
    delay_ms: Optional[int] = Field(None, description="延时毫秒")


class ErrorRecoveryManager:
    """
    错误恢复管理器

    提供重试机制和错误恢复策略
    """

    def __init__(self, default_retry_config: Optional[RetryConfig] = None) -> None:
        """
        初始化错误恢复管理器

        Args:
            default_retry_config: 默认重试配置
        """
        # 1. 初始化配置
        self.default_retry_config = default_retry_config or RetryConfig()

        # 2. 初始化重试历史
        self._retry_history: Dict[str, List[RetryAttempt]] = {}
        self._lock = threading.Lock()

        # 3. 记录初始化
        logger.log(
            LogLevel.INFO,
            "error_recovery",
            "init",
            "错误恢复管理器初始化完成"
        )

    def execute_with_retry(
        self,
        operation: Callable[[], Dict[str, Any]],
        operation_id: str,
        retry_config: Optional[RetryConfig] = None
    ) -> Dict[str, Any]:
        """
        执行操作并支持重试

        Args:
            operation: 要执行的操作函数
            operation_id: 操作标识
            retry_config: 重试配置

        Returns:
            Dict[str, Any]: 操作结果
        """
        # 1. 使用配置
        config = retry_config or self.default_retry_config

        # 2. 初始化重试历史
        with self._lock:
            self._retry_history[operation_id] = []

        # 3. 执行重试循环
        for attempt in range(config.max_retries + 1):
            try:
                # 4. 记录尝试开始
                start_time = logger.start_timer(f"retry_attempt_{operation_id}")

                logger.log(
                    LogLevel.DEBUG,
                    "error_recovery",
                    "attempt",
                    f"开始执行操作: {operation_id}, 尝试 {attempt + 1}/{config.max_retries + 1}"
                )

                # 5. 执行操作
                result = operation()

                # 6. 记录成功
                duration = logger.end_timer(f"retry_attempt_{operation_id}", start_time)
                self._record_attempt(operation_id, attempt + 1, True, None, None)

                logger.log(
                    LogLevel.INFO,
                    "error_recovery",
                    "success",
                    f"操作成功: {operation_id}, 尝试 {attempt + 1}, 耗时 {duration:.2f}ms",
                    data={"attempt": attempt + 1, "duration_ms": duration}
                )

                return result

            except Exception as e:
                # 7. 记录失败
                duration = logger.end_timer(f"retry_attempt_{operation_id}", start_time)
                error_message = str(e)

                logger.log(
                    LogLevel.WARNING,
                    "error_recovery",
                    "failure",
                    f"操作失败: {operation_id}, 尝试 {attempt + 1}, 错误: {error_message}",
                    data={"attempt": attempt + 1, "error": error_message}
                )

                # 8. 检查是否为最后一次尝试
                if attempt >= config.max_retries:
                    self._record_attempt(operation_id, attempt + 1, False, error_message, None)

                    logger.log(
                        LogLevel.ERROR,
                        "error_recovery",
                        "exhausted",
                        f"重试耗尽: {operation_id}, 最终失败",
                        data={"total_attempts": attempt + 1, "final_error": error_message}
                    )

                    return {
                        "success": False,
                        "error": f"操作失败，已重试 {config.max_retries} 次: {error_message}",
                        "attempts": attempt + 1
                    }

                # 9. 计算延时
                delay_ms = self._calculate_delay(config, attempt)
                self._record_attempt(operation_id, attempt + 1, False, error_message, delay_ms)

                logger.log(
                    LogLevel.INFO,
                    "error_recovery",
                    "retry_delay",
                    f"等待重试: {operation_id}, 延时 {delay_ms}ms",
                    data={"delay_ms": delay_ms, "next_attempt": attempt + 2}
                )

                # 10. 执行延时
                time.sleep(delay_ms / 1000.0)

        # 理论上不会到达这里
        return {"success": False, "error": "未知错误"}

    def _calculate_delay(self, config: RetryConfig, attempt: int) -> int:
        """
        计算重试延时

        Args:
            config: 重试配置
            attempt: 当前尝试次数（从0开始）

        Returns:
            int: 延时毫秒数
        """
        # 1. 根据策略计算基础延时
        if config.strategy == RetryStrategy.FIXED_DELAY:
            delay = config.base_delay_ms
        elif config.strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            delay = config.base_delay_ms * (config.backoff_multiplier ** attempt)
        elif config.strategy == RetryStrategy.LINEAR_BACKOFF:
            delay = config.base_delay_ms * (attempt + 1)
        else:
            delay = config.base_delay_ms

        # 2. 应用最大延时限制
        delay = min(delay, config.max_delay_ms)

        # 3. 添加抖动（如果启用）
        if config.jitter:
            import random
            jitter_factor = random.uniform(0.8, 1.2)
            delay = int(delay * jitter_factor)

        return delay

    def _record_attempt(
        self,
        operation_id: str,
        attempt_number: int,
        success: bool,
        error_message: Optional[str],
        delay_ms: Optional[int]
    ) -> None:
        """
        记录重试尝试

        Args:
            operation_id: 操作ID
            attempt_number: 尝试次数
            success: 是否成功
            error_message: 错误消息
            delay_ms: 延时毫秒
        """
        attempt = RetryAttempt(
            attempt_number=attempt_number,
            success=success,
            error_message=error_message,
            delay_ms=delay_ms
        )

        with self._lock:
            if operation_id not in self._retry_history:
                self._retry_history[operation_id] = []
            self._retry_history[operation_id].append(attempt)

    def get_retry_history(self, operation_id: str) -> List[RetryAttempt]:
        """
        获取重试历史

        Args:
            operation_id: 操作ID

        Returns:
            List[RetryAttempt]: 重试历史
        """
        with self._lock:
            return self._retry_history.get(operation_id, []).copy()

    def get_retry_statistics(self) -> Dict[str, Any]:
        """
        获取重试统计

        Returns:
            Dict[str, Any]: 重试统计信息
        """
        with self._lock:
            total_operations = len(self._retry_history)
            total_attempts = sum(len(attempts) for attempts in self._retry_history.values())
            successful_operations = sum(
                1 for attempts in self._retry_history.values()
                if attempts and attempts[-1].success
            )

            return {
                "total_operations": total_operations,
                "total_attempts": total_attempts,
                "successful_operations": successful_operations,
                "success_rate": successful_operations / total_operations if total_operations > 0 else 0,
                "avg_attempts_per_operation": total_attempts / total_operations if total_operations > 0 else 0
            }


class CircuitBreaker:
    """
    熔断器

    防止级联故障，提供快速失败机制
    """

    def __init__(self, name: str, config: Optional[CircuitBreakerConfig] = None) -> None:
        """
        初始化熔断器

        Args:
            name: 熔断器名称
            config: 熔断器配置
        """
        # 1. 初始化配置
        self.name = name
        self.config = config or CircuitBreakerConfig()

        # 2. 初始化状态
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.half_open_calls = 0

        # 3. 初始化线程安全
        self._lock = threading.Lock()

        # 4. 记录初始化
        logger.log(
            LogLevel.INFO,
            "circuit_breaker",
            "init",
            f"熔断器初始化: {name}",
            data={"config": self.config.model_dump()}
        )

    def call(self, operation: Callable[[], Any]) -> Any:
        """
        通过熔断器调用操作

        Args:
            operation: 要执行的操作

        Returns:
            Any: 操作结果

        Raises:
            Exception: 熔断器开启时抛出异常
        """
        with self._lock:
            # 1. 检查熔断器状态
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self.state = CircuitState.HALF_OPEN
                    self.half_open_calls = 0
                    logger.log(
                        LogLevel.INFO,
                        "circuit_breaker",
                        "half_open",
                        f"熔断器转为半开状态: {self.name}"
                    )
                else:
                    logger.log(
                        LogLevel.WARNING,
                        "circuit_breaker",
                        "blocked",
                        f"熔断器阻止调用: {self.name}"
                    )
                    raise Exception(f"熔断器开启，拒绝调用: {self.name}")

            if self.state == CircuitState.HALF_OPEN:
                if self.half_open_calls >= self.config.half_open_max_calls:
                    logger.log(
                        LogLevel.WARNING,
                        "circuit_breaker",
                        "half_open_limit",
                        f"半开状态调用限制: {self.name}"
                    )
                    raise Exception(f"熔断器半开状态调用次数达到限制: {self.name}")
                self.half_open_calls += 1

        # 2. 执行操作
        try:
            result = operation()

            # 3. 记录成功
            with self._lock:
                self._on_success()

            return result

        except Exception:
            # 4. 记录失败
            with self._lock:
                self._on_failure()
            raise

    def _should_attempt_reset(self) -> bool:
        """检查是否应该尝试重置熔断器"""
        if self.last_failure_time is None:
            return True

        timeout_threshold = self.last_failure_time + timedelta(
            milliseconds=self.config.timeout_ms
        )
        return datetime.now() >= timeout_threshold

    def _on_success(self) -> None:
        """处理成功调用"""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.success_count = 0
                logger.log(
                    LogLevel.INFO,
                    "circuit_breaker",
                    "closed",
                    f"熔断器恢复关闭状态: {self.name}"
                )
        else:
            self.failure_count = 0

    def _on_failure(self) -> None:
        """处理失败调用"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if self.state == CircuitState.CLOSED:
            if self.failure_count >= self.config.failure_threshold:
                self.state = CircuitState.OPEN
                logger.log(
                    LogLevel.ERROR,
                    "circuit_breaker",
                    "opened",
                    f"熔断器开启: {self.name}",
                    data={"failure_count": self.failure_count}
                )
        elif self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            logger.log(
                LogLevel.WARNING,
                "circuit_breaker",
                "reopened",
                f"熔断器重新开启: {self.name}"
            )

    def get_state(self) -> Dict[str, Any]:
        """
        获取熔断器状态

        Returns:
            Dict[str, Any]: 熔断器状态信息
        """
        with self._lock:
            return {
                "name": self.name,
                "state": self.state.value,
                "failure_count": self.failure_count,
                "success_count": self.success_count,
                "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None,
                "half_open_calls": self.half_open_calls
            }


# 全局错误恢复管理器实例
_global_error_recovery_manager: Optional[ErrorRecoveryManager] = None


def get_error_recovery_manager() -> ErrorRecoveryManager:
    """
    获取全局错误恢复管理器实例

    Returns:
        ErrorRecoveryManager: 错误恢复管理器实例
    """
    global _global_error_recovery_manager

    # 1. 初始化全局实例（如果需要）
    if _global_error_recovery_manager is None:
        _global_error_recovery_manager = ErrorRecoveryManager()
        logger.log(
            LogLevel.INFO,
            "error_recovery",
            "init_global",
            "初始化全局错误恢复管理器实例"
        )

    return _global_error_recovery_manager