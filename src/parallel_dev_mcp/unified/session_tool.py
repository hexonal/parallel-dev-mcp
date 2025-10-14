# -*- coding: utf-8 -*-
"""
会话管理统一工具

@description 提供符合CLAUDE.md规范的会话管理MCP工具，遵循YAGNI原则
"""

import os
import logging
import subprocess
from typing import Optional, List
from pathlib import Path
from datetime import datetime

from ..mcp_instance import mcp
from .models import SessionInfo, SessionResult

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def _get_project_prefix() -> str:
    """
    获取项目前缀

    Returns:
        str: 项目前缀
    """
    # 1. 从环境变量获取
    return os.environ.get('PROJECT_PREFIX', 'PARALLEL')


def _execute_command(command: List[str], cwd: Optional[str] = None) -> tuple[bool, str, str]:
    """
    执行系统命令

    Args:
        command: 命令列表
        cwd: 工作目录

    Returns:
        tuple[bool, str, str]: (成功标志, 标准输出, 标准错误)
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
        return (
            result.returncode == 0,
            result.stdout.strip(),
            result.stderr.strip()
        )

    except subprocess.TimeoutExpired:
        # 3. 超时处理
        return (False, "", "命令执行超时")

    except Exception as e:
        # 4. 异常处理
        return (False, "", str(e))


def _create_session_impl(
    task_id: str,
    project_id: str
) -> SessionResult:
    """
    创建会话实现（不超过50行）

    Args:
        task_id: 任务ID
        project_id: 项目ID

    Returns:
        SessionResult: 创建结果
    """
    try:
        # 1. 参数验证
        if not task_id or not project_id:
            return SessionResult(
                success=False,
                action='create',
                message="task_id和project_id不能为空",
                error="参数验证失败"
            )

        # 2. 生成会话名称
        prefix = _get_project_prefix()
        session_name = f"{prefix}_child_{project_id}_{task_id}"
        session_id = f"{project_id}/{task_id}"

        # 3. 创建worktree
        base_path = os.getcwd()
        parent_dir = Path(base_path).parent
        worktree_path = parent_dir / f"{project_id}_task_{task_id}_worktree"
        branch_name = f"feature/task-{task_id}"

        # 4. 检查worktree是否已存在
        if worktree_path.exists():
            return SessionResult(
                success=False,
                action='create',
                message=f"Worktree已存在: {worktree_path}",
                error="Worktree路径冲突"
            )

        # 5. 创建Git worktree
        success, stdout, stderr = _execute_command(
            ['git', 'worktree', 'add', '-b', branch_name, str(worktree_path)],
            cwd=base_path
        )

        if not success:
            return SessionResult(
                success=False,
                action='create',
                message=f"Git worktree创建失败: {stderr}",
                error=stderr
            )

        # 6. 创建tmux会话
        success, stdout, stderr = _execute_command(
            ['tmux', 'new-session', '-d', '-s', session_name, '-c', str(worktree_path)]
        )

        if not success:
            # 清理worktree
            _execute_command(['git', 'worktree', 'remove', '--force', str(worktree_path)])
            return SessionResult(
                success=False,
                action='create',
                message=f"Tmux会话创建失败: {stderr}",
                error=stderr
            )

        # 7. 获取tmux会话ID
        success, tmux_id, stderr = _execute_command(
            ['tmux', 'display-message', '-t', session_name, '-p', '#{session_id}']
        )

        # 8. 创建SessionInfo
        session_info = SessionInfo(
            session_id=session_id,
            session_name=session_name,
            task_id=task_id,
            project_id=project_id,
            status='active',
            worktree_path=str(worktree_path),
            tmux_session_id=tmux_id if success else ""
        )

        # 9. 记录日志
        logger.info(f"会话创建成功: {session_name}")

        # 10. 返回成功结果
        return SessionResult(
            success=True,
            action='create',
            message=f"会话创建成功: {session_name}",
            session=session_info,
            count=1
        )

    except Exception as e:
        # 11. 异常处理
        logger.error(f"创建会话异常: {e}")
        return SessionResult(
            success=False,
            action='create',
            message=f"创建会话异常: {str(e)}",
            error=str(e)
        )


def _list_sessions_impl() -> SessionResult:
    """
    列出会话实现（不超过50行）

    Returns:
        SessionResult: 会话列表
    """
    try:
        # 1. 获取项目前缀
        prefix = _get_project_prefix()

        # 2. 执行tmux命令
        success, stdout, stderr = _execute_command(
            ['tmux', 'list-sessions', '-F', '#{session_name}:#{session_id}:#{session_created}']
        )

        # 3. 检查tmux是否运行
        if not success:
            if 'no server running' in stderr.lower():
                return SessionResult(
                    success=True,
                    action='list',
                    message="没有运行的tmux服务器",
                    sessions=[],
                    count=0
                )
            return SessionResult(
                success=False,
                action='list',
                message=f"获取会话列表失败: {stderr}",
                error=stderr
            )

        # 4. 解析会话信息
        sessions: List[SessionInfo] = []
        for line in stdout.split('\n'):
            if not line:
                continue

            parts = line.split(':')
            if len(parts) < 3:
                continue

            session_name = parts[0]
            tmux_id = parts[1]

            # 5. 过滤child会话
            if not session_name.startswith(f"{prefix}_child_"):
                continue

            # 6. 解析project_id和task_id
            try:
                # 格式: PREFIX_child_PROJECT_TASK
                name_parts = session_name.replace(f"{prefix}_child_", "").split('_')
                if len(name_parts) >= 2:
                    project_id = name_parts[0]
                    task_id = '_'.join(name_parts[1:])
                else:
                    continue
            except:
                continue

            # 7. 创建SessionInfo
            session_info = SessionInfo(
                session_id=f"{project_id}/{task_id}",
                session_name=session_name,
                task_id=task_id,
                project_id=project_id,
                status='active',
                worktree_path="",
                tmux_session_id=tmux_id
            )
            sessions.append(session_info)

        # 8. 记录日志
        logger.info(f"成功获取{len(sessions)}个会话")

        # 9. 返回结果
        return SessionResult(
            success=True,
            action='list',
            message=f"成功获取{len(sessions)}个会话",
            sessions=sessions,
            count=len(sessions)
        )

    except Exception as e:
        # 10. 异常处理
        logger.error(f"列出会话异常: {e}")
        return SessionResult(
            success=False,
            action='list',
            message=f"列出会话异常: {str(e)}",
            error=str(e)
        )


def _terminate_session_impl(task_id: str, project_id: str) -> SessionResult:
    """
    终止会话实现（不超过50行）

    Args:
        task_id: 任务ID
        project_id: 项目ID

    Returns:
        SessionResult: 终止结果
    """
    try:
        # 1. 参数验证
        if not task_id or not project_id:
            return SessionResult(
                success=False,
                action='terminate',
                message="task_id和project_id不能为空",
                error="参数验证失败"
            )

        # 2. 生成会话名称
        prefix = _get_project_prefix()
        session_name = f"{prefix}_child_{project_id}_{task_id}"

        # 3. 检查会话是否存在
        success, stdout, stderr = _execute_command(
            ['tmux', 'has-session', '-t', session_name]
        )

        if not success:
            return SessionResult(
                success=False,
                action='terminate',
                message=f"会话不存在: {session_name}",
                error="会话不存在"
            )

        # 4. 终止tmux会话
        success, stdout, stderr = _execute_command(
            ['tmux', 'kill-session', '-t', session_name]
        )

        if not success:
            return SessionResult(
                success=False,
                action='terminate',
                message=f"终止会话失败: {stderr}",
                error=stderr
            )

        # 5. 清理worktree
        base_path = os.getcwd()
        parent_dir = Path(base_path).parent
        worktree_path = parent_dir / f"{project_id}_task_{task_id}_worktree"

        if worktree_path.exists():
            _execute_command(
                ['git', 'worktree', 'remove', '--force', str(worktree_path)],
                cwd=base_path
            )

        # 6. 记录日志
        logger.info(f"会话终止成功: {session_name}")

        # 7. 返回成功结果
        return SessionResult(
            success=True,
            action='terminate',
            message=f"会话终止成功: {session_name}",
            count=0
        )

    except Exception as e:
        # 8. 异常处理
        logger.error(f"终止会话异常: {e}")
        return SessionResult(
            success=False,
            action='terminate',
            message=f"终止会话异常: {str(e)}",
            error=str(e)
        )


@mcp.tool
def session(
    action: str,
    task_id: Optional[str] = None,
    project_id: Optional[str] = None
) -> SessionResult:
    """
    会话管理工具

    统一的会话管理接口，符合CLAUDE.md规范和YAGNI原则。
    所有返回值为类型安全的Pydantic Model。

    Args:
        action: 操作类型 (create | list | terminate)
        task_id: 任务ID (create和terminate操作必需)
        project_id: 项目ID (create和terminate操作必需)

    Returns:
        SessionResult: 类型安全的操作结果

    Examples:
        - 创建会话: session(action='create', task_id='101', project_id='auth')
        - 列出会话: session(action='list')
        - 终止会话: session(action='terminate', task_id='101', project_id='auth')
    """
    # 1. 参数验证
    if action not in ['create', 'list', 'terminate']:
        return SessionResult(
            success=False,
            action=action,
            message=f"无效的操作类型: {action}，必须是 create/list/terminate",
            error="参数验证失败"
        )

    # 2. 路由到对应实现
    if action == 'create':
        if not task_id or not project_id:
            return SessionResult(
                success=False,
                action='create',
                message="create操作需要提供task_id和project_id",
                error="参数缺失"
            )
        return _create_session_impl(task_id, project_id)

    elif action == 'list':
        return _list_sessions_impl()

    elif action == 'terminate':
        if not task_id or not project_id:
            return SessionResult(
                success=False,
                action='terminate',
                message="terminate操作需要提供task_id和project_id",
                error="参数缺失"
            )
        return _terminate_session_impl(task_id, project_id)

    # 3. 不应该到达这里
    return SessionResult(
        success=False,
        action=action,
        message="未知错误",
        error="内部逻辑错误"
    )
