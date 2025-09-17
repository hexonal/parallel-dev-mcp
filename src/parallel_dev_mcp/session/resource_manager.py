# -*- coding: utf-8 -*-
"""
资源管理器

@description 提供Master和Child资源的统一管理接口，包含内存存储、状态管理和生命周期管理
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any, Set
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum, unique
import threading

from .models import MasterResourceModel, ChildResourceModel, RepoInfo, ChildStatus, MasterStatus

# 配置日志系统
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@unique
class ResourceEventType(Enum):
    """资源事件类型枚举"""
    MASTER_CREATED = "master_created"
    MASTER_UPDATED = "master_updated"
    MASTER_DELETED = "master_deleted"
    CHILD_ADDED = "child_added"
    CHILD_UPDATED = "child_updated"
    CHILD_REMOVED = "child_removed"
    AUTO_REFRESH_TRIGGERED = "auto_refresh_triggered"


class ResourceEvent(BaseModel):
    """资源事件数据模型"""

    event_type: ResourceEventType = Field(..., description="事件类型")
    project_id: str = Field(..., description="项目ID")
    timestamp: datetime = Field(default_factory=datetime.now, description="事件时间")
    data: Dict[str, Any] = Field(default_factory=dict, description="事件数据")
    source: str = Field("resource_manager", description="事件源")

    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()}
    )


class ResourceConfig(BaseModel):
    """资源管理配置"""

    auto_refresh_enabled: bool = Field(True, description="是否启用自动刷新")
    auto_refresh_interval_seconds: int = Field(5, description="自动刷新间隔秒数", ge=1, le=300)
    max_children_per_master: int = Field(50, description="每个Master最大子会话数", ge=1, le=200)
    event_history_max_size: int = Field(1000, description="事件历史最大数量", ge=10, le=10000)
    session_timeout_minutes: int = Field(60, description="会话超时分钟数", ge=5, le=1440)
    enable_event_callbacks: bool = Field(True, description="是否启用事件回调")

    model_config = ConfigDict()


class ResourceManager:
    """
    资源管理器

    提供Master和Child资源的统一管理，包含内存存储、状态管理和异步操作支持
    """

    def __init__(self, config: Optional[ResourceConfig] = None) -> None:
        """
        初始化资源管理器

        Args:
            config: 资源管理配置
        """
        # 1. 设置配置
        self.config = config or ResourceConfig()

        # 2. 初始化存储
        self.masters: Dict[str, MasterResourceModel] = {}
        self.resource_lock = asyncio.Lock()

        # 3. 初始化事件系统
        self.event_history: List[ResourceEvent] = []
        self.event_callbacks: List[Callable[[ResourceEvent], None]] = []

        # 4. 初始化自动刷新任务
        self.auto_refresh_task: Optional[asyncio.Task] = None
        self.refresh_stop_event = asyncio.Event()

        # 5. 记录初始化信息
        logger.info(f"资源管理器初始化: 自动刷新={self.config.auto_refresh_enabled}")

    async def create_master_resource(
        self,
        project_id: str,
        repo: RepoInfo,
        session_id: Optional[str] = None,
        project_name: Optional[str] = None
    ) -> MasterResourceModel:
        """
        创建Master资源

        Args:
            project_id: 项目ID
            repo: 仓库信息
            session_id: 会话ID
            project_name: 项目名称

        Returns:
            MasterResourceModel: 创建的Master资源
        """
        async with self.resource_lock:
            # 1. 检查项目ID是否已存在
            if project_id in self.masters:
                raise ValueError(f"项目ID已存在: {project_id}")

            # 2. 创建Master资源
            master = MasterResourceModel(
                project_id=project_id,
                repo=repo,
                session_id=session_id,
                project_name=project_name or project_id,
                auto_refresh_enabled=self.config.auto_refresh_enabled
            )

            # 3. 存储资源
            self.masters[project_id] = master

            # 4. 触发事件
            await self._emit_event(ResourceEventType.MASTER_CREATED, project_id, {
                "session_id": session_id,
                "repo_remote": repo.remote,
                "repo_branch": repo.branch
            })

            # 5. 启动自动刷新（如果需要）
            if self.config.auto_refresh_enabled and session_id is None:
                await self._start_auto_refresh()

            # 6. 记录创建信息
            logger.info(f"创建Master资源: {project_id}")

            return master

    async def update_master_resource(
        self,
        project_id: str,
        session_id: Optional[str] = None,
        repo: Optional[RepoInfo] = None,
        status: Optional[MasterStatus] = None,
        configuration: Optional[Dict[str, Any]] = None
    ) -> Optional[MasterResourceModel]:
        """
        更新Master资源

        Args:
            project_id: 项目ID
            session_id: 新的会话ID
            repo: 新的仓库信息
            status: 新的状态
            configuration: 新的配置

        Returns:
            Optional[MasterResourceModel]: 更新后的Master资源
        """
        async with self.resource_lock:
            # 1. 检查资源是否存在
            if project_id not in self.masters:
                logger.warning(f"Master资源不存在: {project_id}")
                return None

            # 2. 获取资源
            master = self.masters[project_id]

            # 3. 更新字段
            update_data = {}
            if session_id is not None:
                master.session_id = session_id
                update_data["session_id"] = session_id

            if repo is not None:
                master.repo = repo
                update_data["repo"] = repo.model_dump()

            if status is not None:
                master.status = status
                update_data["status"] = status.value

            if configuration is not None:
                master.configuration.update(configuration)
                update_data["configuration"] = configuration

            # 4. 更新时间戳
            master.updated_at = datetime.now()

            # 5. 触发事件
            await self._emit_event(ResourceEventType.MASTER_UPDATED, project_id, update_data)

            # 6. 检查是否需要启动/停止自动刷新
            await self._manage_auto_refresh(master)

            # 7. 记录更新信息
            logger.info(f"更新Master资源: {project_id}")

            return master

    async def delete_master_resource(self, project_id: str) -> bool:
        """
        删除Master资源

        Args:
            project_id: 项目ID

        Returns:
            bool: 是否删除成功
        """
        async with self.resource_lock:
            # 1. 检查资源是否存在
            if project_id not in self.masters:
                logger.warning(f"Master资源不存在: {project_id}")
                return False

            # 2. 获取资源信息
            master = self.masters[project_id]
            children_count = len(master.children)

            # 3. 删除资源
            del self.masters[project_id]

            # 4. 触发事件
            await self._emit_event(ResourceEventType.MASTER_DELETED, project_id, {
                "children_count": children_count
            })

            # 5. 检查是否需要停止自动刷新
            await self._check_stop_auto_refresh()

            # 6. 记录删除信息
            logger.info(f"删除Master资源: {project_id}")

            return True

    async def add_child_resource(
        self,
        project_id: str,
        child: ChildResourceModel
    ) -> bool:
        """
        添加Child资源

        Args:
            project_id: 项目ID
            child: Child资源模型

        Returns:
            bool: 是否添加成功
        """
        async with self.resource_lock:
            # 1. 检查Master资源是否存在
            if project_id not in self.masters:
                logger.warning(f"Master资源不存在: {project_id}")
                return False

            # 2. 获取Master资源
            master = self.masters[project_id]

            # 3. 检查子会话数量限制
            if len(master.children) >= self.config.max_children_per_master:
                logger.warning(f"子会话数量已达上限: {len(master.children)}")
                return False

            try:
                # 4. 添加子会话
                master.add_child(child)

                # 5. 触发事件
                await self._emit_event(ResourceEventType.CHILD_ADDED, project_id, {
                    "task_id": child.task_id,
                    "session_name": child.session_name,
                    "status": child.status.value
                })

                # 6. 记录添加信息
                logger.info(f"添加Child资源: {project_id}/{child.task_id}")

                return True

            except ValueError as e:
                # 7. 处理添加异常
                logger.error(f"添加Child资源失败: {e}")
                return False

    async def update_child_resource(
        self,
        project_id: str,
        task_id: str,
        status: Optional[ChildStatus] = None,
        reason: Optional[str] = None,
        transcript: Optional[str] = None,
        exit_code: Optional[int] = None,
        duration_seconds: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        更新Child资源

        Args:
            project_id: 项目ID
            task_id: 任务ID
            status: 新状态
            reason: 状态原因
            transcript: 会话记录
            exit_code: 退出码
            duration_seconds: 运行时长
            metadata: 附加元数据

        Returns:
            bool: 是否更新成功
        """
        async with self.resource_lock:
            # 1. 检查Master资源是否存在
            if project_id not in self.masters:
                logger.warning(f"Master资源不存在: {project_id}")
                return False

            # 2. 获取Master资源
            master = self.masters[project_id]

            # 3. 查找Child资源
            child = master.get_child(task_id)
            if not child:
                logger.warning(f"Child资源不存在: {project_id}/{task_id}")
                return False

            # 4. 更新字段
            update_data = {}
            if status is not None:
                child.status = status
                update_data["status"] = status.value

            if reason is not None:
                child.reason = reason
                update_data["reason"] = reason

            if transcript is not None:
                child.transcript = transcript
                update_data["transcript_length"] = len(transcript)

            if exit_code is not None:
                child.exit_code = exit_code
                update_data["exit_code"] = exit_code

            if duration_seconds is not None:
                child.duration_seconds = duration_seconds
                update_data["duration_seconds"] = duration_seconds

            if metadata is not None:
                child.metadata.update(metadata)
                update_data["metadata"] = metadata

            # 5. 更新时间戳
            child.last_update = datetime.now()
            master.updated_at = datetime.now()

            # 6. 更新Master计数
            master._update_active_children_count()

            # 7. 触发事件
            await self._emit_event(ResourceEventType.CHILD_UPDATED, project_id, {
                "task_id": task_id,
                **update_data
            })

            # 8. 记录更新信息
            logger.info(f"更新Child资源: {project_id}/{task_id}")

            return True

    async def remove_child_resource(self, project_id: str, task_id: str) -> bool:
        """
        移除Child资源

        Args:
            project_id: 项目ID
            task_id: 任务ID

        Returns:
            bool: 是否移除成功
        """
        async with self.resource_lock:
            # 1. 检查Master资源是否存在
            if project_id not in self.masters:
                logger.warning(f"Master资源不存在: {project_id}")
                return False

            # 2. 获取Master资源
            master = self.masters[project_id]

            # 3. 移除Child资源
            if master.remove_child(task_id):
                # 4. 触发事件
                await self._emit_event(ResourceEventType.CHILD_REMOVED, project_id, {
                    "task_id": task_id
                })

                # 5. 记录移除信息
                logger.info(f"移除Child资源: {project_id}/{task_id}")
                return True

            # 6. 未找到指定的Child资源
            logger.warning(f"Child资源不存在: {project_id}/{task_id}")
            return False

    async def get_master_resource(self, project_id: str) -> Optional[MasterResourceModel]:
        """
        获取Master资源

        Args:
            project_id: 项目ID

        Returns:
            Optional[MasterResourceModel]: Master资源
        """
        async with self.resource_lock:
            return self.masters.get(project_id)

    async def get_child_resource(self, project_id: str, task_id: str) -> Optional[ChildResourceModel]:
        """
        获取Child资源

        Args:
            project_id: 项目ID
            task_id: 任务ID

        Returns:
            Optional[ChildResourceModel]: Child资源
        """
        async with self.resource_lock:
            # 1. 获取Master资源
            master = self.masters.get(project_id)
            if not master:
                return None

            # 2. 获取Child资源
            return master.get_child(task_id)

    async def list_master_resources(self) -> List[MasterResourceModel]:
        """
        列出所有Master资源

        Returns:
            List[MasterResourceModel]: Master资源列表
        """
        async with self.resource_lock:
            return list(self.masters.values())

    async def list_child_resources(self, project_id: str) -> List[ChildResourceModel]:
        """
        列出指定项目的所有Child资源

        Args:
            project_id: 项目ID

        Returns:
            List[ChildResourceModel]: Child资源列表
        """
        async with self.resource_lock:
            # 1. 获取Master资源
            master = self.masters.get(project_id)
            if not master:
                return []

            # 2. 返回Child资源列表
            return master.children.copy()

    async def get_resource_statistics(self) -> Dict[str, Any]:
        """
        获取资源统计信息

        Returns:
            Dict[str, Any]: 统计信息
        """
        async with self.resource_lock:
            # 1. 基础统计
            total_masters = len(self.masters)
            total_children = sum(len(master.children) for master in self.masters.values())

            # 2. 状态统计
            master_status_counts = {}
            child_status_counts = {}

            for master in self.masters.values():
                # Master状态统计
                status = master.status.value
                master_status_counts[status] = master_status_counts.get(status, 0) + 1

                # Child状态统计
                for child in master.children:
                    child_status = child.status.value
                    child_status_counts[child_status] = child_status_counts.get(child_status, 0) + 1

            # 3. 会话统计
            masters_with_session = sum(1 for master in self.masters.values() if master.session_id)
            masters_without_session = total_masters - masters_with_session

            # 4. 自动刷新统计
            auto_refresh_running = self.auto_refresh_task is not None and not self.auto_refresh_task.done()

            return {
                "total_masters": total_masters,
                "total_children": total_children,
                "masters_with_session": masters_with_session,
                "masters_without_session": masters_without_session,
                "master_status_counts": master_status_counts,
                "child_status_counts": child_status_counts,
                "auto_refresh_running": auto_refresh_running,
                "event_history_size": len(self.event_history),
                "config": self.config.model_dump()
            }

    async def add_event_callback(self, callback: Callable[[ResourceEvent], None]) -> None:
        """
        添加事件回调

        Args:
            callback: 事件回调函数
        """
        # 1. 添加回调函数
        if callback not in self.event_callbacks:
            self.event_callbacks.append(callback)
            logger.info("添加事件回调函数")

    async def remove_event_callback(self, callback: Callable[[ResourceEvent], None]) -> None:
        """
        移除事件回调

        Args:
            callback: 事件回调函数
        """
        # 1. 移除回调函数
        if callback in self.event_callbacks:
            self.event_callbacks.remove(callback)
            logger.info("移除事件回调函数")

    async def cleanup_expired_resources(self, timeout_minutes: Optional[int] = None) -> int:
        """
        清理过期资源

        Args:
            timeout_minutes: 超时分钟数

        Returns:
            int: 清理的资源数量
        """
        # 1. 使用配置的超时时间
        timeout = timeout_minutes or self.config.session_timeout_minutes
        cutoff_time = datetime.now() - timedelta(minutes=timeout)

        async with self.resource_lock:
            # 2. 查找过期的Master资源
            expired_masters = []
            for project_id, master in self.masters.items():
                if master.updated_at < cutoff_time and master.status == MasterStatus.INACTIVE:
                    expired_masters.append(project_id)

            # 3. 删除过期资源
            for project_id in expired_masters:
                await self.delete_master_resource(project_id)

            # 4. 记录清理信息
            if expired_masters:
                logger.info(f"清理过期资源: {len(expired_masters)} 个")

            return len(expired_masters)

    async def _emit_event(self, event_type: ResourceEventType, project_id: str, data: Dict[str, Any]) -> None:
        """
        触发事件

        Args:
            event_type: 事件类型
            project_id: 项目ID
            data: 事件数据
        """
        # 1. 创建事件
        event = ResourceEvent(
            event_type=event_type,
            project_id=project_id,
            data=data
        )

        # 2. 添加到历史记录
        self.event_history.append(event)

        # 3. 限制历史记录大小
        if len(self.event_history) > self.config.event_history_max_size:
            self.event_history = self.event_history[-self.config.event_history_max_size:]

        # 4. 触发回调
        if self.config.enable_event_callbacks:
            for callback in self.event_callbacks:
                try:
                    callback(event)
                except Exception as e:
                    logger.error(f"事件回调异常: {e}")

    async def _start_auto_refresh(self) -> None:
        """启动自动刷新任务"""
        # 1. 检查是否已启动
        if self.auto_refresh_task and not self.auto_refresh_task.done():
            return

        # 2. 启动自动刷新任务
        self.refresh_stop_event.clear()
        self.auto_refresh_task = asyncio.create_task(self._auto_refresh_loop())
        logger.info("启动自动刷新任务")

    async def _stop_auto_refresh(self) -> None:
        """停止自动刷新任务"""
        # 1. 设置停止事件
        self.refresh_stop_event.set()

        # 2. 取消任务
        if self.auto_refresh_task and not self.auto_refresh_task.done():
            self.auto_refresh_task.cancel()
            try:
                await self.auto_refresh_task
            except asyncio.CancelledError:
                pass

        logger.info("停止自动刷新任务")

    async def _auto_refresh_loop(self) -> None:
        """自动刷新主循环"""
        while not self.refresh_stop_event.is_set():
            try:
                # 1. 执行刷新
                await self._perform_auto_refresh()

                # 2. 等待下次刷新
                await asyncio.wait_for(
                    self.refresh_stop_event.wait(),
                    timeout=self.config.auto_refresh_interval_seconds
                )

            except asyncio.TimeoutError:
                # 正常的超时，继续循环
                continue
            except Exception as e:
                logger.error(f"自动刷新异常: {e}")
                await asyncio.sleep(5)  # 异常后短暂等待

    async def _perform_auto_refresh(self) -> None:
        """执行自动刷新"""
        async with self.resource_lock:
            # 1. 查找需要刷新的Master资源
            refresh_count = 0
            for project_id, master in self.masters.items():
                if master.session_id is None and master.auto_refresh_enabled:
                    # 2. 更新刷新时间
                    master.last_refresh = datetime.now()
                    refresh_count += 1

                    # 3. 触发刷新事件
                    await self._emit_event(ResourceEventType.AUTO_REFRESH_TRIGGERED, project_id, {
                        "refresh_time": master.last_refresh.isoformat()
                    })

            # 4. 记录刷新信息
            if refresh_count > 0:
                logger.debug(f"自动刷新: {refresh_count} 个资源")

    async def _manage_auto_refresh(self, master: MasterResourceModel) -> None:
        """管理自动刷新状态"""
        # 1. 检查是否需要启动自动刷新
        if master.session_id is None and self.config.auto_refresh_enabled:
            await self._start_auto_refresh()
        else:
            # 2. 检查是否需要停止自动刷新
            await self._check_stop_auto_refresh()

    async def _check_stop_auto_refresh(self) -> None:
        """检查是否需要停止自动刷新"""
        # 1. 检查是否还有需要刷新的资源
        async with self.resource_lock:
            needs_refresh = any(
                master.session_id is None and master.auto_refresh_enabled
                for master in self.masters.values()
            )

        # 2. 如果没有需要刷新的资源，停止自动刷新
        if not needs_refresh:
            await self._stop_auto_refresh()


# 全局资源管理器实例
_global_resource_manager: Optional[ResourceManager] = None


def get_resource_manager() -> ResourceManager:
    """
    获取全局资源管理器实例

    Returns:
        ResourceManager: 全局资源管理器实例
    """
    global _global_resource_manager

    # 1. 初始化全局实例（如果需要）
    if _global_resource_manager is None:
        config = ResourceConfig(
            auto_refresh_enabled=True,
            auto_refresh_interval_seconds=5,
            max_children_per_master=50
        )
        _global_resource_manager = ResourceManager(config)
        logger.info("初始化全局资源管理器实例")

    return _global_resource_manager