# -*- coding: utf-8 -*-
"""
消息日志系统

@description 提供结构化日志记录和性能指标追踪
"""

import logging
import time
import threading
from datetime import datetime
from typing import Dict, Any, Optional, List
from enum import Enum, unique
from pydantic import BaseModel, Field
from collections import defaultdict, deque

# 配置日志系统
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@unique
class LogLevel(Enum):
    """日志级别枚举"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@unique
class MetricType(Enum):
    """指标类型枚举"""
    COUNTER = "counter"
    TIMER = "timer"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"


class LogEntry(BaseModel):
    """日志条目数据模型"""

    timestamp: datetime = Field(default_factory=datetime.now, description="时间戳")
    level: LogLevel = Field(..., description="日志级别")
    component: str = Field(..., description="组件名称")
    operation: str = Field(..., description="操作名称")
    request_id: Optional[str] = Field(None, description="请求ID")
    session_name: Optional[str] = Field(None, description="会话名称")
    message: str = Field(..., description="日志消息")
    data: Optional[Dict[str, Any]] = Field(None, description="附加数据")
    duration_ms: Optional[float] = Field(None, description="操作耗时(毫秒)")
    error_code: Optional[str] = Field(None, description="错误代码")


class MetricEntry(BaseModel):
    """指标条目数据模型"""

    timestamp: datetime = Field(default_factory=datetime.now, description="时间戳")
    metric_type: MetricType = Field(..., description="指标类型")
    name: str = Field(..., description="指标名称")
    value: float = Field(..., description="指标值")
    labels: Optional[Dict[str, str]] = Field(None, description="标签")
    unit: Optional[str] = Field(None, description="单位")


class MessageLogger:
    """
    消息日志记录器

    提供结构化日志记录和性能指标追踪
    """

    def __init__(self, max_log_entries: int = 10000) -> None:
        """
        初始化消息日志记录器

        Args:
            max_log_entries: 最大日志条目数
        """
        # 1. 初始化存储
        self.max_log_entries = max_log_entries
        self._log_entries: deque[LogEntry] = deque(maxlen=max_log_entries)
        self._metrics: deque[MetricEntry] = deque(maxlen=max_log_entries)

        # 2. 初始化统计
        self._counters: Dict[str, int] = defaultdict(int)
        self._timers: Dict[str, List[float]] = defaultdict(list)
        self._gauges: Dict[str, float] = {}

        # 3. 初始化线程安全
        self._lock = threading.Lock()

        # 4. 记录初始化
        logger.info("消息日志记录器初始化完成")

    def log(
        self,
        level: LogLevel,
        component: str,
        operation: str,
        message: str,
        request_id: Optional[str] = None,
        session_name: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        duration_ms: Optional[float] = None,
        error_code: Optional[str] = None
    ) -> None:
        """
        记录日志条目

        Args:
            level: 日志级别
            component: 组件名称
            operation: 操作名称
            message: 日志消息
            request_id: 请求ID
            session_name: 会话名称
            data: 附加数据
            duration_ms: 操作耗时
            error_code: 错误代码
        """
        # 1. 创建日志条目
        log_entry = LogEntry(
            level=level,
            component=component,
            operation=operation,
            message=message,
            request_id=request_id,
            session_name=session_name,
            data=data,
            duration_ms=duration_ms,
            error_code=error_code
        )

        # 2. 线程安全添加
        with self._lock:
            self._log_entries.append(log_entry)

        # 3. 输出到标准日志
        log_message = f"[{component}:{operation}] {message}"
        if request_id:
            log_message += f" (request_id: {request_id})"

        getattr(logger, level.value)(log_message)

    def record_metric(
        self,
        metric_type: MetricType,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None,
        unit: Optional[str] = None
    ) -> None:
        """
        记录性能指标

        Args:
            metric_type: 指标类型
            name: 指标名称
            value: 指标值
            labels: 标签
            unit: 单位
        """
        # 1. 创建指标条目
        metric_entry = MetricEntry(
            metric_type=metric_type,
            name=name,
            value=value,
            labels=labels,
            unit=unit
        )

        # 2. 线程安全处理
        with self._lock:
            # 3. 添加到指标存储
            self._metrics.append(metric_entry)

            # 4. 更新内部统计
            if metric_type == MetricType.COUNTER:
                self._counters[name] += value
            elif metric_type == MetricType.TIMER:
                self._timers[name].append(value)
            elif metric_type == MetricType.GAUGE:
                self._gauges[name] = value

    def start_timer(self, name: str) -> float:
        """
        开始计时

        Args:
            name: 计时器名称

        Returns:
            float: 开始时间戳
        """
        start_time = time.time() * 1000  # 转换为毫秒

        # 记录计时开始
        self.log(
            LogLevel.DEBUG,
            "timer",
            "start",
            f"计时器开始: {name}",
            data={"timer_name": name, "start_time": start_time}
        )

        return start_time

    def end_timer(self, name: str, start_time: float) -> float:
        """
        结束计时并记录

        Args:
            name: 计时器名称
            start_time: 开始时间戳

        Returns:
            float: 耗时(毫秒)
        """
        end_time = time.time() * 1000  # 转换为毫秒
        duration = end_time - start_time

        # 记录计时结果
        self.record_metric(MetricType.TIMER, name, duration, unit="ms")

        self.log(
            LogLevel.DEBUG,
            "timer",
            "end",
            f"计时器结束: {name}, 耗时: {duration:.2f}ms",
            data={"timer_name": name, "duration_ms": duration}
        )

        return duration

    def get_logs(
        self,
        level: Optional[LogLevel] = None,
        component: Optional[str] = None,
        request_id: Optional[str] = None,
        limit: int = 100
    ) -> List[LogEntry]:
        """
        获取日志条目

        Args:
            level: 过滤日志级别
            component: 过滤组件名称
            request_id: 过滤请求ID
            limit: 限制返回数量

        Returns:
            List[LogEntry]: 过滤后的日志条目
        """
        with self._lock:
            # 1. 获取所有日志
            logs = list(self._log_entries)

            # 2. 应用过滤条件
            if level:
                logs = [log for log in logs if log.level == level]
            if component:
                logs = [log for log in logs if log.component == component]
            if request_id:
                logs = [log for log in logs if log.request_id == request_id]

            # 3. 限制数量并返回最新的
            return logs[-limit:] if limit > 0 else logs

    def get_metrics_summary(self) -> Dict[str, Any]:
        """
        获取指标摘要

        Returns:
            Dict[str, Any]: 指标摘要信息
        """
        with self._lock:
            # 1. 计算计时器统计
            timer_stats = {}
            for name, values in self._timers.items():
                if values:
                    timer_stats[name] = {
                        "count": len(values),
                        "avg": sum(values) / len(values),
                        "min": min(values),
                        "max": max(values),
                        "total": sum(values)
                    }

            # 2. 返回汇总信息
            return {
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "timers": timer_stats,
                "total_log_entries": len(self._log_entries),
                "total_metrics": len(self._metrics)
            }


# 全局消息日志记录器实例
_global_message_logger: Optional[MessageLogger] = None


def get_message_logger() -> MessageLogger:
    """
    获取全局消息日志记录器实例

    Returns:
        MessageLogger: 消息日志记录器实例
    """
    global _global_message_logger

    # 1. 初始化全局实例（如果需要）
    if _global_message_logger is None:
        _global_message_logger = MessageLogger()
        logger.info("初始化全局消息日志记录器实例")

    return _global_message_logger