# -*- coding: utf-8 -*-
"""
Child会话生命周期管理器

@description 实现完整的Child会话创建、管理和清理功能
"""

import os
import logging
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

# 导入Git管理器
from .git_manager import GitInfoCollector

# 导入资源管理器
from .resource_manager import get_resource_manager

# 注：消息系统可通过其他方式发送，暂不导入

# 配置日志系统
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ChildLifecycleManager:
    """
    Child会话生命周期管理器

    负责实现PRD第5节的Child职责：
    1. tmux创建：{PROJECT_PREFIX}_child_{taskId}
    2. 在 ./worktree/{taskId} 挂载分支
    3. 启动Claude Code
    4. 管理会话生命周期
    """

    def __init__(self, project_root: Optional[str] = None):
        """
        初始化Child生命周期管理器

        Args:
            project_root: 项目根目录
        """
        # 1. 设置项目根目录
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.worktree_dir = self.project_root / "worktree"

        # 2. 初始化Git收集器
        self.git_collector = GitInfoCollector(self.project_root)

        # 3. 获取项目前缀
        self.project_prefix = os.environ.get('PROJECT_PREFIX')

        # 4. 记录初始化
        logger.info("Child生命周期管理器初始化完成")

    def create_child_session(
        self,
        task_id: str,
        branch_name: Optional[str] = None,
        use_template: bool = True
    ) -> Dict[str, Any]:
        """
        创建完整的Child会话

        Args:
            task_id: 任务ID
            branch_name: 分支名称（可选，默认自动生成）
            use_template: 是否使用模板文件

        Returns:
            Dict[str, Any]: 创建结果
        """
        try:
            # 1. 验证环境
            if not self.project_prefix:
                return {
                    "success": False,
                    "error": "缺少PROJECT_PREFIX环境变量"
                }

            # 2. 生成会话名称
            session_name = f"{self.project_prefix}_child_{task_id}"

            # 3. 检查会话是否已存在
            if self._check_session_exists(session_name):
                return {
                    "success": False,
                    "error": f"会话 {session_name} 已存在",
                    "session_name": session_name
                }

            # 4. 创建worktree
            worktree_result = self._create_worktree(task_id, branch_name)
            if not worktree_result.get("success"):
                return worktree_result

            # 5. 创建tmux会话
            tmux_result = self._create_tmux_session(session_name, task_id)
            if not tmux_result.get("success"):
                # 清理worktree
                self._cleanup_worktree(task_id)
                return tmux_result

            # 6. 启动Claude Code（如果配置了）
            claude_result = self._start_claude_in_session(session_name, task_id, use_template)

            # 7. 更新MCP资源
            self._register_child_resource(task_id, session_name, worktree_result["branch"])

            # 8. 返回成功结果
            logger.info(f"Child会话创建成功: {session_name}")
            return {
                "success": True,
                "message": f"Child会话 {session_name} 创建成功",
                "session_name": session_name,
                "task_id": task_id,
                "worktree_path": str(self.worktree_dir / task_id),
                "branch": worktree_result["branch"],
                "claude_started": claude_result.get("success", False),
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            # 9. 异常处理
            logger.error(f"创建Child会话异常: {e}")
            return {
                "success": False,
                "error": f"创建失败: {str(e)}"
            }

    def _create_worktree(self, task_id: str, branch_name: Optional[str] = None) -> Dict[str, Any]:
        """
        创建Git worktree

        Args:
            task_id: 任务ID
            branch_name: 分支名称

        Returns:
            Dict[str, Any]: 创建结果
        """
        try:
            # 1. 确保worktree目录存在
            self.worktree_dir.mkdir(parents=True, exist_ok=True)

            # 2. 生成分支名称
            if not branch_name:
                branch_name = f"task/{task_id}"

            # 3. worktree路径
            worktree_path = self.worktree_dir / task_id

            # 4. 检查worktree是否已存在
            if worktree_path.exists():
                return {
                    "success": False,
                    "error": f"Worktree {worktree_path} 已存在"
                }

            # 5. 创建新分支和worktree
            result = subprocess.run(
                ['git', 'worktree', 'add', '-b', branch_name, str(worktree_path)],
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                return {
                    "success": False,
                    "error": f"创建worktree失败: {result.stderr}"
                }

            # 6. 返回成功
            logger.info(f"Worktree创建成功: {worktree_path}")
            return {
                "success": True,
                "worktree_path": str(worktree_path),
                "branch": branch_name
            }

        except Exception as e:
            # 7. 异常处理
            logger.error(f"创建worktree异常: {e}")
            return {
                "success": False,
                "error": f"Worktree创建失败: {str(e)}"
            }

    def _create_tmux_session(self, session_name: str, task_id: str) -> Dict[str, Any]:
        """
        创建tmux会话

        Args:
            session_name: 会话名称
            task_id: 任务ID

        Returns:
            Dict[str, Any]: 创建结果
        """
        try:
            # 1. 工作目录
            work_dir = self.worktree_dir / task_id

            # 2. 创建tmux会话
            result = subprocess.run(
                ['tmux', 'new-session', '-d', '-s', session_name, '-c', str(work_dir)],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                return {
                    "success": False,
                    "error": f"创建tmux会话失败: {result.stderr}"
                }

            # 3. 设置环境变量
            env_commands = [
                f"export PROJECT_PREFIX='{self.project_prefix}'",
                f"export TASK_ID='{task_id}'",
                f"export SESSION_TYPE='child'",
                f"export WORK_DIR='{work_dir}'"
            ]

            for cmd in env_commands:
                subprocess.run(
                    ['tmux', 'send-keys', '-t', session_name, cmd, 'Enter'],
                    timeout=5
                )

            # 4. 返回成功
            logger.info(f"Tmux会话创建成功: {session_name}")
            return {
                "success": True,
                "session_name": session_name
            }

        except Exception as e:
            # 5. 异常处理
            logger.error(f"创建tmux会话异常: {e}")
            return {
                "success": False,
                "error": f"Tmux会话创建失败: {str(e)}"
            }

    def _start_claude_in_session(
        self,
        session_name: str,
        task_id: str,
        use_template: bool
    ) -> Dict[str, Any]:
        """
        在会话中启动Claude Code

        Args:
            session_name: 会话名称
            task_id: 任务ID
            use_template: 是否使用模板

        Returns:
            Dict[str, Any]: 启动结果
        """
        try:
            # 1. 构建Claude启动命令
            claude_cmd = self._build_claude_command(use_template)

            # 2. 在tmux会话中执行
            if claude_cmd:
                result = subprocess.run(
                    ['tmux', 'send-keys', '-t', session_name, claude_cmd, 'Enter'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )

                if result.returncode == 0:
                    logger.info(f"Claude Code启动命令已发送到: {session_name}")
                    return {
                        "success": True,
                        "command": claude_cmd
                    }

            return {
                "success": False,
                "message": "未配置Claude启动命令"
            }

        except Exception as e:
            # 3. 异常处理
            logger.error(f"启动Claude异常: {e}")
            return {
                "success": False,
                "error": f"启动失败: {str(e)}"
            }

    def _build_claude_command(self, use_template: bool) -> str:
        """
        构建Claude启动命令

        Args:
            use_template: 是否使用模板

        Returns:
            str: Claude命令
        """
        # 1. 基础命令
        cmd_parts = ['claude']

        # 2. 添加MCP配置
        mcp_config = os.environ.get('MCP_CONFIG_PATH')
        if mcp_config:
            cmd_parts.extend(['--mcp-config', mcp_config])

        # 3. 添加权限跳过
        skip_perms = os.environ.get('DANGEROUSLY_SKIP_PERMISSIONS')
        if skip_perms == 'true':
            cmd_parts.append('--dangerously-skip-permissions')

        # 4. 添加模板（如果存在）
        if use_template:
            template_path = self.project_root / 'child.txt'
            if template_path.exists():
                cmd_parts.extend(['--prompt', f'@{template_path}'])

        # 5. 返回命令
        return ' '.join(cmd_parts) if len(cmd_parts) > 1 else ''

    def _check_session_exists(self, session_name: str) -> bool:
        """
        检查tmux会话是否存在

        Args:
            session_name: 会话名称

        Returns:
            bool: 是否存在
        """
        try:
            result = subprocess.run(
                ['tmux', 'has-session', '-t', session_name],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except:
            return False

    def _cleanup_worktree(self, task_id: str) -> None:
        """
        清理worktree

        Args:
            task_id: 任务ID
        """
        try:
            worktree_path = self.worktree_dir / task_id
            if worktree_path.exists():
                subprocess.run(
                    ['git', 'worktree', 'remove', str(worktree_path), '--force'],
                    cwd=str(self.project_root),
                    timeout=10
                )
                logger.info(f"Worktree清理成功: {worktree_path}")
        except Exception as e:
            logger.error(f"清理worktree失败: {e}")

    def _register_child_resource(
        self,
        task_id: str,
        session_name: str,
        branch: str
    ) -> None:
        """
        注册Child资源到MCP

        Args:
            task_id: 任务ID
            session_name: 会话名称
            branch: 分支名称
        """
        try:
            resource_manager = get_resource_manager()
            if resource_manager:
                child_id = f"child_{task_id}"
                child_data = {
                    "id": child_id,
                    "task_id": task_id,
                    "session_name": session_name,
                    "session_type": "child",
                    "branch": branch,
                    "worktree_path": str(self.worktree_dir / task_id),
                    "created_at": datetime.now().isoformat(),
                    "status": "active"
                }
                resource_manager.children[child_id] = child_data
                resource_manager._notify_resource_change()
                logger.info(f"Child资源注册成功: {child_id}")
        except Exception as e:
            logger.error(f"注册Child资源失败: {e}")

    def terminate_child_session(self, task_id: str) -> Dict[str, Any]:
        """
        终止Child会话

        Args:
            task_id: 任务ID

        Returns:
            Dict[str, Any]: 终止结果
        """
        try:
            # 1. 生成会话名称
            session_name = f"{self.project_prefix}_child_{task_id}"

            # 2. 终止tmux会话
            if self._check_session_exists(session_name):
                result = subprocess.run(
                    ['tmux', 'kill-session', '-t', session_name],
                    capture_output=True,
                    text=True,
                    timeout=10
                )

                if result.returncode != 0:
                    logger.warning(f"终止tmux会话失败: {result.stderr}")

            # 3. 清理worktree
            self._cleanup_worktree(task_id)

            # 4. 更新MCP资源
            resource_manager = get_resource_manager()
            if resource_manager:
                child_id = f"child_{task_id}"
                if child_id in resource_manager.children:
                    resource_manager.children[child_id]["status"] = "terminated"
                    resource_manager.children[child_id]["terminated_at"] = datetime.now().isoformat()
                    resource_manager._notify_resource_change()

            # 5. 返回成功
            logger.info(f"Child会话终止成功: {session_name}")
            return {
                "success": True,
                "message": f"Child会话 {session_name} 已终止",
                "task_id": task_id,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            # 6. 异常处理
            logger.error(f"终止Child会话异常: {e}")
            return {
                "success": False,
                "error": f"终止失败: {str(e)}"
            }

    def list_child_sessions(self) -> Dict[str, Any]:
        """
        列出所有Child会话

        Returns:
            Dict[str, Any]: Child会话列表
        """
        try:
            # 1. 获取所有tmux会话
            result = subprocess.run(
                ['tmux', 'list-sessions', '-F', '#{session_name}:#{session_windows}:#{session_created}'],
                capture_output=True,
                text=True,
                timeout=10
            )

            sessions = []
            if result.returncode == 0 and self.project_prefix:
                child_prefix = f"{self.project_prefix}_child_"

                for line in result.stdout.strip().split('\n'):
                    if line and line.startswith(child_prefix):
                        parts = line.split(':')
                        session_name = parts[0]
                        task_id = session_name[len(child_prefix):]

                        session_info = {
                            "session_name": session_name,
                            "task_id": task_id,
                            "windows": int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0,
                            "created": parts[2] if len(parts) > 2 else "unknown"
                        }
                        sessions.append(session_info)

            # 2. 返回结果
            return {
                "success": True,
                "child_sessions": sessions,
                "count": len(sessions),
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            # 3. 异常处理
            logger.error(f"列出Child会话异常: {e}")
            return {
                "success": False,
                "error": f"查询失败: {str(e)}"
            }


# 全局Child生命周期管理器实例
_child_lifecycle_manager = None


def get_child_lifecycle_manager(project_root: Optional[str] = None) -> ChildLifecycleManager:
    """
    获取全局Child生命周期管理器实例

    Args:
        project_root: 项目根目录

    Returns:
        ChildLifecycleManager: 管理器实例
    """
    global _child_lifecycle_manager

    if _child_lifecycle_manager is None:
        _child_lifecycle_manager = ChildLifecycleManager(project_root)
        logger.info("创建全局Child生命周期管理器实例")

    return _child_lifecycle_manager