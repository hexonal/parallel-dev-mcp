# -*- coding: utf-8 -*-
"""
会话生命周期集成

@description 将资源管理与Master和Child会话生命周期集成，确保资源状态与会话状态同步
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional, Callable, List
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum, unique

from .resource_manager import ResourceManager, ResourceEvent, ResourceEventType
from .models import MasterResourceModel, ChildResourceModel, RepoInfo, ChildStatus, MasterStatus
from .mcp_resources import get_resource_manager

# 配置日志系统
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@unique
class SessionEventType(Enum):
    """会话事件类型枚举"""
    MASTER_SESSION_STARTED = "master_session_started"
    MASTER_SESSION_UPDATED = "master_session_updated"
    MASTER_SESSION_STOPPED = "master_session_stopped"
    CHILD_SESSION_CREATED = "child_session_created"
    CHILD_SESSION_STARTED = "child_session_started"
    CHILD_SESSION_UPDATED = "child_session_updated"
    CHILD_SESSION_COMPLETED = "child_session_completed"
    CHILD_SESSION_FAILED = "child_session_failed"
    CHILD_SESSION_TERMINATED = "child_session_terminated"


class SessionEvent(BaseModel):
    """会话事件数据模型"""

    event_type: SessionEventType = Field(..., description="事件类型")
    project_id: str = Field(..., description="项目ID")
    task_id: Optional[str] = Field(None, description="任务ID（Child会话专用）")
    session_id: Optional[str] = Field(None, description="会话ID")
    session_name: Optional[str] = Field(None, description="会话名称")
    timestamp: datetime = Field(default_factory=datetime.now, description="事件时间")
    data: Dict[str, Any] = Field(default_factory=dict, description="事件数据")
    source: str = Field("lifecycle_integration", description="事件源")

    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()}
    )


class LifecycleConfig(BaseModel):
    """生命周期集成配置"""

    auto_create_resources: bool = Field(True, description="是否自动创建资源")
    auto_update_status: bool = Field(True, description="是否自动更新状态")
    auto_cleanup_completed: bool = Field(True, description="是否自动清理已完成的会话")
    max_session_duration_hours: int = Field(24, description="最大会话持续时间（小时）", ge=1, le=168)
    enable_lifecycle_callbacks: bool = Field(True, description="是否启用生命周期回调")
    resource_sync_interval_seconds: int = Field(30, description="资源同步间隔秒数", ge=10, le=300)

    model_config = ConfigDict()


class LifecycleIntegration:
    """
    会话生命周期集成器

    负责将资源管理与会话生命周期事件集成，确保资源状态与会话状态保持同步
    """

    def __init__(self, config: Optional[LifecycleConfig] = None) -> None:
        """
        初始化生命周期集成器

        Args:
            config: 生命周期集成配置
        """
        # 1. 设置配置
        self.config = config or LifecycleConfig()

        # 2. 获取资源管理器
        self.resource_manager = get_resource_manager()

        # 3. 初始化事件处理器
        self.event_handlers: Dict[SessionEventType, List[Callable]] = {
            event_type: [] for event_type in SessionEventType
        }

        # 4. 注册资源事件回调
        asyncio.create_task(self._register_resource_callbacks())

        # 5. 记录初始化信息
        logger.info("会话生命周期集成器初始化完成")

    async def handle_master_session_started(
        self,
        project_id: str,
        session_id: str,
        repo: RepoInfo,
        project_name: Optional[str] = None,
        configuration: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        处理Master会话启动事件

        Args:
            project_id: 项目ID
            session_id: 会话ID
            repo: 仓库信息
            project_name: 项目名称
            configuration: 配置信息

        Returns:
            bool: 是否处理成功
        """
        try:
            # 1. 检查是否已存在Master资源
            existing_master = await self.resource_manager.get_master_resource(project_id)

            if existing_master is not None:
                # 2. 更新现有资源
                await self.resource_manager.update_master_resource(
                    project_id=project_id,
                    session_id=session_id,
                    repo=repo,
                    status=MasterStatus.ACTIVE,
                    configuration=configuration or {}
                )
                logger.info(f"更新Master会话资源: {project_id}")

            else:
                # 3. 创建新Master资源
                await self.resource_manager.create_master_resource(
                    project_id=project_id,
                    repo=repo,
                    session_id=session_id,
                    project_name=project_name or project_id
                )
                logger.info(f"创建Master会话资源: {project_id}")

            # 4. 触发会话事件
            await self._emit_session_event(
                SessionEventType.MASTER_SESSION_STARTED,
                project_id,
                session_id=session_id,
                data={
                    "repo_remote": repo.remote,
                    "repo_branch": repo.branch,
                    "project_name": project_name
                }
            )

            return True

        except Exception as e:
            # 5. 处理异常
            logger.error(f"处理Master会话启动失败: {project_id}, 错误: {e}")
            return False

    async def handle_master_session_stopped(
        self,
        project_id: str,
        session_id: Optional[str] = None,
        cleanup_children: bool = True
    ) -> bool:
        """
        处理Master会话停止事件

        Args:
            project_id: 项目ID
            session_id: 会话ID
            cleanup_children: 是否清理子会话

        Returns:
            bool: 是否处理成功
        """
        try:
            # 1. 获取Master资源
            master = await self.resource_manager.get_master_resource(project_id)
            if master is None:
                logger.warning(f"Master资源不存在: {project_id}")
                return False

            # 2. 处理子会话清理
            if cleanup_children and self.config.auto_cleanup_completed:
                for child in master.children:
                    if child.status in [ChildStatus.COMPLETED, ChildStatus.FAILED, ChildStatus.CANCELLED]:
                        await self.resource_manager.remove_child_resource(project_id, child.task_id)
                        logger.info(f"清理已完成的Child会话: {project_id}/{child.task_id}")

            # 3. 更新Master状态
            await self.resource_manager.update_master_resource(
                project_id=project_id,
                session_id=None,
                status=MasterStatus.INACTIVE
            )

            # 4. 触发会话事件
            await self._emit_session_event(
                SessionEventType.MASTER_SESSION_STOPPED,
                project_id,
                session_id=session_id,
                data={
                    "children_count": len(master.children),
                    "cleanup_children": cleanup_children
                }
            )

            logger.info(f"处理Master会话停止: {project_id}")
            return True

        except Exception as e:
            # 5. 处理异常
            logger.error(f"处理Master会话停止失败: {project_id}, 错误: {e}")
            return False

    async def handle_child_session_created(
        self,
        project_id: str,
        task_id: str,
        session_name: str,
        worktree_path: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        处理Child会话创建事件

        Args:
            project_id: 项目ID
            task_id: 任务ID
            session_name: 会话名称
            worktree_path: 工作树路径
            metadata: 附加元数据

        Returns:
            bool: 是否处理成功
        """
        try:
            # 1. 创建Child资源
            child = ChildResourceModel(
                session_name=session_name,
                task_id=task_id,
                status=ChildStatus.PENDING,
                project_id=project_id,
                worktree_path=worktree_path,
                metadata=metadata or {}
            )

            # 2. 添加到Master资源
            success = await self.resource_manager.add_child_resource(project_id, child)
            if not success:
                logger.error(f"添加Child资源失败: {project_id}/{task_id}")
                return False

            # 3. 触发会话事件
            await self._emit_session_event(
                SessionEventType.CHILD_SESSION_CREATED,
                project_id,
                task_id=task_id,
                session_name=session_name,
                data={
                    "worktree_path": worktree_path,
                    "metadata": metadata
                }
            )

            logger.info(f"处理Child会话创建: {project_id}/{task_id}")
            return True

        except Exception as e:
            # 4. 处理异常
            logger.error(f"处理Child会话创建失败: {project_id}/{task_id}, 错误: {e}")
            return False

    async def handle_child_session_started(
        self,
        project_id: str,
        task_id: str,
        reason: Optional[str] = None
    ) -> bool:
        """
        处理Child会话启动事件

        Args:
            project_id: 项目ID
            task_id: 任务ID
            reason: 启动原因

        Returns:
            bool: 是否处理成功
        """
        try:
            # 1. 更新Child状态
            success = await self.resource_manager.update_child_resource(
                project_id=project_id,
                task_id=task_id,
                status=ChildStatus.RUNNING,
                reason=reason
            )

            if not success:
                logger.error(f"更新Child状态失败: {project_id}/{task_id}")
                return False

            # 2. 触发会话事件
            await self._emit_session_event(
                SessionEventType.CHILD_SESSION_STARTED,
                project_id,
                task_id=task_id,
                data={"reason": reason}
            )

            logger.info(f"处理Child会话启动: {project_id}/{task_id}")
            return True

        except Exception as e:
            # 3. 处理异常
            logger.error(f"处理Child会话启动失败: {project_id}/{task_id}, 错误: {e}")
            return False

    async def handle_child_session_completed(
        self,
        project_id: str,
        task_id: str,
        exit_code: int = 0,
        duration_seconds: Optional[float] = None,
        transcript: Optional[str] = None,
        reason: Optional[str] = None
    ) -> bool:
        """
        处理Child会话完成事件

        Args:
            project_id: 项目ID
            task_id: 任务ID
            exit_code: 退出码
            duration_seconds: 运行时长
            transcript: 会话记录
            reason: 完成原因

        Returns:
            bool: 是否处理成功
        """
        try:
            # 1. 更新Child状态
            success = await self.resource_manager.update_child_resource(
                project_id=project_id,
                task_id=task_id,
                status=ChildStatus.COMPLETED,
                reason=reason,
                transcript=transcript,
                exit_code=exit_code,
                duration_seconds=duration_seconds
            )

            if not success:
                logger.error(f"更新Child状态失败: {project_id}/{task_id}")
                return False

            # 2. 触发会话事件
            await self._emit_session_event(
                SessionEventType.CHILD_SESSION_COMPLETED,
                project_id,
                task_id=task_id,
                data={
                    "exit_code": exit_code,
                    "duration_seconds": duration_seconds,
                    "reason": reason,
                    "transcript_length": len(transcript) if transcript else 0
                }
            )

            logger.info(f"处理Child会话完成: {project_id}/{task_id}")
            return True

        except Exception as e:
            # 3. 处理异常
            logger.error(f"处理Child会话完成失败: {project_id}/{task_id}, 错误: {e}")
            return False

    async def handle_child_session_failed(
        self,
        project_id: str,
        task_id: str,
        error_message: str,
        exit_code: int = 1,
        duration_seconds: Optional[float] = None,
        transcript: Optional[str] = None
    ) -> bool:
        """
        处理Child会话失败事件

        Args:
            project_id: 项目ID
            task_id: 任务ID
            error_message: 错误消息
            exit_code: 退出码
            duration_seconds: 运行时长
            transcript: 会话记录

        Returns:
            bool: 是否处理成功
        """
        try:
            # 1. 更新Child状态
            success = await self.resource_manager.update_child_resource(
                project_id=project_id,
                task_id=task_id,
                status=ChildStatus.FAILED,
                reason=error_message,
                transcript=transcript,
                exit_code=exit_code,
                duration_seconds=duration_seconds
            )

            if not success:
                logger.error(f"更新Child状态失败: {project_id}/{task_id}")
                return False

            # 2. 触发会话事件
            await self._emit_session_event(
                SessionEventType.CHILD_SESSION_FAILED,
                project_id,
                task_id=task_id,
                data={
                    "error_message": error_message,
                    "exit_code": exit_code,
                    "duration_seconds": duration_seconds,
                    "transcript_length": len(transcript) if transcript else 0
                }
            )

            logger.info(f"处理Child会话失败: {project_id}/{task_id}")
            return True

        except Exception as e:
            # 3. 处理异常
            logger.error(f"处理Child会话失败事件失败: {project_id}/{task_id}, 错误: {e}")
            return False

    async def handle_child_session_terminated(
        self,
        project_id: str,
        task_id: str,
        reason: str = "手动终止"
    ) -> bool:
        """
        处理Child会话终止事件

        Args:
            project_id: 项目ID
            task_id: 任务ID
            reason: 终止原因

        Returns:
            bool: 是否处理成功
        """
        try:
            # 1. 更新Child状态
            success = await self.resource_manager.update_child_resource(
                project_id=project_id,
                task_id=task_id,
                status=ChildStatus.CANCELLED,
                reason=reason
            )

            if not success:
                logger.error(f"更新Child状态失败: {project_id}/{task_id}")
                return False

            # 2. 触发会话事件
            await self._emit_session_event(
                SessionEventType.CHILD_SESSION_TERMINATED,
                project_id,
                task_id=task_id,
                data={"reason": reason}
            )

            logger.info(f"处理Child会话终止: {project_id}/{task_id}")
            return True

        except Exception as e:
            # 3. 处理异常
            logger.error(f"处理Child会话终止失败: {project_id}/{task_id}, 错误: {e}")
            return False

    async def sync_resources_with_sessions(self) -> Dict[str, Any]:
        """
        同步资源与实际会话状态

        Returns:
            Dict[str, Any]: 同步结果
        """
        try:
            # 1. 获取所有Master资源
            masters = await self.resource_manager.list_master_resources()

            sync_results = {
                "masters_synced": 0,
                "children_synced": 0,
                "errors": []
            }

            # 2. 逐个同步Master资源
            for master in masters:
                try:
                    # 3. 同步Master状态
                    # 这里可以添加实际的tmux会话检测逻辑
                    sync_results["masters_synced"] += 1

                    # 4. 同步Child状态
                    for child in master.children:
                        try:
                            # 这里可以添加实际的Child会话状态检测逻辑
                            sync_results["children_synced"] += 1

                        except Exception as e:
                            sync_results["errors"].append({
                                "type": "child_sync_error",
                                "project_id": master.project_id,
                                "task_id": child.task_id,
                                "error": str(e)
                            })

                except Exception as e:
                    sync_results["errors"].append({
                        "type": "master_sync_error",
                        "project_id": master.project_id,
                        "error": str(e)
                    })

            # 5. 记录同步结果
            logger.info(f"资源同步完成: {sync_results}")

            return sync_results

        except Exception as e:
            # 6. 处理同步异常
            logger.error(f"资源同步失败: {e}")
            return {
                "masters_synced": 0,
                "children_synced": 0,
                "errors": [{"type": "sync_error", "error": str(e)}]
            }

    async def cleanup_expired_sessions(self) -> int:
        """
        清理过期会话

        Returns:
            int: 清理的会话数量
        """
        try:
            # 1. 清理过期的Master资源
            cleanup_count = await self.resource_manager.cleanup_expired_resources(
                timeout_minutes=self.config.max_session_duration_hours * 60
            )

            # 2. 记录清理信息
            logger.info(f"清理过期会话: {cleanup_count} 个")

            return cleanup_count

        except Exception as e:
            # 3. 处理清理异常
            logger.error(f"清理过期会话失败: {e}")
            return 0

    async def add_event_handler(
        self,
        event_type: SessionEventType,
        handler: Callable[[SessionEvent], None]
    ) -> None:
        """
        添加事件处理器

        Args:
            event_type: 事件类型
            handler: 事件处理函数
        """
        # 1. 添加处理器
        if handler not in self.event_handlers[event_type]:
            self.event_handlers[event_type].append(handler)
            logger.info(f"添加事件处理器: {event_type.value}")

    async def remove_event_handler(
        self,
        event_type: SessionEventType,
        handler: Callable[[SessionEvent], None]
    ) -> None:
        """
        移除事件处理器

        Args:
            event_type: 事件类型
            handler: 事件处理函数
        """
        # 1. 移除处理器
        if handler in self.event_handlers[event_type]:
            self.event_handlers[event_type].remove(handler)
            logger.info(f"移除事件处理器: {event_type.value}")

    async def _emit_session_event(
        self,
        event_type: SessionEventType,
        project_id: str,
        task_id: Optional[str] = None,
        session_id: Optional[str] = None,
        session_name: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        触发会话事件

        Args:
            event_type: 事件类型
            project_id: 项目ID
            task_id: 任务ID
            session_id: 会话ID
            session_name: 会话名称
            data: 事件数据
        """
        # 1. 创建事件
        event = SessionEvent(
            event_type=event_type,
            project_id=project_id,
            task_id=task_id,
            session_id=session_id,
            session_name=session_name,
            data=data or {}
        )

        # 2. 触发事件处理器
        if self.config.enable_lifecycle_callbacks:
            for handler in self.event_handlers[event_type]:
                try:
                    handler(event)
                except Exception as e:
                    logger.error(f"事件处理器异常: {event_type.value}, 错误: {e}")

    async def _register_resource_callbacks(self) -> None:
        """注册资源事件回调"""
        # 1. 添加资源事件回调
        await self.resource_manager.add_event_callback(self._handle_resource_event)

    def _handle_resource_event(self, event: ResourceEvent) -> None:
        """
        处理资源事件

        Args:
            event: 资源事件
        """
        try:
            # 1. 记录资源事件
            logger.debug(f"资源事件: {event.event_type.value}, 项目: {event.project_id}")

            # 2. 根据事件类型执行相应处理
            # 这里可以添加资源事件的特殊处理逻辑

        except Exception as e:
            # 3. 处理异常
            logger.error(f"处理资源事件异常: {e}")


# 全局生命周期集成器实例
_lifecycle_integration: Optional[LifecycleIntegration] = None


def get_lifecycle_integration() -> LifecycleIntegration:
    """
    获取全局生命周期集成器实例

    Returns:
        LifecycleIntegration: 生命周期集成器实例
    """
    global _lifecycle_integration

    # 1. 初始化集成器（如果需要）
    if _lifecycle_integration is None:
        config = LifecycleConfig()
        _lifecycle_integration = LifecycleIntegration(config)
        logger.info("初始化全局生命周期集成器")

    return _lifecycle_integration