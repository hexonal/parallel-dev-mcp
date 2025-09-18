# -*- coding: utf-8 -*-
"""
MCP资源集成

@description 使用FastMCP的@mcp.resource装饰器注册Master和Child资源，提供动态资源获取和更新
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from .resource_manager import ResourceManager, ResourceConfig
from .models import ChildStatus, MasterStatus

# 配置日志系统
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 获取FastMCP实例
from ..mcp_instance import mcp

# 全局资源管理器实例
_resource_manager: Optional[ResourceManager] = None


def get_resource_manager() -> ResourceManager:
    """
    获取全局资源管理器实例

    Returns:
        ResourceManager: 资源管理器实例
    """
    global _resource_manager

    # 1. 初始化资源管理器（如果需要）
    if _resource_manager is None:
        config = ResourceConfig(
            auto_refresh_enabled=True,
            auto_refresh_interval_seconds=5,
            max_children_per_master=50
        )
        _resource_manager = ResourceManager(config)
        logger.info("初始化全局资源管理器")

    return _resource_manager


def _safe_async_call(coroutine) -> Any:
    """
    安全调用异步方法

    Args:
        coroutine: 协程对象

    Returns:
        Any: 执行结果
    """
    try:
        # 1. 获取事件循环
        loop = asyncio.get_event_loop()

        # 2. 检查循环是否运行中
        if loop.is_running():
            # 在运行中的循环中使用run_coroutine_threadsafe
            future = asyncio.run_coroutine_threadsafe(coroutine, loop)
            return future.result(timeout=5.0)  # 5秒超时
        else:
            # 没有运行的循环，直接运行
            return loop.run_until_complete(coroutine)

    except Exception as e:
        logger.error(f"异步调用失败: {e}")
        return None


@mcp.resource("resource://parallel-dev-mcp/masters")
def masters_resource() -> Dict[str, Any]:
    """
    所有Master资源列表

    提供系统中所有Master会话的完整信息，包括会话状态、仓库信息、子会话统计等。
    该资源自动更新，当Master资源发生变化时会反映最新状态。

    Returns:
        Dict[str, Any]: Master资源列表，包含以下字段：
            - masters: Master资源列表
            - total_count: Master总数
            - active_count: 活跃Master数量
            - last_updated: 最后更新时间
            - resource_version: 资源版本
    """
    try:
        # 1. 获取资源管理器
        manager = get_resource_manager()

        # 2. 获取所有Master资源
        masters = _safe_async_call(manager.list_master_resources())
        if masters is None:
            masters = []

        # 3. 序列化Master资源
        masters_data = []
        active_count = 0

        for master in masters:
            master_dict = master.model_dump()
            masters_data.append(master_dict)

            # 统计活跃Master
            if master.status == MasterStatus.ACTIVE:
                active_count += 1

        # 4. 构建资源内容
        resource_content = {
            "masters": masters_data,
            "total_count": len(masters_data),
            "active_count": active_count,
            "last_updated": datetime.now().isoformat(),
            "resource_version": "1.0",
            "resource_type": "master_list"
        }

        # 5. 记录资源访问
        logger.debug(f"Master资源列表被访问: {len(masters_data)} 个资源")

        return resource_content

    except Exception as e:
        # 6. 处理异常
        logger.error(f"获取Master资源列表失败: {e}")
        return {
            "masters": [],
            "total_count": 0,
            "active_count": 0,
            "last_updated": datetime.now().isoformat(),
            "error": str(e),
            "resource_version": "1.0",
            "resource_type": "master_list"
        }


@mcp.resource("resource://parallel-dev-mcp/master/{project_id}")
def master_resource(project_id: str) -> Dict[str, Any]:
    """
    单个Master资源

    提供指定项目的Master会话详细信息，包括所有子会话状态、仓库信息等。

    Args:
        project_id: 项目ID

    Returns:
        Dict[str, Any]: Master资源详细信息
    """
    try:
        # 1. 获取资源管理器
        manager = get_resource_manager()

        # 2. 获取指定Master资源
        master = _safe_async_call(manager.get_master_resource(project_id))

        if master is None:
            return {
                "project_id": project_id,
                "exists": False,
                "error": "Master资源不存在",
                "last_updated": datetime.now().isoformat(),
                "resource_version": "1.0",
                "resource_type": "master_detail"
            }

        # 3. 序列化Master资源
        master_dict = master.model_dump()

        # 4. 添加统计信息
        master_dict.update({
            "exists": True,
            "children_count": len(master.children),
            "active_children_count": master.active_children,
            "last_updated": datetime.now().isoformat(),
            "resource_version": "1.0",
            "resource_type": "master_detail"
        })

        # 5. 记录资源访问
        logger.debug(f"Master资源被访问: {project_id}")

        return master_dict

    except Exception as e:
        # 6. 处理异常
        logger.error(f"获取Master资源失败: {project_id}, 错误: {e}")
        return {
            "project_id": project_id,
            "exists": False,
            "error": str(e),
            "last_updated": datetime.now().isoformat(),
            "resource_version": "1.0",
            "resource_type": "master_detail"
        }


@mcp.resource("resource://parallel-dev-mcp/children")
def children_resource() -> Dict[str, Any]:
    """
    所有Child资源列表

    提供系统中所有Child会话的汇总信息，按项目分组显示。

    Returns:
        Dict[str, Any]: Child资源汇总信息
    """
    try:
        # 1. 获取资源管理器
        manager = get_resource_manager()

        # 2. 获取所有Master资源
        masters = _safe_async_call(manager.list_master_resources())
        if masters is None:
            masters = []

        # 3. 收集所有Child资源
        all_children = []
        children_by_project = {}
        total_children = 0
        status_counts = {}

        for master in masters:
            project_children = []
            for child in master.children:
                child_dict = child.model_dump()
                child_dict["project_id"] = master.project_id
                project_children.append(child_dict)
                all_children.append(child_dict)

                # 统计状态
                status = child.status.value
                status_counts[status] = status_counts.get(status, 0) + 1

            children_by_project[master.project_id] = {
                "project_name": master.project_name,
                "children": project_children,
                "count": len(project_children)
            }
            total_children += len(project_children)

        # 4. 构建资源内容
        resource_content = {
            "children_by_project": children_by_project,
            "all_children": all_children,
            "total_count": total_children,
            "status_counts": status_counts,
            "projects_count": len(children_by_project),
            "last_updated": datetime.now().isoformat(),
            "resource_version": "1.0",
            "resource_type": "children_list"
        }

        # 5. 记录资源访问
        logger.debug(f"Child资源列表被访问: {total_children} 个资源")

        return resource_content

    except Exception as e:
        # 6. 处理异常
        logger.error(f"获取Child资源列表失败: {e}")
        return {
            "children_by_project": {},
            "all_children": [],
            "total_count": 0,
            "status_counts": {},
            "projects_count": 0,
            "error": str(e),
            "last_updated": datetime.now().isoformat(),
            "resource_version": "1.0",
            "resource_type": "children_list"
        }


@mcp.resource("resource://parallel-dev-mcp/child/{project_id}/{task_id}")
def child_resource(project_id: str, task_id: str) -> Dict[str, Any]:
    """
    单个Child资源

    提供指定Child会话的详细信息，包括执行状态、会话记录等。

    Args:
        project_id: 项目ID
        task_id: 任务ID

    Returns:
        Dict[str, Any]: Child资源详细信息
    """
    try:
        # 1. 获取资源管理器
        manager = get_resource_manager()

        # 2. 获取指定Child资源
        child = _safe_async_call(manager.get_child_resource(project_id, task_id))

        if child is None:
            return {
                "project_id": project_id,
                "task_id": task_id,
                "exists": False,
                "error": "Child资源不存在",
                "last_updated": datetime.now().isoformat(),
                "resource_version": "1.0",
                "resource_type": "child_detail"
            }

        # 3. 序列化Child资源
        child_dict = child.model_dump()

        # 4. 添加附加信息
        child_dict.update({
            "exists": True,
            "transcript_length": len(child.transcript) if child.transcript else 0,
            "is_active": child.status in [ChildStatus.RUNNING, ChildStatus.PENDING],
            "last_updated": datetime.now().isoformat(),
            "resource_version": "1.0",
            "resource_type": "child_detail"
        })

        # 5. 记录资源访问
        logger.debug(f"Child资源被访问: {project_id}/{task_id}")

        return child_dict

    except Exception as e:
        # 6. 处理异常
        logger.error(f"获取Child资源失败: {project_id}/{task_id}, 错误: {e}")
        return {
            "project_id": project_id,
            "task_id": task_id,
            "exists": False,
            "error": str(e),
            "last_updated": datetime.now().isoformat(),
            "resource_version": "1.0",
            "resource_type": "child_detail"
        }


@mcp.resource("resource://parallel-dev-mcp/statistics")
def statistics_resource() -> Dict[str, Any]:
    """
    资源统计信息

    提供系统整体的资源统计和健康状态信息。

    Returns:
        Dict[str, Any]: 系统统计信息
    """
    try:
        # 1. 获取资源管理器
        manager = get_resource_manager()

        # 2. 获取统计信息
        stats = _safe_async_call(manager.get_resource_statistics())
        if stats is None:
            stats = {}

        # 3. 添加时间戳和版本信息
        stats.update({
            "last_updated": datetime.now().isoformat(),
            "resource_version": "1.0",
            "resource_type": "statistics",
            "manager_status": "active" if _resource_manager is not None else "inactive"
        })

        # 4. 记录资源访问
        logger.debug("统计信息资源被访问")

        return stats

    except Exception as e:
        # 5. 处理异常
        logger.error(f"获取统计信息失败: {e}")
        return {
            "error": str(e),
            "last_updated": datetime.now().isoformat(),
            "resource_version": "1.0",
            "resource_type": "statistics",
            "manager_status": "error"
        }


def initialize_mcp_resources() -> None:
    """
    初始化MCP资源系统

    创建全局资源管理器实例并启动必要的后台任务
    """
    try:
        # 1. 获取资源管理器（这会初始化全局实例）
        manager = get_resource_manager()

        # 2. 记录初始化信息
        logger.info("MCP资源系统初始化完成")

    except Exception as e:
        # 3. 处理初始化异常
        logger.error(f"MCP资源系统初始化失败: {e}")


def cleanup_mcp_resources() -> None:
    """
    清理MCP资源系统

    停止后台任务并释放资源
    """
    global _resource_manager

    try:
        # 1. 停止资源管理器
        if _resource_manager is not None:
            # 停止自动刷新任务
            _safe_async_call(_resource_manager._stop_auto_refresh())
            _resource_manager = None

        # 2. 记录清理信息
        logger.info("MCP资源系统清理完成")

    except Exception as e:
        # 3. 处理清理异常
        logger.error(f"MCP资源系统清理失败: {e}")


# 在模块加载时初始化资源系统
initialize_mcp_resources()