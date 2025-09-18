# -*- coding: utf-8 -*-
"""
自动重试调度器

@description 在指定时间自动发送'继续执行'消息的调度器系统
"""

import json
import logging
import asyncio
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Callable, Any
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum, unique
import uuid

# 配置日志系统
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@unique
class RetryStatus(Enum):
    """重试状态枚举"""
    PENDING = "pending"
    SCHEDULED = "scheduled"
    EXECUTED = "executed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@unique
class RetryStrategy(Enum):
    """重试策略枚举"""
    IMMEDIATE = "immediate"      # 立即重试
    SCHEDULED = "scheduled"      # 定时重试
    EXPONENTIAL = "exponential"  # 指数退避
    FIXED_INTERVAL = "fixed"     # 固定间隔


class RetryConfig(BaseModel):
    """重试配置数据模型"""

    max_retries: int = Field(3, description="最大重试次数", ge=1, le=10)
    default_strategy: RetryStrategy = Field(RetryStrategy.SCHEDULED, description="默认重试策略")
    continue_message: str = Field("继续执行", description="继续执行消息内容")
    storage_file_path: str = Field(".retry_tasks.json", description="任务存储文件路径")
    check_interval_seconds: int = Field(60, description="检查间隔秒数", ge=10, le=300)
    max_concurrent_tasks: int = Field(5, description="最大并发任务数", ge=1, le=20)
    task_timeout_minutes: int = Field(30, description="任务超时分钟数", ge=5, le=120)

    model_config = ConfigDict()


class RetryTask(BaseModel):
    """重试任务数据模型"""

    task_id: str = Field(..., description="任务ID")
    retry_time: datetime = Field(..., description="重试时间")
    message: str = Field(..., description="重试消息内容")
    session_id: Optional[str] = Field(None, description="会话ID")
    project_id: Optional[str] = Field(None, description="项目ID")
    status: RetryStatus = Field(RetryStatus.PENDING, description="任务状态")
    strategy: RetryStrategy = Field(RetryStrategy.SCHEDULED, description="重试策略")
    attempt_count: int = Field(0, description="已尝试次数", ge=0)
    max_retries: int = Field(3, description="最大重试次数", ge=1)
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    last_attempt_at: Optional[datetime] = Field(None, description="最后尝试时间")
    next_retry_at: Optional[datetime] = Field(None, description="下次重试时间")
    error_message: Optional[str] = Field(None, description="错误消息")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="附加元数据")

    model_config = ConfigDict(
        # json_encoders deprecated in V2 - datetime fields will use default serialization
    )


class AutoRetryScheduler:
    """
    自动重试调度器

    负责管理和执行定时重试任务
    """

    def __init__(self, config: Optional[RetryConfig] = None) -> None:
        """
        初始化自动重试调度器

        Args:
            config: 重试配置，使用默认配置如果未提供
        """
        # 1. 设置重试配置
        self.config = config or RetryConfig()

        # 2. 初始化任务存储
        self.storage_path = Path(self.config.storage_file_path)
        self.retry_tasks: Dict[str, RetryTask] = {}

        # 3. 初始化调度器状态
        self.is_running = False
        self.scheduler_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()

        # 4. 初始化回调函数
        self.retry_callback: Optional[Callable[[RetryTask], bool]] = None

        # 5. 加载任务数据
        self._load_tasks()

        # 6. 记录初始化信息
        logger.info(f"自动重试调度器初始化: 检查间隔={self.config.check_interval_seconds}秒")

    def schedule_retry(self, retry_time: datetime, message: str, **kwargs) -> str:
        """
        安排重试任务

        Args:
            retry_time: 重试时间
            message: 重试消息
            **kwargs: 其他任务参数

        Returns:
            str: 任务ID
        """
        # 1. 生成任务ID
        task_id = str(uuid.uuid4())

        # 2. 创建重试任务
        task = RetryTask(
            task_id=task_id,
            retry_time=retry_time,
            message=message,
            session_id=kwargs.get("session_id"),
            project_id=kwargs.get("project_id"),
            strategy=kwargs.get("strategy", self.config.default_strategy),
            max_retries=kwargs.get("max_retries", self.config.max_retries),
            metadata=kwargs.get("metadata", {})
        )

        # 3. 计算下次重试时间
        task.next_retry_at = retry_time
        task.status = RetryStatus.SCHEDULED

        # 4. 添加到任务列表
        self.retry_tasks[task_id] = task

        # 5. 保存任务数据
        self._save_tasks()

        # 6. 记录调度信息
        logger.info(f"安排重试任务: {task_id}, 时间: {retry_time.isoformat()}")

        # 7. 返回任务ID
        return task_id

    def cancel_retry(self, task_id: str) -> bool:
        """
        取消重试任务

        Args:
            task_id: 任务ID

        Returns:
            bool: 是否取消成功
        """
        # 1. 检查任务是否存在
        if task_id not in self.retry_tasks:
            logger.warning(f"取消重试失败: 任务不存在 {task_id}")
            return False

        # 2. 取消任务
        task = self.retry_tasks[task_id]
        task.status = RetryStatus.CANCELLED

        # 3. 保存任务数据
        self._save_tasks()

        # 4. 记录取消信息
        logger.info(f"取消重试任务: {task_id}")

        # 5. 返回取消成功
        return True

    def start_scheduler(self, retry_callback: Optional[Callable[[RetryTask], bool]] = None) -> None:
        """
        启动调度器

        Args:
            retry_callback: 重试回调函数，返回True表示成功
        """
        # 1. 检查是否已运行
        if self.is_running:
            logger.warning("调度器已在运行")
            return

        # 2. 设置回调函数
        if retry_callback:
            self.retry_callback = retry_callback

        # 3. 启动调度器线程
        self.is_running = True
        self.stop_event.clear()
        self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.scheduler_thread.start()

        # 4. 记录启动信息
        logger.info("自动重试调度器已启动")

    def stop_scheduler(self) -> None:
        """停止调度器"""
        # 1. 设置停止标志
        if not self.is_running:
            logger.info("调度器未运行")
            return

        # 2. 停止调度器
        self.is_running = False
        self.stop_event.set()

        # 3. 等待线程结束
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=5.0)

        # 4. 记录停止信息
        logger.info("自动重试调度器已停止")

    def get_pending_tasks(self) -> List[RetryTask]:
        """
        获取待执行任务

        Returns:
            List[RetryTask]: 待执行任务列表
        """
        # 1. 过滤待执行任务
        pending_tasks = [
            task for task in self.retry_tasks.values()
            if task.status in [RetryStatus.PENDING, RetryStatus.SCHEDULED]
        ]

        # 2. 按重试时间排序
        pending_tasks.sort(key=lambda t: t.retry_time)

        # 3. 返回任务列表
        return pending_tasks

    def get_task_status(self, task_id: str) -> Optional[RetryTask]:
        """
        获取任务状态

        Args:
            task_id: 任务ID

        Returns:
            Optional[RetryTask]: 任务信息
        """
        # 1. 返回任务信息
        return self.retry_tasks.get(task_id)

    def cleanup_completed_tasks(self, older_than_hours: int = 24) -> int:
        """
        清理已完成任务

        Args:
            older_than_hours: 清理多少小时前的任务

        Returns:
            int: 清理的任务数量
        """
        # 1. 计算过期时间
        cutoff_time = datetime.now() - timedelta(hours=older_than_hours)

        # 2. 过滤需要清理的任务
        tasks_to_remove = []
        for task_id, task in self.retry_tasks.items():
            if (task.status in [RetryStatus.EXECUTED, RetryStatus.FAILED, RetryStatus.CANCELLED] and
                task.created_at < cutoff_time):
                tasks_to_remove.append(task_id)

        # 3. 删除任务
        for task_id in tasks_to_remove:
            del self.retry_tasks[task_id]

        # 4. 保存任务数据
        if tasks_to_remove:
            self._save_tasks()

        # 5. 记录清理信息
        cleanup_count = len(tasks_to_remove)
        if cleanup_count > 0:
            logger.info(f"清理已完成任务: {cleanup_count} 个")

        # 6. 返回清理数量
        return cleanup_count

    def _scheduler_loop(self) -> None:
        """调度器主循环"""
        # 1. 主循环
        while self.is_running and not self.stop_event.is_set():
            try:
                # 2. 检查待执行任务
                self._check_and_execute_tasks()

                # 3. 等待下次检查
                self.stop_event.wait(self.config.check_interval_seconds)

            except Exception as e:
                # 4. 处理循环异常
                logger.error(f"调度器循环异常: {e}")
                self.stop_event.wait(5)  # 异常后短暂等待

    def _check_and_execute_tasks(self) -> None:
        """检查并执行任务"""
        # 1. 获取当前时间
        current_time = datetime.now()

        # 2. 查找需要执行的任务
        tasks_to_execute = []
        for task in self.retry_tasks.values():
            if (task.status == RetryStatus.SCHEDULED and
                task.next_retry_at and
                task.next_retry_at <= current_time):
                tasks_to_execute.append(task)

        # 3. 执行任务
        for task in tasks_to_execute[:self.config.max_concurrent_tasks]:
            self._execute_retry_task(task)

    def _execute_retry_task(self, task: RetryTask) -> None:
        """
        执行重试任务

        Args:
            task: 重试任务
        """
        # 1. 更新任务状态
        task.attempt_count += 1
        task.last_attempt_at = datetime.now()
        task.status = RetryStatus.PENDING

        try:
            # 2. 执行重试回调
            success = False
            if self.retry_callback:
                success = self.retry_callback(task)
            else:
                logger.warning(f"未设置重试回调函数: {task.task_id}")

            # 3. 处理执行结果
            if success:
                task.status = RetryStatus.EXECUTED
                logger.info(f"重试任务执行成功: {task.task_id}")
            else:
                self._handle_retry_failure(task)

        except Exception as e:
            # 4. 处理执行异常
            task.error_message = str(e)
            logger.error(f"重试任务执行异常: {task.task_id}, 错误: {e}")
            self._handle_retry_failure(task)

        # 5. 保存任务数据
        self._save_tasks()

    def _handle_retry_failure(self, task: RetryTask) -> None:
        """
        处理重试失败

        Args:
            task: 失败的任务
        """
        # 1. 检查是否还能重试
        if task.attempt_count >= task.max_retries:
            task.status = RetryStatus.FAILED
            logger.error(f"重试任务最终失败: {task.task_id}, 尝试次数: {task.attempt_count}")
            return

        # 2. 计算下次重试时间
        next_retry_delay = self._calculate_retry_delay(task)
        task.next_retry_at = datetime.now() + next_retry_delay
        task.status = RetryStatus.SCHEDULED

        # 3. 记录重试安排
        logger.info(f"安排重试任务: {task.task_id}, 下次时间: {task.next_retry_at.isoformat()}")

    def _calculate_retry_delay(self, task: RetryTask) -> timedelta:
        """
        计算重试延迟

        Args:
            task: 重试任务

        Returns:
            timedelta: 延迟时间
        """
        # 1. 根据策略计算延迟
        if task.strategy == RetryStrategy.IMMEDIATE:
            return timedelta(seconds=30)
        elif task.strategy == RetryStrategy.EXPONENTIAL:
            # 指数退避: 2^attempt_count 分钟
            delay_minutes = min(2 ** task.attempt_count, 60)
            return timedelta(minutes=delay_minutes)
        elif task.strategy == RetryStrategy.FIXED_INTERVAL:
            return timedelta(minutes=5)
        else:  # SCHEDULED
            return timedelta(minutes=10)

    def _load_tasks(self) -> None:
        """从文件加载任务数据"""
        try:
            # 1. 检查文件是否存在
            if not self.storage_path.exists():
                return

            # 2. 读取文件内容
            content = self.storage_path.read_text(encoding='utf-8')
            data = json.loads(content)

            # 3. 解析任务数据
            for task_data in data.get('tasks', []):
                task = RetryTask(**task_data)
                self.retry_tasks[task.task_id] = task

            # 4. 记录加载信息
            logger.info(f"加载重试任务: {len(self.retry_tasks)} 个")

        except Exception as e:
            # 5. 处理加载异常
            logger.warning(f"加载重试任务失败: {e}")

    def _save_tasks(self) -> None:
        """保存任务数据到文件"""
        try:
            # 1. 序列化任务数据
            tasks_data = [task.model_dump() for task in self.retry_tasks.values()]
            data = {"tasks": tasks_data, "updated_at": datetime.now().isoformat()}

            # 2. 写入文件
            self.storage_path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding='utf-8'
            )

        except Exception as e:
            # 3. 处理保存异常
            logger.error(f"保存重试任务失败: {e}")

    def get_scheduler_status(self) -> Dict[str, Any]:
        """
        获取调度器状态

        Returns:
            Dict[str, Any]: 调度器状态信息
        """
        # 1. 统计任务状态
        status_counts = {}
        for status in RetryStatus:
            count = sum(1 for task in self.retry_tasks.values() if task.status == status)
            status_counts[status.value] = count

        # 2. 返回状态信息
        return {
            "is_running": self.is_running,
            "total_tasks": len(self.retry_tasks),
            "task_counts": status_counts,
            "check_interval": self.config.check_interval_seconds,
            "max_concurrent": self.config.max_concurrent_tasks,
            "storage_path": str(self.storage_path),
            "thread_alive": self.scheduler_thread.is_alive() if self.scheduler_thread else False
        }