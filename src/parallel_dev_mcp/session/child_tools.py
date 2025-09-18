# -*- coding: utf-8 -*-
"""
Child会话管理MCP工具

@description 提供Child会话生命周期管理的MCP工具接口
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

# 导入FastMCP实例
from ..mcp_instance import mcp

# 导入Child生命周期管理器
from .child_lifecycle import get_child_lifecycle_manager

# 配置日志系统
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@mcp.tool
def child_session_tool(
    action: str,
    task_id: Optional[str] = None,
    branch_name: Optional[str] = None,
    use_template: Optional[bool] = True
) -> Dict[str, Any]:
    """
    Child会话管理工具

    管理Child会话的完整生命周期，包括创建、终止和查询。
    实现PRD第5节要求的Child职责。

    Args:
        action: 操作类型 (create/terminate/list/status)
        task_id: 任务ID (create和terminate操作必需)
        branch_name: 分支名称 (create操作可选)
        use_template: 是否使用模板文件 (create操作可选)

    Returns:
        Dict[str, Any]: 操作结果
    """
    try:
        # 1. 参数验证
        if action not in ['create', 'terminate', 'list', 'status']:
            return {
                "success": False,
                "error": "无效的操作类型，必须是: create, terminate, list, status"
            }

        # 2. 获取Child生命周期管理器
        manager = get_child_lifecycle_manager()

        # 3. 执行对应操作
        if action == 'create':
            if not task_id:
                return {
                    "success": False,
                    "error": "create操作需要提供task_id参数"
                }
            return manager.create_child_session(task_id, branch_name, use_template)

        elif action == 'terminate':
            if not task_id:
                return {
                    "success": False,
                    "error": "terminate操作需要提供task_id参数"
                }
            return manager.terminate_child_session(task_id)

        elif action == 'list':
            return manager.list_child_sessions()

        elif action == 'status':
            # 获取特定任务的Child会话状态
            if task_id:
                sessions = manager.list_child_sessions()
                if sessions.get("success"):
                    for session in sessions.get("child_sessions", []):
                        if session["task_id"] == task_id:
                            return {
                                "success": True,
                                "session": session,
                                "exists": True,
                                "timestamp": datetime.now().isoformat()
                            }
                    return {
                        "success": True,
                        "exists": False,
                        "message": f"任务 {task_id} 没有活动的Child会话",
                        "timestamp": datetime.now().isoformat()
                    }
                return sessions
            else:
                # 返回所有Child会话的汇总状态
                sessions = manager.list_child_sessions()
                if sessions.get("success"):
                    return {
                        "success": True,
                        "total_sessions": sessions.get("count", 0),
                        "sessions": sessions.get("child_sessions", []),
                        "timestamp": datetime.now().isoformat()
                    }
                return sessions

    except Exception as e:
        # 4. 异常处理
        logger.error(f"Child会话工具异常: {e}")
        return {
            "success": False,
            "error": f"操作失败: {str(e)}"
        }


def _batch_child_operations_internal(
    action: str,
    task_ids: str,
    branch_prefix: Optional[str] = "task/"
) -> Dict[str, Any]:
    """
    批量Child会话操作内部函数

    内部使用，不暴露为MCP工具。
    支持批量创建或终止多个Child会话。

    Args:
        action: 操作类型 (create_batch/terminate_batch)
        task_ids: 任务ID列表，逗号分隔 (如 "101,102,103")
        branch_prefix: 分支前缀 (默认 "task/")

    Returns:
        Dict[str, Any]: 批量操作结果
    """
    try:
        # 1. 参数验证
        if action not in ['create_batch', 'terminate_batch']:
            return {
                "success": False,
                "error": "无效的操作类型，必须是: create_batch, terminate_batch"
            }

        if not task_ids:
            return {
                "success": False,
                "error": "必须提供task_ids参数"
            }

        # 2. 解析任务ID列表
        task_list = [tid.strip() for tid in task_ids.split(',') if tid.strip()]
        if not task_list:
            return {
                "success": False,
                "error": "task_ids列表为空"
            }

        # 3. 获取管理器
        manager = get_child_lifecycle_manager()

        # 4. 执行批量操作
        results = []
        success_count = 0
        failed_count = 0

        for task_id in task_list:
            if action == 'create_batch':
                branch_name = f"{branch_prefix}{task_id}"
                result = manager.create_child_session(task_id, branch_name)
            else:  # terminate_batch
                result = manager.terminate_child_session(task_id)

            results.append({
                "task_id": task_id,
                "success": result.get("success"),
                "message": result.get("message") or result.get("error")
            })

            if result.get("success"):
                success_count += 1
            else:
                failed_count += 1

        # 5. 返回批量操作结果
        return {
            "success": failed_count == 0,
            "action": action,
            "total_tasks": len(task_list),
            "success_count": success_count,
            "failed_count": failed_count,
            "results": results,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        # 6. 异常处理
        logger.error(f"批量Child操作工具异常: {e}")
        return {
            "success": False,
            "error": f"批量操作失败: {str(e)}"
        }


def _child_worktree_internal(
    action: str,
    task_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Child Worktree管理内部函数

    内部使用，不暴露为MCP工具。
    专门管理Child会话的Git worktree。

    Args:
        action: 操作类型 (list/cleanup/verify)
        task_id: 任务ID (cleanup操作必需)

    Returns:
        Dict[str, Any]: 操作结果
    """
    try:
        # 1. 参数验证
        if action not in ['list', 'cleanup', 'verify']:
            return {
                "success": False,
                "error": "无效的操作类型，必须是: list, cleanup, verify"
            }

        # 2. 执行操作
        import subprocess
        from pathlib import Path

        project_root = Path.cwd()
        worktree_dir = project_root / "worktree"

        if action == 'list':
            # 列出所有worktree
            result = subprocess.run(
                ['git', 'worktree', 'list'],
                cwd=str(project_root),
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                worktrees = []
                for line in result.stdout.strip().split('\n'):
                    if 'worktree/' in line:
                        parts = line.split()
                        if parts:
                            path = Path(parts[0])
                            task_id = path.name
                            worktrees.append({
                                "task_id": task_id,
                                "path": str(path),
                                "branch": parts[2] if len(parts) > 2 else "unknown"
                            })

                return {
                    "success": True,
                    "worktrees": worktrees,
                    "count": len(worktrees),
                    "timestamp": datetime.now().isoformat()
                }

        elif action == 'cleanup':
            if not task_id:
                return {
                    "success": False,
                    "error": "cleanup操作需要提供task_id参数"
                }

            worktree_path = worktree_dir / task_id
            if worktree_path.exists():
                result = subprocess.run(
                    ['git', 'worktree', 'remove', str(worktree_path), '--force'],
                    cwd=str(project_root),
                    capture_output=True,
                    text=True,
                    timeout=10
                )

                if result.returncode == 0:
                    return {
                        "success": True,
                        "message": f"Worktree {task_id} 清理成功",
                        "path": str(worktree_path),
                        "timestamp": datetime.now().isoformat()
                    }
                else:
                    return {
                        "success": False,
                        "error": f"清理失败: {result.stderr}"
                    }
            else:
                return {
                    "success": True,
                    "message": f"Worktree {task_id} 不存在",
                    "timestamp": datetime.now().isoformat()
                }

        elif action == 'verify':
            # 验证worktree状态
            result = subprocess.run(
                ['git', 'worktree', 'list'],
                cwd=str(project_root),
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                issues = []
                # 检查是否有断开的worktree
                if 'prunable' in result.stdout:
                    issues.append("存在可清理的worktree")

                return {
                    "success": True,
                    "healthy": len(issues) == 0,
                    "issues": issues,
                    "timestamp": datetime.now().isoformat()
                }

        return {
            "success": False,
            "error": "未知的操作"
        }

    except Exception as e:
        # 3. 异常处理
        logger.error(f"Child Worktree工具异常: {e}")
        return {
            "success": False,
            "error": f"操作失败: {str(e)}"
        }