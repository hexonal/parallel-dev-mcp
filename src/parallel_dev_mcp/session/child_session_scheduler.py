# -*- coding: utf-8 -*-
"""
子会话定时调度器

@description 实现子会话清单的定时刷新和消息处理
"""

import logging
import threading
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

from ..resources.master_resource import master_resource_manager
from .._internal.config_tools import get_environment_config

# 配置日志系统
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class SchedulerConfig(BaseModel):
    """
    调度器配置数据模型

    定义定时任务的执行参数
    """

    interval_seconds: int = Field(5, description="刷新间隔（秒）", ge=1, le=300)
    project_prefix: str = Field("parallel", description="项目前缀", min_length=1)
    cleanup_enabled: bool = Field(True, description="是否启用自动清理")
    cleanup_interval: int = Field(30, description="清理间隔（秒）", ge=10, le=3600)
    max_errors: int = Field(10, description="最大连续错误次数", ge=1, le=100)

    model_config = ConfigDict(
        # 1. JSON编码器配置
        json_encoders={},
        # 2. 示例数据
        json_schema_extra={
            "example": {
                "interval_seconds": 5,
                "project_prefix": "parallel",
                "cleanup_enabled": True,
                "cleanup_interval": 30,
                "max_errors": 10,
            }
        },
    )


class ChildSessionScheduler:
    """
    子会话定时调度器

    实现子会话清单的定时刷新和状态管理
    """

    def __init__(self, config: Optional[SchedulerConfig] = None) -> None:
        """
        初始化调度器

        Args:
            config: 调度器配置，如果为 None 则使用默认配置
        """
        # 1. 初始化配置
        if config is None:
            env_config = get_environment_config()
            config = SchedulerConfig(project_prefix=env_config.project_prefix)
        self.config = config

        # 2. 初始化状态
        self._is_running = False
        self._refresh_timer: Optional[threading.Timer] = None
        self._cleanup_timer: Optional[threading.Timer] = None
        self._lock = threading.RLock()
        self._error_count = 0
        self._last_refresh = None
        self._last_cleanup = None

        # 3. 记录初始化信息
        logger.info(f"子会话调度器初始化: 间隔={config.interval_seconds}秒")

    def start(self) -> bool:
        """
        启动定时调度器

        Returns:
            bool: 启动是否成功
        """
        with self._lock:
            # 1. 检查是否已经运行
            if self._is_running:
                logger.warning("调度器已在运行，无需重复启动")
                return True

            try:
                # 2. 启动刷新定时器
                self._start_refresh_timer()

                # 3. 启动清理定时器（如果启用）
                if self.config.cleanup_enabled:
                    self._start_cleanup_timer()

                # 4. 设置运行状态
                self._is_running = True
                self._error_count = 0

                # 5. 记录启动成功
                logger.info("子会话调度器启动成功")

                # 6. 返回成功状态
                return True

            except Exception as e:
                # 7. 处理启动失败
                logger.error(f"调度器启动失败: {e}")
                self._cleanup_timers()
                return False

    def stop(self) -> bool:
        """
        停止定时调度器

        Returns:
            bool: 停止是否成功
        """
        with self._lock:
            # 1. 检查是否正在运行
            if not self._is_running:
                logger.debug("调度器未运行，无需停止")
                return True

            try:
                # 2. 清理定时器
                self._cleanup_timers()

                # 3. 设置停止状态
                self._is_running = False

                # 4. 记录停止成功
                logger.info("子会话调度器停止成功")

                # 5. 返回成功状态
                return True

            except Exception as e:
                # 6. 处理停止失败
                logger.error(f"调度器停止失败: {e}")
                return False

    def is_running(self) -> bool:
        """
        检查调度器是否正在运行

        Returns:
            bool: 调度器运行状态
        """
        with self._lock:
            return self._is_running

    def get_status(self) -> dict:
        """
        获取调度器状态信息

        Returns:
            dict: 调度器状态字典
        """
        with self._lock:
            # 1. 收集状态信息
            status = {
                "is_running": self._is_running,
                "interval_seconds": self.config.interval_seconds,
                "project_prefix": self.config.project_prefix,
                "cleanup_enabled": self.config.cleanup_enabled,
                "error_count": self._error_count,
                "max_errors": self.config.max_errors,
                "last_refresh": (
                    self._last_refresh.isoformat() if self._last_refresh else None
                ),
                "last_cleanup": (
                    self._last_cleanup.isoformat() if self._last_cleanup else None
                ),
            }

            # 2. 返回状态信息
            return status

    def force_refresh(self) -> bool:
        """
        强制执行一次刷新

        Returns:
            bool: 刷新是否成功
        """
        # 1. 执行刷新操作
        return self._execute_refresh()

    def force_cleanup(self) -> int:
        """
        强制执行一次清理

        Returns:
            int: 清理的会话数量
        """
        # 1. 执行清理操作
        return self._execute_cleanup()

    def _start_refresh_timer(self) -> None:
        """
        启动刷新定时器

        内部方法，启动子会话清单刷新的定时器
        """
        # 1. 取消现有定时器
        if self._refresh_timer:
            self._refresh_timer.cancel()

        # 2. 创建新定时器
        self._refresh_timer = threading.Timer(
            self.config.interval_seconds, self._refresh_callback
        )

        # 3. 设置为守护线程
        self._refresh_timer.daemon = True

        # 4. 启动定时器
        self._refresh_timer.start()

        # 5. 记录启动信息
        logger.debug(f"刷新定时器启动: {self.config.interval_seconds}秒间隔")

    def _start_cleanup_timer(self) -> None:
        """
        启动清理定时器

        内部方法，启动子会话清理的定时器
        """
        # 1. 取消现有定时器
        if self._cleanup_timer:
            self._cleanup_timer.cancel()

        # 2. 创建新定时器
        self._cleanup_timer = threading.Timer(
            self.config.cleanup_interval, self._cleanup_callback
        )

        # 3. 设置为守护线程
        self._cleanup_timer.daemon = True

        # 4. 启动定时器
        self._cleanup_timer.start()

        # 5. 记录启动信息
        logger.debug(f"清理定时器启动: {self.config.cleanup_interval}秒间隔")

    def _cleanup_timers(self) -> None:
        """
        清理所有定时器

        内部方法，取消所有正在运行的定时器
        """
        # 1. 取消刷新定时器
        if self._refresh_timer:
            self._refresh_timer.cancel()
            self._refresh_timer = None

        # 2. 取消清理定时器
        if self._cleanup_timer:
            self._cleanup_timer.cancel()
            self._cleanup_timer = None

        # 3. 记录清理信息
        logger.debug("所有定时器已清理")

    def _refresh_callback(self) -> None:
        """
        刷新回调函数

        定时器回调，执行子会话清单刷新
        """
        try:
            # 1. 检查运行状态
            if not self._is_running:
                return

            # 2. 执行刷新操作
            success = self._execute_refresh()

            # 3. 处理执行结果
            if success:
                # 4. 重置错误计数
                self._error_count = 0
            else:
                # 5. 增加错误计数
                self._error_count += 1
                logger.warning(
                    f"刷新失败，错误计数: {self._error_count}/{self.config.max_errors}"
                )

                # 6. 检查是否超过最大错误次数
                if self._error_count >= self.config.max_errors:
                    logger.error("达到最大错误次数，停止调度器")
                    self.stop()
                    return

            # 7. 重新启动定时器
            if self._is_running:
                self._start_refresh_timer()

        except Exception as e:
            # 8. 处理回调异常
            logger.error(f"刷新回调异常: {e}")
            self._error_count += 1

            # 9. 重新启动定时器（如果仍在运行）
            if self._is_running:
                self._start_refresh_timer()

    def _cleanup_callback(self) -> None:
        """
        清理回调函数

        定时器回调，执行子会话清理
        """
        try:
            # 1. 检查运行状态
            if not self._is_running:
                return

            # 2. 执行清理操作
            cleaned_count = self._execute_cleanup()

            # 3. 记录清理结果
            if cleaned_count > 0:
                logger.info(f"定时清理完成，清理了 {cleaned_count} 个会话")
            else:
                logger.debug("定时清理完成，无需清理")

            # 4. 重新启动定时器
            if self._is_running:
                self._start_cleanup_timer()

        except Exception as e:
            # 5. 处理回调异常
            logger.error(f"清理回调异常: {e}")

            # 6. 重新启动定时器（如果仍在运行）
            if self._is_running:
                self._start_cleanup_timer()

    def _execute_refresh(self) -> bool:
        """
        执行刷新操作

        内部方法，执行子会话清单刷新

        Returns:
            bool: 刷新是否成功
        """
        try:
            # 1. 调用资源管理器刷新方法
            success = master_resource_manager.refresh_children_list(
                self.config.project_prefix
            )

            # 2. 更新最后刷新时间
            if success:
                self._last_refresh = datetime.now()
                logger.debug("子会话清单刷新成功")
            else:
                logger.warning("子会话清单刷新失败")

            # 3. 返回结果
            return success

        except Exception as e:
            # 4. 处理刷新异常
            logger.error(f"执行刷新异常: {e}")
            return False

    def _execute_cleanup(self) -> int:
        """
        执行清理操作

        内部方法，执行子会话清理

        Returns:
            int: 清理的会话数量
        """
        try:
            # 1. 调用资源管理器清理方法
            cleaned_count = master_resource_manager.cleanup_completed_sessions(
                self.config.project_prefix
            )

            # 2. 更新最后清理时间
            self._last_cleanup = datetime.now()

            # 3. 返回清理数量
            return cleaned_count

        except Exception as e:
            # 4. 处理清理异常
            logger.error(f"执行清理异常: {e}")
            return 0


# 全局调度器实例
child_session_scheduler = ChildSessionScheduler()


def create_child_session_scheduler(
    config: Optional[SchedulerConfig] = None,
) -> ChildSessionScheduler:
    """
    创建子会话调度器实例

    Args:
        config: 调度器配置

    Returns:
        ChildSessionScheduler: 配置好的调度器实例
    """
    # 1. 创建调度器实例
    scheduler = ChildSessionScheduler(config)

    # 2. 记录创建信息
    logger.info("子会话调度器实例创建成功")

    # 3. 返回调度器实例
    return scheduler


def start_global_scheduler() -> bool:
    """
    启动全局调度器

    Returns:
        bool: 启动是否成功
    """
    # 1. 启动全局调度器实例
    return child_session_scheduler.start()


def stop_global_scheduler() -> bool:
    """
    停止全局调度器

    Returns:
        bool: 停止是否成功
    """
    # 1. 停止全局调度器实例
    return child_session_scheduler.stop()


def get_global_scheduler_status() -> dict:
    """
    获取全局调度器状态

    Returns:
        dict: 调度器状态信息
    """
    # 1. 获取全局调度器状态
    return child_session_scheduler.get_status()
