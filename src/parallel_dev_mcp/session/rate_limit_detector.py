# -*- coding: utf-8 -*-
"""
限流检测管理器

@description 检测会话是否被限流并管理定时任务
"""

import asyncio
import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum

# 导入结构化日志
from .structured_logger import log_info, log_warning, log_error, LogCategory

# 配置日志系统
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class SessionType(Enum):
    """会话类型枚举"""
    MASTER = "master"
    CHILD = "child"


@dataclass
class ScheduledTask:
    """定时任务数据结构"""
    task_id: str
    session_type: SessionType
    created_at: datetime
    execute_at: datetime
    prompt: Optional[str] = None
    status: str = "pending"  # pending, executed, cancelled

    def is_ready(self) -> bool:
        """检查任务是否准备执行"""
        return datetime.now() >= self.execute_at and self.status == "pending"


class RateLimitDetector:
    """
    限流检测管理器

    检测会话限流状态并管理定时任务
    """

    def __init__(self, session_type: SessionType, session_id: str) -> None:
        """
        初始化限流检测器

        Args:
            session_type: 会话类型
            session_id: 会话标识
        """
        # 1. 基础配置
        self.session_type = session_type
        self.session_id = session_id
        self.is_running = False
        self.check_interval = 5  # 5秒检测间隔

        # 2. 限流检测配置
        self.rate_limit_threshold = 3  # 连续失败次数阈值
        self.consecutive_failures = 0
        self.last_successful_request = datetime.now()

        # 3. 定时任务管理
        self.scheduled_tasks: Dict[str, ScheduledTask] = {}
        self.task_counter = 0

        # 4. 线程管理
        self.detection_thread: Optional[threading.Thread] = None
        self.task_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # 5. 记录初始化
        log_info(
            LogCategory.SYSTEM,
            f"限流检测器初始化完成 - 会话类型: {session_type.value}, 会话ID: {session_id}"
        )

    def start_detection(self) -> Dict[str, Any]:
        """
        启动限流检测

        Returns:
            Dict[str, Any]: 启动结果
        """
        try:
            # 1. 检查运行状态
            if self.is_running:
                return {
                    "success": False,
                    "message": "限流检测已在运行中"
                }

            # 2. 启动检测线程
            self.is_running = True
            self._stop_event.clear()

            self.detection_thread = threading.Thread(
                target=self._detection_loop,
                daemon=True,
                name=f"RateLimit-{self.session_id}"
            )
            self.detection_thread.start()

            # 3. 启动任务执行线程
            self.task_thread = threading.Thread(
                target=self._task_execution_loop,
                daemon=True,
                name=f"TaskExec-{self.session_id}"
            )
            self.task_thread.start()

            # 4. 记录启动成功
            log_info(
                LogCategory.SESSION,
                f"限流检测启动成功 - {self.session_type.value} 会话 {self.session_id}"
            )

            return {
                "success": True,
                "message": "限流检测启动成功",
                "session_type": self.session_type.value,
                "session_id": self.session_id,
                "check_interval": self.check_interval
            }

        except Exception as e:
            # 5. 异常处理
            log_error(
                LogCategory.SYSTEM,
                f"启动限流检测失败: {str(e)}"
            )
            return {
                "success": False,
                "error": f"启动失败: {str(e)}"
            }

    def stop_detection(self) -> Dict[str, Any]:
        """
        停止限流检测

        Returns:
            Dict[str, Any]: 停止结果
        """
        try:
            # 1. 设置停止标志
            self.is_running = False
            self._stop_event.set()

            # 2. 等待线程结束
            if self.detection_thread and self.detection_thread.is_alive():
                self.detection_thread.join(timeout=10)

            if self.task_thread and self.task_thread.is_alive():
                self.task_thread.join(timeout=10)

            # 3. 取消所有待执行任务
            cancelled_count = 0
            for task in self.scheduled_tasks.values():
                if task.status == "pending":
                    task.status = "cancelled"
                    cancelled_count += 1

            # 4. 记录停止成功
            log_info(
                LogCategory.SESSION,
                f"限流检测停止成功 - {self.session_type.value} 会话 {self.session_id}, 取消任务: {cancelled_count}个"
            )

            return {
                "success": True,
                "message": "限流检测停止成功",
                "cancelled_tasks": cancelled_count
            }

        except Exception as e:
            # 5. 异常处理
            log_error(
                LogCategory.SYSTEM,
                f"停止限流检测失败: {str(e)}"
            )
            return {
                "success": False,
                "error": f"停止失败: {str(e)}"
            }

    def _detection_loop(self) -> None:
        """限流检测循环"""
        while self.is_running and not self._stop_event.is_set():
            try:
                # 1. 执行限流检测
                is_rate_limited = self._check_rate_limit()

                # 2. 如果检测到限流，创建定时任务
                if is_rate_limited:
                    self._create_scheduled_task()

                # 3. 等待下一次检测
                self._stop_event.wait(self.check_interval)

            except Exception as e:
                log_error(
                    LogCategory.SYSTEM,
                    f"限流检测循环异常: {str(e)}"
                )
                time.sleep(self.check_interval)

    def _task_execution_loop(self) -> None:
        """定时任务执行循环"""
        while self.is_running and not self._stop_event.is_set():
            try:
                # 1. 检查并执行就绪任务
                ready_tasks = [
                    task for task in self.scheduled_tasks.values()
                    if task.is_ready()
                ]

                for task in ready_tasks:
                    self._execute_task(task)

                # 2. 等待1秒后再次检查
                self._stop_event.wait(1)

            except Exception as e:
                log_error(
                    LogCategory.SYSTEM,
                    f"任务执行循环异常: {str(e)}"
                )
                time.sleep(1)

    def _check_rate_limit(self) -> bool:
        """
        检测是否被限流

        Returns:
            bool: 是否被限流
        """
        # 1. 模拟API请求检测（实际项目中应该是真实的API调用）
        try:
            # 这里应该是实际的API请求逻辑
            # 暂时使用模拟逻辑：基于连续失败次数判断

            # 2. 模拟请求结果
            import random
            request_success = random.random() > 0.1  # 90%成功率模拟

            if request_success:
                # 3. 请求成功，重置失败计数
                self.consecutive_failures = 0
                self.last_successful_request = datetime.now()
                return False
            else:
                # 4. 请求失败，增加失败计数
                self.consecutive_failures += 1

                if self.consecutive_failures >= self.rate_limit_threshold:
                    log_warning(
                        LogCategory.SESSION,
                        f"检测到限流 - {self.session_type.value} 会话 {self.session_id}, 连续失败 {self.consecutive_failures} 次"
                    )
                    return True

                return False

        except Exception as e:
            # 5. 异常视为失败
            self.consecutive_failures += 1
            log_error(
                LogCategory.SYSTEM,
                f"限流检测异常: {str(e)}"
            )
            return self.consecutive_failures >= self.rate_limit_threshold

    def _create_scheduled_task(self, delay_minutes: int = 5, prompt: Optional[str] = None) -> str:
        """
        创建定时任务

        Args:
            delay_minutes: 延时分钟数
            prompt: 任务提示信息

        Returns:
            str: 任务ID
        """
        # 1. 生成任务ID
        self.task_counter += 1
        task_id = f"task_{self.session_id}_{self.task_counter}_{int(time.time())}"

        # 2. 创建任务对象
        task = ScheduledTask(
            task_id=task_id,
            session_type=self.session_type,
            created_at=datetime.now(),
            execute_at=datetime.now() + timedelta(minutes=delay_minutes),
            prompt=prompt,
            status="pending"
        )

        # 3. 存储任务
        self.scheduled_tasks[task_id] = task

        # 4. 记录任务创建
        log_info(
            LogCategory.SESSION,
            f"创建定时任务 - 任务ID: {task_id}, 执行时间: {task.execute_at}, 会话类型: {self.session_type.value}"
        )

        return task_id

    def _execute_task(self, task: ScheduledTask) -> None:
        """
        执行定时任务

        Args:
            task: 要执行的任务
        """
        try:
            # 1. 标记任务为执行中
            task.status = "executed"

            # 2. 根据会话类型执行不同操作
            if task.session_type == SessionType.MASTER:
                # 主会话发送"继续"
                message = "继续"
                self._send_master_message(message)

            elif task.session_type == SessionType.CHILD:
                # 子会话发送"继续完成"或处理prompt
                if task.prompt:
                    message = f"继续完成{task.prompt}"
                else:
                    message = "继续完成"
                self._send_child_message(message)

            # 3. 记录任务执行
            log_info(
                LogCategory.SESSION,
                f"执行定时任务完成 - 任务ID: {task.task_id}, 消息: {message}"
            )

        except Exception as e:
            # 4. 异常处理
            task.status = "failed"
            log_error(
                LogCategory.SYSTEM,
                f"执行定时任务失败 - 任务ID: {task.task_id}, 错误: {str(e)}"
            )

    def _send_master_message(self, message: str) -> None:
        """
        发送主会话消息

        Args:
            message: 消息内容
        """
        # 这里应该集成实际的消息发送逻辑
        # 暂时使用日志记录
        log_info(
            LogCategory.MASTER,
            f"主会话消息: {message}"
        )

    def _send_child_message(self, message: str) -> None:
        """
        发送子会话消息

        Args:
            message: 消息内容
        """
        # 这里应该集成实际的消息发送逻辑
        # 暂时使用日志记录
        log_info(
            LogCategory.CHILD,
            f"子会话消息: {message}"
        )

    def get_status(self) -> Dict[str, Any]:
        """
        获取检测器状态

        Returns:
            Dict[str, Any]: 状态信息
        """
        # 1. 统计任务状态
        task_stats = {}
        for status in ["pending", "executed", "cancelled", "failed"]:
            task_stats[status] = len([
                t for t in self.scheduled_tasks.values()
                if t.status == status
            ])

        # 2. 返回状态信息
        return {
            "is_running": self.is_running,
            "session_type": self.session_type.value,
            "session_id": self.session_id,
            "consecutive_failures": self.consecutive_failures,
            "last_successful_request": self.last_successful_request.isoformat(),
            "total_tasks": len(self.scheduled_tasks),
            "task_stats": task_stats,
            "check_interval": self.check_interval
        }

    def add_prompt_task(self, prompt: str, delay_minutes: int = 5) -> str:
        """
        添加带prompt的定时任务

        Args:
            prompt: 任务提示
            delay_minutes: 延时分钟数

        Returns:
            str: 任务ID
        """
        return self._create_scheduled_task(delay_minutes, prompt)