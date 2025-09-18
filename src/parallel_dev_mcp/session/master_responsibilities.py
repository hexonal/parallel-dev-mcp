# -*- coding: utf-8 -*-
"""
Master职责集成管理器和MCP工具

@description 集成所有Master职责功能，提供统一的MCP工具接口
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

# 导入FastMCP实例
from ..mcp_instance import mcp

# 导入所有Master职责管理器
from .session_id_manager import get_session_id_manager, auto_ensure_master_session_id
from .git_resource_manager import get_git_resource_manager, auto_sync_git_to_resources
from .worktree_auto_manager import get_worktree_auto_manager, auto_ensure_worktree_directory
from .child_session_monitor import get_child_session_monitor, auto_start_child_monitoring

# 配置日志系统
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@mcp.tool
def master_session_id_tool(
    action: str,
    session_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Master会话ID管理工具

    管理session_id.txt文件，实现PRD要求的Master会话标识。
    仅Master节点可以写入，Child节点禁止写入。

    Args:
        action: 操作类型 (write/read/clear/status/ensure)
        session_id: 会话ID（仅write操作需要，可选自动生成）

    Returns:
        Dict[str, Any]: 操作结果
    """
    try:
        # 1. 参数验证
        if action not in ['write', 'read', 'clear', 'status', 'ensure']:
            return {
                "success": False,
                "error": "无效的操作类型，必须是: write, read, clear, status, ensure"
            }

        # 2. 获取Session ID管理器
        manager = get_session_id_manager()

        # 3. 执行对应操作
        if action == 'write':
            return manager.write_master_session_id(session_id)
        elif action == 'read':
            return manager.read_session_id()
        elif action == 'clear':
            return manager.clear_session_id()
        elif action == 'status':
            return manager.get_session_status()
        elif action == 'ensure':
            return manager.ensure_master_session_id()

    except Exception as e:
        # 4. 异常处理
        logger.error(f"Master会话ID工具异常: {e}")
        return {
            "success": False,
            "error": f"操作失败: {str(e)}"
        }


def _git_resource_internal(
    action: str
) -> Dict[str, Any]:
    """
    Git资源管理内部函数

    内部使用，不暴露为MCP工具。系统自动收集和持久化Git信息。

    将Git信息（remote + branch）落盘到MCP资源，实现PRD要求的Git状态持久化。

    Args:
        action: 操作类型 (sync/status/auto_sync)

    Returns:
        Dict[str, Any]: 操作结果
    """
    try:
        # 1. 参数验证
        if action not in ['sync', 'status', 'auto_sync']:
            return {
                "success": False,
                "error": "无效的操作类型，必须是: sync, status, auto_sync"
            }

        # 2. 获取Git资源管理器
        manager = get_git_resource_manager()

        # 3. 执行对应操作
        if action == 'sync':
            return manager.sync_git_info_to_resources()
        elif action == 'status':
            return manager.get_git_resource_status()
        elif action == 'auto_sync':
            return manager.auto_sync_git_info()

    except Exception as e:
        # 4. 异常处理
        logger.error(f"Git资源工具异常: {e}")
        return {
            "success": False,
            "error": f"操作失败: {str(e)}"
        }


def _worktree_management_internal(
    action: str,
    task_id: Optional[str] = None,
    branch_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Worktree管理内部函数

    内部使用，不暴露为MCP工具。系统自动管理Git worktree。
    自动创建和管理./worktree/目录，支持Child会话的Git worktree操作。

    Args:
        action: 操作类型 (ensure/create_child/list/cleanup/status/auto_ensure)
        task_id: 任务ID（create_child和cleanup操作需要）
        branch_name: 分支名称（create_child操作可选）

    Returns:
        Dict[str, Any]: 操作结果
    """
    try:
        # 1. 参数验证
        if action not in ['ensure', 'create_child', 'list', 'cleanup', 'status', 'auto_ensure']:
            return {
                "success": False,
                "error": "无效的操作类型，必须是: ensure, create_child, list, cleanup, status, auto_ensure"
            }

        # 2. 获取Worktree管理器
        manager = get_worktree_auto_manager()

        # 3. 执行对应操作
        if action == 'ensure':
            return manager.ensure_worktree_directory()
        elif action == 'create_child':
            if not task_id:
                return {
                    "success": False,
                    "error": "create_child操作需要提供task_id参数"
                }
            return manager.create_child_worktree(task_id, branch_name)
        elif action == 'list':
            return manager.list_child_worktrees()
        elif action == 'cleanup':
            if not task_id:
                return {
                    "success": False,
                    "error": "cleanup操作需要提供task_id参数"
                }
            return manager.cleanup_child_worktree(task_id)
        elif action == 'status':
            return manager.get_worktree_status()
        elif action == 'auto_ensure':
            return manager.auto_ensure_worktree_directory()

    except Exception as e:
        # 4. 异常处理
        logger.error(f"Worktree管理工具异常: {e}")
        return {
            "success": False,
            "error": f"操作失败: {str(e)}"
        }


@mcp.tool
def child_session_monitoring_tool(
    action: str
) -> Dict[str, Any]:
    """
    Child会话监控工具

    实现真正的5秒子会话清单刷新，实时跟踪所有Child会话状态。

    Args:
        action: 操作类型 (start/stop/status/refresh/auto_start)

    Returns:
        Dict[str, Any]: 操作结果
    """
    try:
        # 1. 参数验证
        if action not in ['start', 'stop', 'status', 'refresh', 'auto_start']:
            return {
                "success": False,
                "error": "无效的操作类型，必须是: start, stop, status, refresh, auto_start"
            }

        # 2. 获取Child会话监控器
        monitor = get_child_session_monitor()

        # 3. 执行对应操作
        if action == 'start':
            return monitor.start_monitoring()
        elif action == 'stop':
            return monitor.stop_monitoring()
        elif action == 'status':
            return monitor.get_monitoring_status()
        elif action == 'refresh':
            return monitor.force_refresh_now()
        elif action == 'auto_start':
            return auto_start_child_monitoring()

    except Exception as e:
        # 4. 异常处理
        logger.error(f"Child会话监控工具异常: {e}")
        return {
            "success": False,
            "error": f"操作失败: {str(e)}"
        }


def _master_responsibilities_status_internal() -> Dict[str, Any]:
    """
    Master职责状态检查内部函数

    内部使用，不暴露为MCP工具。
    检查所有Master职责的完成状态，提供综合的状态报告。

    Returns:
        Dict[str, Any]: 状态报告
    """
    try:
        # 1. 检查Master权限
        from .master_detector import is_master_node, get_master_session_info
        master_info = get_master_session_info()

        if not master_info.get("is_master", False):
            return {
                "success": True,
                "is_master_node": False,
                "message": "当前不是Master节点，Master职责不适用",
                "master_info": master_info
            }

        # 2. 检查各项Master职责状态
        responsibilities_status = {}

        # 2.1 检查session_id.txt状态
        session_manager = get_session_id_manager()
        session_status = session_manager.get_session_status()
        responsibilities_status["session_id_management"] = {
            "required": "绑定 session_id.txt（仅 Master 写）",
            "status": "completed" if session_status.get("session_id") else "pending",
            "details": session_status
        }

        # 2.2 检查Git信息落盘状态
        git_manager = get_git_resource_manager()
        git_status = git_manager.get_git_resource_status()
        responsibilities_status["git_info_persistence"] = {
            "required": "落盘 Git 信息（remote + branch）到 @mcp.resource",
            "status": "completed" if git_status.get("is_synced") else "pending",
            "details": git_status
        }

        # 2.3 检查worktree目录状态
        worktree_manager = get_worktree_auto_manager()
        worktree_status = worktree_manager.get_worktree_status()
        responsibilities_status["worktree_creation"] = {
            "required": "自动创建 ./worktree/",
            "status": "completed" if worktree_status.get("worktree_directory_exists") else "pending",
            "details": worktree_status
        }

        # 2.4 检查子会话监控状态
        child_monitor = get_child_session_monitor()
        monitor_status = child_monitor.get_monitoring_status()
        responsibilities_status["child_session_monitoring"] = {
            "required": "每 5s 刷新子会话清单",
            "status": "running" if monitor_status.get("is_monitoring") else "stopped",
            "details": monitor_status
        }

        # 2.5 检查Web服务状态（从生命周期管理器）
        from ..web.lifecycle_manager import get_lifecycle_manager
        lifecycle_manager = get_lifecycle_manager()
        lifecycle_status = lifecycle_manager.get_lifecycle_status()
        responsibilities_status["flask_web_service"] = {
            "required": "启动 Flask（绑定 WEB_PORT）",
            "status": "running" if lifecycle_status.get("status", {}).get("web_server_active") else "stopped",
            "details": lifecycle_status
        }

        # 3. 计算完成度
        completed_count = len([r for r in responsibilities_status.values()
                             if r["status"] in ["completed", "running"]])
        total_count = len(responsibilities_status)
        completion_percentage = (completed_count / total_count) * 100

        # 4. 返回综合状态
        return {
            "success": True,
            "is_master_node": True,
            "master_info": master_info,
            "responsibilities_status": responsibilities_status,
            "completion_summary": {
                "completed_count": completed_count,
                "total_count": total_count,
                "completion_percentage": completion_percentage,
                "overall_status": "healthy" if completion_percentage >= 80 else "needs_attention"
            },
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        # 5. 异常处理
        logger.error(f"Master职责状态检查异常: {e}")
        return {
            "success": False,
            "error": f"状态检查失败: {str(e)}"
        }


def initialize_all_master_responsibilities() -> Dict[str, Any]:
    """
    初始化所有Master职责

    在系统启动时自动调用，确保所有Master职责正常运行。

    Returns:
        Dict[str, Any]: 初始化结果
    """
    try:
        # 1. 检查是否为Master节点
        from .master_detector import is_master_node
        if not is_master_node():
            return {
                "success": True,
                "message": "非Master节点，跳过Master职责初始化",
                "action": "skipped"
            }

        # 2. 初始化各项Master职责
        initialization_results = {}

        # 2.1 确保session_id.txt
        session_result = auto_ensure_master_session_id()
        initialization_results["session_id"] = session_result

        # 2.2 同步Git信息到资源
        git_result = auto_sync_git_to_resources()
        initialization_results["git_sync"] = git_result

        # 2.3 确保worktree目录
        worktree_result = auto_ensure_worktree_directory()
        initialization_results["worktree"] = worktree_result

        # 2.4 启动子会话监控
        monitor_result = auto_start_child_monitoring()
        initialization_results["child_monitoring"] = monitor_result

        # 3. 统计初始化结果
        success_count = len([r for r in initialization_results.values() if r.get("success")])
        total_count = len(initialization_results)

        # 4. 记录初始化结果
        if success_count == total_count:
            logger.info("所有Master职责初始化成功")
            overall_status = "success"
        else:
            logger.warning(f"Master职责初始化部分失败: {success_count}/{total_count}")
            overall_status = "partial_success"

        return {
            "success": True,
            "message": f"Master职责初始化完成: {success_count}/{total_count}",
            "overall_status": overall_status,
            "initialization_results": initialization_results,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        # 5. 异常处理
        logger.error(f"初始化Master职责异常: {e}")
        return {
            "success": False,
            "error": f"初始化失败: {str(e)}"
        }