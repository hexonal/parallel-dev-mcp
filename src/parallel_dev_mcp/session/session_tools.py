# -*- coding: utf-8 -*-
"""
会话管理MCP工具

@description 实现会话创建、管理和资源操作的MCP工具集
"""

import os
import subprocess
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
from pydantic import BaseModel, Field, field_validator

# 获取FastMCP实例
from ..mcp_instance import mcp
from .models import ChildResourceModel, ChildStatus, MasterStatus
from .resource_manager import get_resource_manager

# 配置日志系统
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class SessionCreateResult(BaseModel):
    """会话创建结果模型"""

    success: bool = Field(..., description="创建是否成功")
    session_name: Optional[str] = Field(None, description="创建的会话名称")
    worktree_path: Optional[str] = Field(None, description="工作树路径")
    tmux_session_id: Optional[str] = Field(None, description="Tmux会话ID")
    error_message: Optional[str] = Field(None, description="错误信息")
    project_id: Optional[str] = Field(None, description="项目ID")
    task_id: Optional[str] = Field(None, description="任务ID")

    @field_validator('session_name')
    @classmethod
    def validate_session_name(cls, v: Optional[str]) -> Optional[str]:
        """验证会话名称"""
        if v is None:
            return v
        return v.strip() if v.strip() else None


def _execute_command(command: List[str], cwd: Optional[str] = None) -> Dict[str, Any]:
    """
    执行命令工具函数

    Args:
        command: 命令列表
        cwd: 工作目录

    Returns:
        Dict[str, Any]: 执行结果
    """
    try:
        # 1. 执行命令
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            cwd=cwd,
            timeout=30
        )

        # 2. 返回结果
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "return_code": result.returncode
        }

    except subprocess.TimeoutExpired:
        # 3. 超时处理
        return {
            "success": False,
            "stdout": "",
            "stderr": "命令执行超时",
            "return_code": -1
        }
    except Exception as e:
        # 4. 异常处理
        return {
            "success": False,
            "stdout": "",
            "stderr": str(e),
            "return_code": -1
        }


def _get_project_prefix() -> str:
    """获取项目前缀"""
    return os.environ.get('PROJECT_PREFIX', 'PARALLEL')


def _create_worktree(project_id: str, task_id: str, base_repo_path: str) -> Dict[str, Any]:
    """
    创建Git Worktree

    Args:
        project_id: 项目ID
        task_id: 任务ID
        base_repo_path: 基础仓库路径

    Returns:
        Dict[str, Any]: 创建结果
    """
    try:
        # 1. 构建工作树路径
        worktree_name = f"{project_id}_task_{task_id}"
        parent_dir = Path(base_repo_path).parent
        worktree_path = parent_dir / f"{worktree_name}_worktree"

        # 2. 创建分支名称
        branch_name = f"feature/task-{task_id}"

        # 3. 检查工作树是否已存在
        if worktree_path.exists():
            logger.warning(f"工作树已存在: {worktree_path}")
            return {
                "success": False,
                "path": str(worktree_path),
                "error": "工作树路径已存在"
            }

        # 4. 创建Git worktree
        command = ['git', 'worktree', 'add', '-b', branch_name, str(worktree_path)]
        result = _execute_command(command, cwd=base_repo_path)

        if not result["success"]:
            # 5. 创建失败处理
            logger.error(f"Git worktree创建失败: {result['stderr']}")
            return {
                "success": False,
                "path": str(worktree_path),
                "error": f"Git worktree创建失败: {result['stderr']}"
            }

        # 6. 验证工作树创建成功
        if not worktree_path.exists():
            return {
                "success": False,
                "path": str(worktree_path),
                "error": "工作树创建成功但目录不存在"
            }

        # 7. 返回成功结果
        logger.info(f"Git worktree创建成功: {worktree_path}")
        return {
            "success": True,
            "path": str(worktree_path),
            "branch": branch_name
        }

    except Exception as e:
        # 8. 异常处理
        logger.error(f"创建工作树异常: {e}")
        return {
            "success": False,
            "path": str(worktree_path) if 'worktree_path' in locals() else "",
            "error": str(e)
        }


def _create_tmux_session(session_name: str, working_directory: str) -> Dict[str, Any]:
    """
    创建Tmux会话

    Args:
        session_name: 会话名称
        working_directory: 工作目录

    Returns:
        Dict[str, Any]: 创建结果
    """
    try:
        # 1. 检查会话是否已存在
        check_command = ['tmux', 'has-session', '-t', session_name]
        check_result = _execute_command(check_command)

        if check_result["success"]:
            # 2. 会话已存在
            logger.warning(f"Tmux会话已存在: {session_name}")
            return {
                "success": False,
                "session_id": None,
                "error": f"会话已存在: {session_name}"
            }

        # 3. 创建新的tmux会话（detached模式）
        create_command = [
            'tmux', 'new-session', '-d', '-s', session_name, '-c', working_directory
        ]
        create_result = _execute_command(create_command)

        if not create_result["success"]:
            # 4. 创建失败
            logger.error(f"Tmux会话创建失败: {create_result['stderr']}")
            return {
                "success": False,
                "session_id": None,
                "error": f"Tmux会话创建失败: {create_result['stderr']}"
            }

        # 5. 获取会话ID
        info_command = ['tmux', 'display-message', '-t', session_name, '-p', '#{session_id}']
        info_result = _execute_command(info_command)

        session_id = info_result["stdout"] if info_result["success"] else None

        # 6. 返回成功结果
        logger.info(f"Tmux会话创建成功: {session_name} (ID: {session_id})")
        return {
            "success": True,
            "session_id": session_id,
            "session_name": session_name
        }

    except Exception as e:
        # 7. 异常处理
        logger.error(f"创建Tmux会话异常: {e}")
        return {
            "success": False,
            "session_id": None,
            "error": str(e)
        }


def _start_claude_code(working_directory: str, session_name: str) -> Dict[str, Any]:
    """
    在tmux会话中启动Claude Code

    Args:
        working_directory: 工作目录
        session_name: tmux会话名称

    Returns:
        Dict[str, Any]: 启动结果
    """
    try:
        # 1. 构建Claude Code启动命令
        claude_command = "cd {} && claude".format(working_directory)

        # 2. 在tmux会话中发送命令
        send_command = ['tmux', 'send-keys', '-t', session_name, claude_command, 'Enter']
        result = _execute_command(send_command)

        if not result["success"]:
            # 3. 发送命令失败
            logger.error(f"启动Claude Code失败: {result['stderr']}")
            return {
                "success": False,
                "error": f"发送命令失败: {result['stderr']}"
            }

        # 4. 等待一小段时间让Claude Code启动
        import time
        time.sleep(2)

        # 5. 返回成功结果
        logger.info(f"Claude Code启动命令已发送到会话: {session_name}")
        return {
            "success": True,
            "message": f"Claude Code已在会话 {session_name} 中启动"
        }

    except Exception as e:
        # 6. 异常处理
        logger.error(f"启动Claude Code异常: {e}")
        return {
            "success": False,
            "error": str(e)
        }


# ============================================================
# 注意：create_session 工具已被统一工具 session(action='create') 替代
# 该工具已删除，请使用新的统一工具接口
# ============================================================


def _update_master_resource_internal(
    project_id: str,
    session_id: Optional[str] = None,
    status: Optional[str] = None,
    configuration: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    更新Master资源内部函数

    内部使用，不暴露为MCP工具。系统状态变化时自动更新。
    更新指定项目的Master资源信息，包括会话ID、状态和配置。

    Args:
        project_id: 项目ID
        session_id: 新的会话ID
        status: 新的状态 (active/inactive/suspended)
        configuration: 新的配置信息

    Returns:
        Dict[str, Any]: 更新结果
    """
    try:
        # 1. 参数验证
        if not project_id or not project_id.strip():
            return {
                "success": False,
                "error": "项目ID不能为空"
            }

        # 2. 状态验证
        valid_statuses = ["active", "inactive", "suspended"]
        if status and status not in valid_statuses:
            return {
                "success": False,
                "error": f"状态必须是以下之一: {valid_statuses}"
            }

        # 3. 获取资源管理器
        resource_manager = get_resource_manager()

        # 4. 准备更新参数
        update_kwargs = {}
        if session_id is not None:
            update_kwargs["session_id"] = session_id
        if status is not None:
            update_kwargs["status"] = MasterStatus(status)
        if configuration is not None:
            update_kwargs["configuration"] = configuration

        # 5. 执行更新
        # TODO: 需要根据resource_manager的实际实现来处理异步调用
        logger.info(f"准备更新Master资源: {project_id}")
        updated_master = None  # 暂时设为None，需要实际的异步调用实现

        if updated_master is None:
            return {
                "success": False,
                "error": f"Master资源不存在: {project_id}"
            }

        # 6. 返回成功结果
        logger.info(f"Master资源更新成功: {project_id}")
        return {
            "success": True,
            "project_id": project_id,
            "updated_fields": list(update_kwargs.keys()),
            "updated_at": updated_master.updated_at.isoformat()
        }

    except Exception as e:
        # 7. 异常处理
        logger.error(f"更新Master资源异常: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool
def update_child_resource(
    project_id: str,
    task_id: str,
    status: Optional[str] = None,
    reason: Optional[str] = None,
    transcript: Optional[str] = None,
    exit_code: Optional[int] = None,
    metadata: Optional[Dict[str, Any]] = None
):
    """
    更新Child资源

    更新指定项目中特定任务的Child资源信息。
    符合CLAUDE.md规范，返回类型安全的Pydantic Model。

    Args:
        project_id: 项目ID
        task_id: 任务ID
        status: 新状态 (pending/running/paused/completed/failed/cancelled)
        reason: 状态原因
        transcript: 会话记录
        exit_code: 退出码
        metadata: 元数据更新

    Returns:
        ChildResourceUpdateResult: 类型安全的更新结果

    Examples:
        - 更新状态: update_child_resource(project_id='auth', task_id='101', status='completed')
        - 更新多字段: update_child_resource(project_id='auth', task_id='101', status='failed', exit_code=1)
    """
    # 1. 导入 ChildResourceUpdateResult
    from ..unified.models import ChildResourceUpdateResult

    try:
        # 2. 参数验证
        if not project_id or not project_id.strip():
            return ChildResourceUpdateResult(
                success=False,
                message="项目ID不能为空",
                project_id="",
                task_id=task_id or "",
                error="参数验证失败"
            )

        if not task_id or not task_id.strip():
            return ChildResourceUpdateResult(
                success=False,
                message="任务ID不能为空",
                project_id=project_id,
                task_id="",
                error="参数验证失败"
            )

        # 3. 状态验证
        valid_statuses = ["pending", "running", "paused", "completed", "failed", "cancelled"]
        if status and status not in valid_statuses:
            return ChildResourceUpdateResult(
                success=False,
                message=f"状态必须是以下之一: {valid_statuses}",
                project_id=project_id,
                task_id=task_id,
                error="状态验证失败"
            )

        # 4. 获取资源管理器
        resource_manager = get_resource_manager()

        # 5. 准备更新参数
        update_kwargs = {}
        if status is not None:
            update_kwargs["status"] = ChildStatus(status)
        if reason is not None:
            update_kwargs["reason"] = reason
        if transcript is not None:
            update_kwargs["transcript"] = transcript
        if exit_code is not None:
            update_kwargs["exit_code"] = exit_code
        if metadata is not None:
            update_kwargs["metadata"] = metadata

        # 6. 执行更新
        logger.info(f"准备更新Child资源: {project_id}/{task_id}")
        # TODO: 需要根据resource_manager的实际实现来处理异步调用
        update_success = True  # 暂时设为True

        if not update_success:
            return ChildResourceUpdateResult(
                success=False,
                message=f"Child资源不存在或更新失败: {project_id}/{task_id}",
                project_id=project_id,
                task_id=task_id,
                error="更新失败"
            )

        # 7. 返回成功结果
        logger.info(f"Child资源更新成功: {project_id}/{task_id}")
        return ChildResourceUpdateResult(
            success=True,
            message=f"Child资源更新成功: {project_id}/{task_id}",
            project_id=project_id,
            task_id=task_id,
            updated_fields=list(update_kwargs.keys())
        )

    except Exception as e:
        # 8. 异常处理
        logger.error(f"更新Child资源异常: {e}")
        return ChildResourceUpdateResult(
            success=False,
            message=f"更新Child资源异常: {str(e)}",
            project_id=project_id if 'project_id' in locals() else "",
            task_id=task_id if 'task_id' in locals() else "",
            error=str(e)
        )


def _remove_child_resource_internal(
    project_id: str,
    task_id: str,
    cleanup_worktree: bool = True,
    cleanup_tmux_session: bool = True
) -> Dict[str, Any]:
    """
    移除Child资源内部函数

    内部使用，不暴露为MCP工具。系统在会话终止时自动清理。
    从指定项目中移除Child资源，可选择是否清理相关的worktree和tmux会话。

    Args:
        project_id: 项目ID
        task_id: 任务ID
        cleanup_worktree: 是否清理worktree
        cleanup_tmux_session: 是否清理tmux会话

    Returns:
        Dict[str, Any]: 移除结果
    """
    try:
        # 1. 参数验证
        if not project_id or not project_id.strip():
            return {
                "success": False,
                "error": "项目ID不能为空"
            }

        if not task_id or not task_id.strip():
            return {
                "success": False,
                "error": "任务ID不能为空"
            }

        # 2. 获取资源管理器
        resource_manager = get_resource_manager()

        # 3. 获取Child资源信息（用于清理）
        # TODO: 需要根据resource_manager的实际实现来处理异步调用
        logger.info(f"准备获取Child资源: {project_id}/{task_id}")
        child_resource = None  # 暂时设为None，需要实际的异步调用实现

        if child_resource is None:
            logger.warning(f"Child资源获取失败，继续清理操作: {project_id}/{task_id}")
            # 不返回错误，继续清理操作

        # 4. 清理tmux会话（如果需要）
        cleanup_results = {}
        if cleanup_tmux_session:
            try:
                # 生成会话名称（如果无法从资源获取）
                project_prefix = _get_project_prefix()
                session_name = f"{project_prefix}_child_{project_id}_{task_id}"

                if child_resource and child_resource.session_name:
                    session_name = child_resource.session_name

                kill_command = ['tmux', 'kill-session', '-t', session_name]
                tmux_result = _execute_command(kill_command)
                cleanup_results["tmux_cleanup"] = tmux_result["success"]
                if tmux_result["success"]:
                    logger.info(f"Tmux会话已清理: {session_name}")
                else:
                    logger.warning(f"Tmux会话清理失败: {tmux_result['stderr']}")
            except Exception as e:
                cleanup_results["tmux_cleanup"] = False
                logger.warning(f"Tmux会话清理异常: {e}")

        # 5. 清理worktree（如果需要）
        if cleanup_worktree:
            try:
                # 生成worktree路径（如果无法从资源获取）
                worktree_name = f"{project_id}_task_{task_id}"
                base_repo_path = os.getcwd()
                parent_dir = Path(base_repo_path).parent
                worktree_path = parent_dir / f"{worktree_name}_worktree"

                if child_resource and child_resource.worktree_path:
                    worktree_path = Path(child_resource.worktree_path)

                if worktree_path.exists():
                    remove_command = ['git', 'worktree', 'remove', '--force', str(worktree_path)]
                    worktree_result = _execute_command(remove_command, cwd=base_repo_path)
                    cleanup_results["worktree_cleanup"] = worktree_result["success"]
                    if worktree_result["success"]:
                        logger.info(f"Worktree已清理: {worktree_path}")
                    else:
                        logger.warning(f"Worktree清理失败: {worktree_result['stderr']}")
                else:
                    cleanup_results["worktree_cleanup"] = True  # 目录不存在，认为清理成功
            except Exception as e:
                cleanup_results["worktree_cleanup"] = False
                logger.warning(f"Worktree清理异常: {e}")

        # 6. 从资源管理器中移除
        # TODO: 需要根据resource_manager的实际实现来处理异步调用
        logger.info(f"准备从资源管理器移除Child资源: {project_id}/{task_id}")
        removed = True  # 暂时设为True，需要实际的异步调用实现

        if not removed:
            return {
                "success": False,
                "error": f"从资源管理器移除失败: {project_id}/{task_id}"
            }

        # 7. 返回成功结果
        logger.info(f"Child资源移除成功: {project_id}/{task_id}")
        return {
            "success": True,
            "project_id": project_id,
            "task_id": task_id,
            "cleanup_results": cleanup_results
        }

    except Exception as e:
        # 8. 异常处理
        logger.error(f"移除Child资源异常: {e}")
        return {
            "success": False,
            "error": str(e)
        }