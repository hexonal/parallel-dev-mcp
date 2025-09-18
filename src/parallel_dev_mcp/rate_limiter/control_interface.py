# -*- coding: utf-8 -*-
"""
限流控制接口

@description 提供统一的状态查询和手动重置功能，整合所有限流组件的管理接口
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Union
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum, unique

from .rate_limiter_manager import RateLimiterManager, RateLimitConfig, RateLimitStatus
from .message_detector import FiveHourLimitDetector, LimitDetectionResult
from .auto_retry_scheduler import AutoRetryScheduler, RetryConfig, RetryTask
from .message_sender import DelayedMessageSender, DelayConfig, MessageSendResult
from .state_manager import StateManager, StateConfig, StateType

# 配置日志系统
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@unique
class ComponentType(Enum):
    """组件类型枚举"""
    RATE_LIMITER = "rate_limiter"
    MESSAGE_DETECTOR = "message_detector"
    RETRY_SCHEDULER = "retry_scheduler"
    MESSAGE_SENDER = "message_sender"
    STATE_MANAGER = "state_manager"


@unique
class SystemHealth(Enum):
    """系统健康状态枚举"""
    HEALTHY = "healthy"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ComponentStatus(BaseModel):
    """组件状态数据模型"""

    component_type: ComponentType = Field(..., description="组件类型")
    is_active: bool = Field(False, description="是否活跃")
    health_status: SystemHealth = Field(SystemHealth.HEALTHY, description="健康状态")
    status_data: Dict[str, Any] = Field(default_factory=dict, description="状态数据")
    error_message: Optional[str] = Field(None, description="错误消息")
    last_updated: datetime = Field(default_factory=datetime.now, description="最后更新时间")
    uptime_seconds: float = Field(0.0, description="运行时间（秒）")
    performance_metrics: Dict[str, Any] = Field(default_factory=dict, description="性能指标")

    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()}
    )


class SystemStatus(BaseModel):
    """系统状态数据模型"""

    overall_health: SystemHealth = Field(SystemHealth.HEALTHY, description="整体健康状态")
    components: Dict[str, ComponentStatus] = Field(default_factory=dict, description="组件状态")
    system_metrics: Dict[str, Any] = Field(default_factory=dict, description="系统指标")
    active_limits: List[Dict[str, Any]] = Field(default_factory=list, description="活跃限制")
    pending_tasks: List[Dict[str, Any]] = Field(default_factory=list, description="待处理任务")
    recent_activities: List[Dict[str, Any]] = Field(default_factory=list, description="最近活动")
    configuration_summary: Dict[str, Any] = Field(default_factory=dict, description="配置摘要")
    last_reset_time: Optional[datetime] = Field(None, description="最后重置时间")
    total_uptime_seconds: float = Field(0.0, description="总运行时间（秒）")

    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()}
    )


class ControlInterface:
    """
    限流控制接口

    提供统一的状态查询、重置控制和系统管理功能
    """

    def __init__(self) -> None:
        """
        初始化控制接口
        """
        # 1. 初始化组件实例
        self.rate_limiter: Optional[RateLimiterManager] = None
        self.message_detector: Optional[FiveHourLimitDetector] = None
        self.retry_scheduler: Optional[AutoRetryScheduler] = None
        self.message_sender: Optional[DelayedMessageSender] = None
        self.state_manager: Optional[StateManager] = None

        # 2. 初始化系统状态
        self.system_start_time = datetime.now()
        self.last_health_check = datetime.now()

        # 3. 记录初始化信息
        logger.info("限流控制接口初始化完成")

    def initialize_components(
        self,
        rate_limit_config: Optional[RateLimitConfig] = None,
        retry_config: Optional[RetryConfig] = None,
        delay_config: Optional[DelayConfig] = None,
        state_config: Optional[StateConfig] = None
    ) -> bool:
        """
        初始化所有组件

        Args:
            rate_limit_config: 限流配置
            retry_config: 重试配置
            delay_config: 延迟配置
            state_config: 状态配置

        Returns:
            bool: 是否初始化成功
        """
        try:
            # 1. 初始化限流管理器
            self.rate_limiter = RateLimiterManager(rate_limit_config)

            # 2. 初始化消息检测器
            self.message_detector = FiveHourLimitDetector()

            # 3. 初始化重试调度器
            self.retry_scheduler = AutoRetryScheduler(retry_config)

            # 4. 初始化消息发送器
            self.message_sender = DelayedMessageSender(delay_config)

            # 5. 初始化状态管理器
            self.state_manager = StateManager(state_config)

            # 6. 记录初始化成功
            logger.info("所有组件初始化完成")
            return True

        except Exception as e:
            # 7. 处理初始化异常
            logger.error(f"组件初始化失败: {e}")
            return False

    def get_system_status(self, detailed: bool = True) -> SystemStatus:
        """
        获取系统状态

        Args:
            detailed: 是否获取详细状态

        Returns:
            SystemStatus: 系统状态信息
        """
        # 1. 获取组件状态
        components = {}
        overall_health = SystemHealth.HEALTHY

        for component_type in ComponentType:
            try:
                # 2. 获取组件状态
                component_status = self._get_component_status(component_type, detailed)
                components[component_type.value] = component_status

                # 3. 更新整体健康状态
                if component_status.health_status.value == SystemHealth.CRITICAL.value:
                    overall_health = SystemHealth.CRITICAL
                elif (component_status.health_status.value == SystemHealth.ERROR.value and
                      overall_health != SystemHealth.CRITICAL):
                    overall_health = SystemHealth.ERROR
                elif (component_status.health_status.value == SystemHealth.WARNING.value and
                      overall_health == SystemHealth.HEALTHY):
                    overall_health = SystemHealth.WARNING

            except Exception as e:
                # 4. 处理组件状态获取异常
                logger.error(f"获取组件状态失败: {component_type.value}, 错误: {e}")
                overall_health = SystemHealth.ERROR

        # 5. 计算系统指标
        system_metrics = self._calculate_system_metrics()

        # 6. 获取活跃限制
        active_limits = self._get_active_limits()

        # 7. 获取待处理任务
        pending_tasks = self._get_pending_tasks()

        # 8. 获取最近活动
        recent_activities = self._get_recent_activities() if detailed else []

        # 9. 获取配置摘要
        config_summary = self._get_configuration_summary()

        # 10. 计算总运行时间
        total_uptime = (datetime.now() - self.system_start_time).total_seconds()

        # 11. 构建系统状态
        return SystemStatus(
            overall_health=overall_health,
            components=components,
            system_metrics=system_metrics,
            active_limits=active_limits,
            pending_tasks=pending_tasks,
            recent_activities=recent_activities,
            configuration_summary=config_summary,
            total_uptime_seconds=total_uptime
        )

    def reset_component(self, component_type: ComponentType, confirm: bool = False) -> bool:
        """
        重置指定组件

        Args:
            component_type: 组件类型
            confirm: 确认重置操作

        Returns:
            bool: 是否重置成功
        """
        if not confirm:
            logger.warning(f"重置组件需要确认参数: {component_type.value}")
            return False

        try:
            # 1. 根据组件类型执行重置
            if component_type == ComponentType.RATE_LIMITER and self.rate_limiter:
                result = self.rate_limiter.manual_reset()
                success = result.get("status") == "success"

            elif component_type == ComponentType.RETRY_SCHEDULER and self.retry_scheduler:
                # 停止并重新启动调度器
                self.retry_scheduler.stop_scheduler()
                self.retry_scheduler.cleanup_completed_tasks(0)  # 清理所有任务
                success = True

            elif component_type == ComponentType.MESSAGE_SENDER and self.message_sender:
                # 停止并清理发送器
                self.message_sender.stop_processor()
                self.message_sender.clear_history(0)  # 清理所有历史
                success = True

            elif component_type == ComponentType.STATE_MANAGER and self.state_manager:
                # 清空所有状态
                success = self.state_manager.clear_all_states(confirm=True)

            elif component_type == ComponentType.MESSAGE_DETECTOR:
                # 消息检测器无状态，重置总是成功
                success = True

            else:
                logger.error(f"未知组件类型或组件未初始化: {component_type.value}")
                success = False

            # 2. 记录重置结果
            if success:
                logger.info(f"组件重置成功: {component_type.value}")
            else:
                logger.error(f"组件重置失败: {component_type.value}")

            return success

        except Exception as e:
            # 3. 处理重置异常
            logger.error(f"重置组件异常: {component_type.value}, 错误: {e}")
            return False

    def reset_all_components(self, confirm: bool = False) -> Dict[str, bool]:
        """
        重置所有组件

        Args:
            confirm: 确认重置操作

        Returns:
            Dict[str, bool]: 各组件重置结果
        """
        if not confirm:
            logger.warning("重置所有组件需要确认参数")
            return {}

        # 1. 重置所有组件
        results = {}
        for component_type in ComponentType:
            results[component_type.value] = self.reset_component(component_type, confirm=True)

        # 2. 更新系统启动时间
        self.system_start_time = datetime.now()

        # 3. 记录全量重置
        success_count = sum(results.values())
        logger.info(f"全量重置完成: 成功 {success_count}/{len(results)} 个组件")

        return results

    def perform_health_check(self) -> Dict[str, Any]:
        """
        执行健康检查

        Returns:
            Dict[str, Any]: 健康检查结果
        """
        # 1. 记录检查时间
        self.last_health_check = datetime.now()

        # 2. 获取系统状态
        system_status = self.get_system_status(detailed=False)

        # 3. 执行专门的健康检查
        health_checks = {
            "overall_health": system_status.overall_health.value,
            "components_count": len(system_status.components),
            "active_components": sum(1 for comp in system_status.components.values() if comp.is_active),
            "error_components": [
                comp_name for comp_name, comp in system_status.components.items()
                if comp.health_status in [SystemHealth.ERROR, SystemHealth.CRITICAL]
            ],
            "system_uptime_hours": system_status.total_uptime_seconds / 3600,
            "check_timestamp": self.last_health_check.isoformat()
        }

        # 4. 添加详细检查项
        health_checks.update(self._perform_detailed_health_checks())

        return health_checks

    def get_component_status(self, component_type: ComponentType) -> Optional[ComponentStatus]:
        """
        获取单个组件状态

        Args:
            component_type: 组件类型

        Returns:
            Optional[ComponentStatus]: 组件状态
        """
        try:
            return self._get_component_status(component_type, detailed=True)
        except Exception as e:
            logger.error(f"获取组件状态失败: {component_type.value}, 错误: {e}")
            return None

    def _get_component_status(self, component_type: ComponentType, detailed: bool) -> ComponentStatus:
        """
        获取组件状态（内部方法）

        Args:
            component_type: 组件类型
            detailed: 是否获取详细信息

        Returns:
            ComponentStatus: 组件状态
        """
        # 1. 初始化状态
        status = ComponentStatus(component_type=component_type)

        try:
            # 2. 根据组件类型获取状态
            if component_type == ComponentType.RATE_LIMITER and self.rate_limiter:
                current_status = self.rate_limiter.get_current_status()
                status.is_active = True
                status.status_data = current_status.model_dump()
                status.health_status = SystemHealth.HEALTHY

            elif component_type == ComponentType.MESSAGE_DETECTOR and self.message_detector:
                status.is_active = True
                status.status_data = {
                    "supported_patterns": self.message_detector.get_supported_patterns()
                }
                status.health_status = SystemHealth.HEALTHY

            elif component_type == ComponentType.RETRY_SCHEDULER and self.retry_scheduler:
                scheduler_status = self.retry_scheduler.get_scheduler_status()
                status.is_active = scheduler_status["is_running"]
                status.status_data = scheduler_status
                status.health_status = SystemHealth.HEALTHY if status.is_active else SystemHealth.WARNING

            elif component_type == ComponentType.MESSAGE_SENDER and self.message_sender:
                queue_status = self.message_sender.get_queue_status()
                status.is_active = queue_status["is_running"]
                status.status_data = queue_status
                status.health_status = SystemHealth.HEALTHY if status.is_active else SystemHealth.WARNING

            elif component_type == ComponentType.STATE_MANAGER and self.state_manager:
                state_summary = self.state_manager.get_state_summary()
                status.is_active = True
                status.status_data = state_summary
                status.health_status = SystemHealth.HEALTHY

            else:
                # 3. 组件未初始化
                status.health_status = SystemHealth.ERROR
                status.error_message = "组件未初始化"

        except Exception as e:
            # 4. 处理状态获取异常
            status.health_status = SystemHealth.ERROR
            status.error_message = str(e)

        # 5. 更新时间戳
        status.last_updated = datetime.now()

        return status

    def _calculate_system_metrics(self) -> Dict[str, Any]:
        """计算系统指标"""
        # 1. 计算基础指标
        uptime_hours = (datetime.now() - self.system_start_time).total_seconds() / 3600

        metrics = {
            "uptime_hours": uptime_hours,
            "components_initialized": sum(1 for comp in [
                self.rate_limiter, self.message_detector, self.retry_scheduler,
                self.message_sender, self.state_manager
            ] if comp is not None),
            "last_health_check": self.last_health_check.isoformat()
        }

        # 2. 添加组件特定指标
        if self.rate_limiter:
            status = self.rate_limiter.get_current_status()
            metrics["rate_limiter"] = {
                "total_blocked_requests": status.total_blocked_requests,
                "current_state": status.state.value
            }

        if self.retry_scheduler:
            scheduler_status = self.retry_scheduler.get_scheduler_status()
            metrics["retry_scheduler"] = {
                "total_tasks": scheduler_status["total_tasks"],
                "is_running": scheduler_status["is_running"]
            }

        if self.message_sender:
            queue_status = self.message_sender.get_queue_status()
            metrics["message_sender"] = {
                "queue_size": queue_status["queue_size"],
                "concurrent_sends": queue_status["concurrent_sends"]
            }

        return metrics

    def _get_active_limits(self) -> List[Dict[str, Any]]:
        """获取活跃限制"""
        limits = []

        # 1. 获取限流状态
        if self.rate_limiter:
            status = self.rate_limiter.get_current_status()
            if status.state.value != "normal":
                limits.append({
                    "type": "rate_limit",
                    "state": status.state.value,
                    "next_allowed_time": status.next_allowed_time.isoformat() if status.next_allowed_time else None,
                    "requests_in_window": status.requests_in_window
                })

        return limits

    def _get_pending_tasks(self) -> List[Dict[str, Any]]:
        """获取待处理任务"""
        tasks = []

        # 1. 获取重试任务
        if self.retry_scheduler:
            pending_tasks = self.retry_scheduler.get_pending_tasks()
            for task in pending_tasks[:10]:  # 最多显示10个
                tasks.append({
                    "type": "retry_task",
                    "task_id": task.task_id,
                    "retry_time": task.retry_time.isoformat(),
                    "message": task.message,
                    "attempt_count": task.attempt_count
                })

        # 2. 获取消息队列
        if self.message_sender:
            queue_status = self.message_sender.get_queue_status()
            tasks.append({
                "type": "message_queue",
                "queue_size": queue_status["queue_size"],
                "next_send_time": queue_status["next_send_time"]
            })

        return tasks

    def _get_recent_activities(self) -> List[Dict[str, Any]]:
        """获取最近活动"""
        # 1. 这里可以从日志或历史记录中获取最近活动
        # 目前返回基础活动信息
        activities = [
            {
                "type": "system_status_check",
                "timestamp": datetime.now().isoformat(),
                "description": "系统状态检查"
            }
        ]

        return activities

    def _get_configuration_summary(self) -> Dict[str, Any]:
        """获取配置摘要"""
        config = {}

        # 1. 获取各组件配置
        if self.rate_limiter:
            config["rate_limiter"] = {
                "rate_limit_seconds": self.rate_limiter.config.rate_limit_seconds,
                "max_requests_per_interval": self.rate_limiter.config.max_requests_per_interval
            }

        if self.retry_scheduler:
            config["retry_scheduler"] = {
                "max_retries": self.retry_scheduler.config.max_retries,
                "check_interval_seconds": self.retry_scheduler.config.check_interval_seconds
            }

        if self.message_sender:
            config["message_sender"] = {
                "default_delay_seconds": self.message_sender.config.default_delay_seconds,
                "max_queue_size": self.message_sender.config.max_queue_size
            }

        return config

    def _perform_detailed_health_checks(self) -> Dict[str, Any]:
        """执行详细健康检查"""
        checks = {}

        # 1. 检查文件系统
        checks["file_system"] = self._check_file_system()

        # 2. 检查内存使用
        checks["memory_usage"] = self._check_memory_usage()

        # 3. 检查组件通信
        checks["component_communication"] = self._check_component_communication()

        return checks

    def _check_file_system(self) -> Dict[str, Any]:
        """检查文件系统"""
        try:
            # 1. 检查状态文件是否可写
            test_files = []
            if self.state_manager:
                for state_type in StateType:
                    file_path = self.state_manager.state_files[state_type]
                    test_files.append({
                        "file": str(file_path),
                        "exists": file_path.exists(),
                        "writable": file_path.parent.exists()
                    })

            return {
                "status": "healthy",
                "test_files": test_files
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }

    def _check_memory_usage(self) -> Dict[str, Any]:
        """检查内存使用"""
        try:
            # 1. 基础内存检查
            return {
                "status": "healthy",
                "note": "内存检查需要psutil库支持"
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }

    def _check_component_communication(self) -> Dict[str, Any]:
        """检查组件通信"""
        try:
            # 1. 检查组件间是否能正常通信
            communication_tests = []

            # 2. 测试消息检测器
            if self.message_detector:
                test_result = self.message_detector.detect_limit_message("test message")
                communication_tests.append({
                    "component": "message_detector",
                    "test": "detect_message",
                    "success": not test_result.detected  # 测试消息不应被检测为限制
                })

            return {
                "status": "healthy",
                "tests": communication_tests
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }