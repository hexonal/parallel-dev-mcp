# -*- coding: utf-8 -*-
"""
Worktree 目录管理器

@description 在Master会话中管理worktree目录结构，提供目录创建、权限设置和清理策略
"""

import logging
import os
import stat
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict

from .git_manager import GitInfoCollector

# 配置日志系统
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class WorktreeInfo(BaseModel):
    """
    Worktree 信息数据模型

    包含worktree目录的基本信息和元数据
    """

    path: str = Field(..., description="Worktree目录路径")
    task_id: Optional[str] = Field(None, description="关联的任务ID")
    created_at: datetime = Field(..., description="创建时间")
    last_modified: datetime = Field(..., description="最后修改时间")
    size_bytes: int = Field(0, description="目录大小（字节）", ge=0)
    is_active: bool = Field(True, description="是否活跃状态")

    model_config = ConfigDict(
        # 1. JSON编码器配置
        json_encoders={datetime: lambda v: v.isoformat()}
    )


class WorktreeManager:
    """
    Worktree 目录管理器

    负责worktree目录的创建、维护和清理
    """

    def __init__(self, project_root: Optional[Path] = None) -> None:
        """
        初始化Worktree管理器

        Args:
            project_root: 项目根目录，默认为当前工作目录
        """
        # 1. 设置项目根目录
        self.project_root = project_root or Path.cwd()

        # 2. 确定worktree目录路径
        self.worktree_root = self.project_root / "worktree"

        # 3. 初始化Git信息收集器
        self.git_collector = GitInfoCollector(self.project_root)

        # 4. 记录初始化信息
        logger.info(f"Worktree管理器初始化: 项目根目录={self.project_root}")
        logger.info(f"Worktree目录: {self.worktree_root}")

    def ensure_worktree_directory(self) -> bool:
        """
        确保worktree目录存在并正确配置

        Returns:
            bool: 目录创建或配置是否成功
        """
        try:
            # 1. 创建worktree根目录
            self.worktree_root.mkdir(mode=0o755, parents=True, exist_ok=True)

            # 2. 设置目录权限
            self._set_directory_permissions(self.worktree_root, 0o755)

            # 3. 创建或更新.gitignore文件
            self._ensure_gitignore()

            # 4. 创建README文件
            self._ensure_readme()

            # 5. 记录成功信息
            logger.info(f"Worktree目录配置成功: {self.worktree_root}")

            # 6. 返回成功状态
            return True

        except Exception as e:
            # 7. 处理创建失败
            logger.error(f"Worktree目录创建失败: {e}")
            return False

    def _set_directory_permissions(self, directory: Path, mode: int) -> None:
        """
        设置目录权限

        Args:
            directory: 目录路径
            mode: 权限模式（八进制）
        """
        try:
            # 1. 设置目录权限
            os.chmod(directory, mode)

            # 2. 记录权限设置
            current_mode = oct(stat.S_IMODE(directory.stat().st_mode))
            logger.debug(f"目录权限设置: {directory} -> {current_mode}")

        except Exception as e:
            # 3. 权限设置失败警告
            logger.warning(f"设置目录权限失败: {directory} - {e}")

    def _ensure_gitignore(self) -> None:
        """
        确保.gitignore文件存在并包含worktree目录排除规则
        """
        # 1. 确定.gitignore文件路径
        gitignore_path = self.project_root / ".gitignore"

        # 2. 定义worktree排除规则
        worktree_rules = [
            "# Worktree directories (auto-generated)",
            "worktree/",
            "*.worktree/",
        ]

        try:
            # 3. 读取现有.gitignore内容
            existing_content = ""
            if gitignore_path.exists():
                existing_content = gitignore_path.read_text(encoding="utf-8")

            # 4. 检查是否需要添加规则
            needs_update = False
            for rule in worktree_rules:
                if rule not in existing_content:
                    needs_update = True
                    break

            # 5. 如果需要更新，添加规则
            if needs_update:
                # 6. 确保内容以换行结尾
                if existing_content and not existing_content.endswith("\n"):
                    existing_content += "\n"

                # 7. 添加worktree规则
                updated_content = (
                    existing_content + "\n" + "\n".join(worktree_rules) + "\n"
                )

                # 8. 写入更新的内容
                gitignore_path.write_text(updated_content, encoding="utf-8")

                # 9. 记录更新信息
                logger.info(".gitignore文件已更新，添加worktree排除规则")
            else:
                # 10. 规则已存在
                logger.debug(".gitignore文件已包含worktree排除规则")

        except Exception as e:
            # 11. 处理.gitignore更新失败
            logger.warning(f".gitignore文件更新失败: {e}")

    def _ensure_readme(self) -> None:
        """
        确保worktree目录包含README文件
        """
        # 1. 确定README文件路径
        readme_path = self.worktree_root / "README.md"

        # 2. 如果README不存在，创建它
        if not readme_path.exists():
            try:
                # 3. 定义README内容
                readme_content = """# Worktree Directory

This directory is automatically managed by the parallel-dev-mcp system.

## Purpose

This directory contains Git worktrees created for parallel development tasks:
- Each subdirectory represents a separate working tree for a specific task
- Naming convention: `task_<task_id>_<timestamp>`
- Automatically cleaned up when tasks are completed

## Directory Structure

```
worktree/
├── task_001_20250918_123456/    # Task 1 worktree
├── task_002_20250918_134567/    # Task 2 worktree
└── README.md                    # This file
```

## Management

- **Auto-creation**: Directories are created on-demand
- **Auto-cleanup**: Expired worktrees are removed automatically
- **Permissions**: Standard 755 permissions for development use

⚠️ **Warning**: Do not manually modify files in this directory.
All changes should be made through the parallel-dev-mcp system.
"""

                # 4. 写入README内容
                readme_path.write_text(readme_content, encoding="utf-8")

                # 5. 记录README创建
                logger.info(f"Worktree README文件创建成功: {readme_path}")

            except Exception as e:
                # 6. 处理README创建失败
                logger.warning(f"Worktree README文件创建失败: {e}")

    def create_task_worktree(self, task_id: str) -> Optional[Path]:
        """
        为指定任务创建worktree目录

        Args:
            task_id: 任务ID

        Returns:
            Optional[Path]: 创建的worktree目录路径，失败时返回None
        """
        try:
            # 1. 确保根目录存在
            if not self.ensure_worktree_directory():
                logger.error("无法创建根worktree目录")
                return None

            # 2. 生成worktree目录名称
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            worktree_name = f"task_{task_id}_{timestamp}"
            worktree_path = self.worktree_root / worktree_name

            # 3. 创建任务worktree目录
            worktree_path.mkdir(mode=0o755, parents=True, exist_ok=True)

            # 4. 设置目录权限
            self._set_directory_permissions(worktree_path, 0o755)

            # 5. 创建任务信息文件
            self._create_task_info_file(worktree_path, task_id)

            # 6. 记录创建成功
            logger.info(f"任务worktree创建成功: {worktree_path}")

            # 7. 返回目录路径
            return worktree_path

        except Exception as e:
            # 8. 处理创建失败
            logger.error(f"任务worktree创建失败: {task_id} - {e}")
            return None

    def _create_task_info_file(self, worktree_path: Path, task_id: str) -> None:
        """
        在worktree目录中创建任务信息文件

        Args:
            worktree_path: worktree目录路径
            task_id: 任务ID
        """
        try:
            # 1. 定义任务信息文件路径
            info_file = worktree_path / ".task_info.json"

            # 2. 获取Git信息
            git_info = self.git_collector.collect_repository_info()

            # 3. 构建任务信息
            task_info = {
                "task_id": task_id,
                "created_at": datetime.now().isoformat(),
                "worktree_path": str(worktree_path),
                "project_root": str(self.project_root),
                "git_info": {
                    "remote_url": git_info.remote_url,
                    "current_branch": git_info.current_branch,
                    "repository_path": git_info.repository_path,
                },
                "system_info": {
                    "created_by": "parallel-dev-mcp",
                    "version": "1.0.0",
                },
            }

            # 4. 写入任务信息文件
            import json

            with open(info_file, "w", encoding="utf-8") as f:
                json.dump(task_info, f, ensure_ascii=False, indent=2)

            # 5. 记录信息文件创建
            logger.debug(f"任务信息文件创建: {info_file}")

        except Exception as e:
            # 6. 处理信息文件创建失败
            logger.warning(f"任务信息文件创建失败: {e}")

    def list_worktrees(self) -> List[WorktreeInfo]:
        """
        列出所有worktree目录信息

        Returns:
            List[WorktreeInfo]: worktree目录信息列表
        """
        worktrees = []

        try:
            # 1. 检查worktree根目录是否存在
            if not self.worktree_root.exists():
                logger.debug("Worktree根目录不存在")
                return worktrees

            # 2. 遍历worktree目录
            for item in self.worktree_root.iterdir():
                if item.is_dir() and not item.name.startswith("."):
                    # 3. 解析worktree信息
                    worktree_info = self._parse_worktree_info(item)
                    if worktree_info:
                        worktrees.append(worktree_info)

            # 4. 按创建时间排序
            worktrees.sort(key=lambda x: x.created_at, reverse=True)

            # 5. 记录列表信息
            logger.debug(f"找到 {len(worktrees)} 个worktree目录")

        except Exception as e:
            # 6. 处理列表获取失败
            logger.error(f"列出worktree目录失败: {e}")

        # 7. 返回worktree列表
        return worktrees

    def _parse_worktree_info(self, worktree_path: Path) -> Optional[WorktreeInfo]:
        """
        解析worktree目录信息

        Args:
            worktree_path: worktree目录路径

        Returns:
            Optional[WorktreeInfo]: worktree信息对象
        """
        try:
            # 1. 获取目录统计信息
            stat_info = worktree_path.stat()

            # 2. 提取任务ID（从目录名）
            task_id = None
            if worktree_path.name.startswith("task_"):
                parts = worktree_path.name.split("_")
                if len(parts) >= 2:
                    task_id = parts[1]

            # 3. 计算目录大小
            total_size = self._calculate_directory_size(worktree_path)

            # 4. 创建WorktreeInfo对象
            worktree_info = WorktreeInfo(
                path=str(worktree_path),
                task_id=task_id,
                created_at=datetime.fromtimestamp(stat_info.st_ctime),
                last_modified=datetime.fromtimestamp(stat_info.st_mtime),
                size_bytes=total_size,
                is_active=True,
            )

            # 5. 返回worktree信息
            return worktree_info

        except Exception as e:
            # 6. 处理解析失败
            logger.warning(f"解析worktree信息失败: {worktree_path} - {e}")
            return None

    def _calculate_directory_size(self, directory: Path) -> int:
        """
        计算目录总大小

        Args:
            directory: 目录路径

        Returns:
            int: 目录大小（字节）
        """
        total_size = 0

        try:
            # 1. 遍历目录中的所有文件
            for dirpath, dirnames, filenames in os.walk(directory):
                for filename in filenames:
                    filepath = Path(dirpath) / filename
                    try:
                        # 2. 累加文件大小
                        total_size += filepath.stat().st_size
                    except (OSError, IOError):
                        # 3. 跳过无法访问的文件
                        pass

        except Exception as e:
            # 4. 处理大小计算失败
            logger.debug(f"计算目录大小失败: {directory} - {e}")

        # 5. 返回总大小
        return total_size

    def clean_expired_worktrees(self, max_age_hours: int = 72) -> Dict[str, Any]:
        """
        清理过期的worktree目录

        Args:
            max_age_hours: 最大存活时间（小时），默认72小时

        Returns:
            Dict[str, Any]: 清理结果统计
        """
        # 1. 初始化清理统计
        cleanup_stats = {
            "total_found": 0,
            "expired_count": 0,
            "cleaned_count": 0,
            "failed_count": 0,
            "size_freed_bytes": 0,
            "cleaned_paths": [],
            "failed_paths": [],
        }

        try:
            # 2. 获取所有worktree列表
            worktrees = self.list_worktrees()
            cleanup_stats["total_found"] = len(worktrees)

            # 3. 计算过期时间点
            expiry_time = datetime.now() - timedelta(hours=max_age_hours)

            # 4. 遍历worktree进行清理检查
            for worktree in worktrees:
                # 5. 检查是否过期
                if worktree.last_modified < expiry_time:
                    cleanup_stats["expired_count"] += 1

                    # 6. 尝试清理过期worktree
                    if self._remove_worktree(Path(worktree.path)):
                        cleanup_stats["cleaned_count"] += 1
                        cleanup_stats["size_freed_bytes"] += worktree.size_bytes
                        cleanup_stats["cleaned_paths"].append(worktree.path)
                    else:
                        cleanup_stats["failed_count"] += 1
                        cleanup_stats["failed_paths"].append(worktree.path)

            # 7. 记录清理结果
            logger.info(
                f"Worktree清理完成: 找到 {cleanup_stats['total_found']} 个，"
                f"过期 {cleanup_stats['expired_count']} 个，"
                f"清理 {cleanup_stats['cleaned_count']} 个，"
                f"释放 {cleanup_stats['size_freed_bytes']} 字节"
            )

        except Exception as e:
            # 8. 处理清理异常
            logger.error(f"Worktree清理过程异常: {e}")

        # 9. 返回清理统计
        return cleanup_stats

    def _remove_worktree(self, worktree_path: Path) -> bool:
        """
        删除指定的worktree目录

        Args:
            worktree_path: worktree目录路径

        Returns:
            bool: 删除是否成功
        """
        try:
            # 1. 检查路径是否存在
            if not worktree_path.exists():
                logger.debug(f"Worktree目录不存在: {worktree_path}")
                return True

            # 2. 确保是worktree子目录
            if not str(worktree_path).startswith(str(self.worktree_root)):
                logger.warning(f"拒绝删除非worktree目录: {worktree_path}")
                return False

            # 3. 删除目录和所有内容
            import shutil

            shutil.rmtree(worktree_path)

            # 4. 记录删除成功
            logger.info(f"Worktree目录删除成功: {worktree_path}")

            # 5. 返回成功状态
            return True

        except Exception as e:
            # 6. 处理删除失败
            logger.error(f"Worktree目录删除失败: {worktree_path} - {e}")
            return False

    def get_worktree_by_task_id(self, task_id: str) -> Optional[WorktreeInfo]:
        """
        根据任务ID获取worktree信息

        Args:
            task_id: 任务ID

        Returns:
            Optional[WorktreeInfo]: worktree信息，未找到时返回None
        """
        # 1. 获取所有worktree
        worktrees = self.list_worktrees()

        # 2. 查找匹配的任务ID
        for worktree in worktrees:
            if worktree.task_id == task_id:
                return worktree

        # 3. 未找到匹配的worktree
        logger.debug(f"未找到任务ID为 {task_id} 的worktree")
        return None

    def get_stats(self) -> Dict[str, Any]:
        """
        获取worktree管理统计信息

        Returns:
            Dict[str, Any]: 统计信息字典
        """
        try:
            # 1. 获取所有worktree信息
            worktrees = self.list_worktrees()

            # 2. 计算统计数据
            total_count = len(worktrees)
            total_size = sum(w.size_bytes for w in worktrees)
            active_count = sum(1 for w in worktrees if w.is_active)

            # 3. 计算平均大小
            avg_size = total_size / total_count if total_count > 0 else 0

            # 4. 找到最新和最旧的worktree
            newest_worktree = (
                max(worktrees, key=lambda x: x.created_at) if worktrees else None
            )
            oldest_worktree = (
                min(worktrees, key=lambda x: x.created_at) if worktrees else None
            )

            # 5. 构建统计信息
            stats = {
                "total_worktrees": total_count,
                "active_worktrees": active_count,
                "total_size_bytes": total_size,
                "average_size_bytes": int(avg_size),
                "worktree_root": str(self.worktree_root),
                "newest_worktree": newest_worktree.path if newest_worktree else None,
                "oldest_worktree": oldest_worktree.path if oldest_worktree else None,
                "collected_at": datetime.now().isoformat(),
            }

            # 6. 记录统计收集
            logger.debug(f"Worktree统计信息收集完成: {total_count} 个目录")

            # 7. 返回统计信息
            return stats

        except Exception as e:
            # 8. 处理统计收集失败
            logger.error(f"Worktree统计信息收集失败: {e}")
            return {"error": str(e), "collected_at": datetime.now().isoformat()}


def create_worktree_manager(project_root: Optional[Path] = None) -> WorktreeManager:
    """
    创建Worktree管理器实例

    Args:
        project_root: 项目根目录

    Returns:
        WorktreeManager: 配置好的Worktree管理器实例
    """
    # 1. 创建管理器实例
    manager = WorktreeManager(project_root)

    # 2. 确保基础目录结构
    manager.ensure_worktree_directory()

    # 3. 记录创建信息
    logger.info("Worktree管理器实例创建成功")

    # 4. 返回管理器实例
    return manager
