# -*- coding: utf-8 -*-
"""
Git 信息收集器

@description 获取当前仓库的 remote URL 和 branch 信息，处理各种边缘情况
"""

import logging
import subprocess
from pathlib import Path
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime

# 配置日志系统
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class GitRepositoryInfo(BaseModel):
    """
    Git 仓库信息数据模型

    包含仓库的基本信息和状态
    """

    remote_url: Optional[str] = Field(None, description="远程仓库URL")
    current_branch: Optional[str] = Field(None, description="当前分支名称")
    is_detached_head: bool = Field(False, description="是否处于detached HEAD状态")
    default_branch: Optional[str] = Field(None, description="默认分支名称")
    remotes: List[str] = Field(default_factory=list, description="所有远程仓库名称")
    is_git_repository: bool = Field(False, description="是否为Git仓库")
    repository_path: Optional[str] = Field(None, description="仓库根目录路径")

    model_config = ConfigDict(
        # 1. JSON编码器配置
        json_encoders={datetime: lambda v: v.isoformat()}
    )


class GitInfoCollector:
    """
    Git 信息收集器

    获取当前仓库的详细信息，处理各种边缘情况
    """

    def __init__(self, repository_path: Optional[Path] = None) -> None:
        """
        初始化Git信息收集器

        Args:
            repository_path: 仓库路径，默认为当前目录
        """
        # 1. 设置仓库路径
        self.repository_path = repository_path or Path.cwd()

        # 2. 记录初始化信息
        logger.info(f"Git信息收集器初始化: 路径={self.repository_path}")

    def execute_git_command(self, args: List[str], timeout: int = 10) -> Optional[str]:
        """
        执行Git命令并返回结果

        Args:
            args: Git命令参数列表
            timeout: 命令超时时间（秒）

        Returns:
            Optional[str]: 命令输出结果，失败时返回None
        """
        # 1. 构建完整命令
        command = ["git"] + args

        try:
            # 2. 执行Git命令
            result = subprocess.run(
                command,
                cwd=str(self.repository_path),
                capture_output=True,
                text=True,
                timeout=timeout,
                check=True,
            )

            # 3. 返回输出结果
            output = result.stdout.strip()
            logger.debug(f"Git命令执行成功: {' '.join(command)} -> {output}")
            return output

        except subprocess.CalledProcessError as e:
            # 4. 处理命令执行错误
            logger.warning(f"Git命令执行失败: {' '.join(command)} - {e}")
            return None

        except subprocess.TimeoutExpired:
            # 5. 处理超时
            logger.warning(f"Git命令执行超时: {' '.join(command)}")
            return None

        except Exception as e:
            # 6. 处理其他异常
            logger.error(f"Git命令执行时发生未知错误: {e}")
            return None

    def is_git_repository(self) -> bool:
        """
        检查当前目录是否为Git仓库

        Returns:
            bool: 是否为Git仓库
        """
        # 1. 尝试执行git rev-parse命令
        result = self.execute_git_command(["rev-parse", "--git-dir"])

        # 2. 返回检查结果
        is_repo = result is not None
        logger.debug(f"Git仓库检查结果: {is_repo}")
        return is_repo

    def get_repository_root(self) -> Optional[str]:
        """
        获取Git仓库根目录

        Returns:
            Optional[str]: 仓库根目录路径
        """
        # 1. 执行git rev-parse命令
        result = self.execute_git_command(["rev-parse", "--show-toplevel"])

        # 2. 记录结果
        if result:
            logger.debug(f"仓库根目录: {result}")
        else:
            logger.warning("无法获取仓库根目录")

        # 3. 返回结果
        return result

    def get_remote_url(self, remote_name: str = "origin") -> Optional[str]:
        """
        获取远程仓库URL

        Args:
            remote_name: 远程仓库名称

        Returns:
            Optional[str]: 远程仓库URL
        """
        # 1. 执行git remote get-url命令
        result = self.execute_git_command(["remote", "get-url", remote_name])

        # 2. 记录结果
        if result:
            logger.info(f"获取远程仓库URL: {remote_name} -> {result}")
        else:
            logger.warning(f"无法获取远程仓库URL: {remote_name}")

        # 3. 返回结果
        return result

    def get_all_remotes(self) -> List[str]:
        """
        获取所有远程仓库名称

        Returns:
            List[str]: 远程仓库名称列表
        """
        # 1. 执行git remote命令
        result = self.execute_git_command(["remote"])

        # 2. 处理结果
        if result:
            remotes = [
                remote.strip() for remote in result.split("\n") if remote.strip()
            ]
            logger.debug(f"所有远程仓库: {remotes}")
            return remotes
        else:
            # 3. 返回空列表
            logger.debug("没有找到远程仓库")
            return []

    def get_current_branch(self) -> Optional[str]:
        """
        获取当前分支名称

        Returns:
            Optional[str]: 当前分支名称，detached HEAD时返回None
        """
        # 1. 执行git branch --show-current命令
        result = self.execute_git_command(["branch", "--show-current"])

        # 2. 处理结果
        if result:
            logger.info(f"当前分支: {result}")
            return result
        else:
            # 3. 可能处于detached HEAD状态
            logger.warning("无法获取当前分支，可能处于detached HEAD状态")
            return None

    def is_detached_head(self) -> bool:
        """
        检查是否处于detached HEAD状态

        Returns:
            bool: 是否为detached HEAD
        """
        # 1. 执行git symbolic-ref命令
        result = self.execute_git_command(["symbolic-ref", "-q", "HEAD"])

        # 2. 如果命令失败，则可能是detached HEAD
        is_detached = result is None

        # 3. 记录结果
        if is_detached:
            logger.info("检测到detached HEAD状态")
        else:
            logger.debug("当前不是detached HEAD状态")

        # 4. 返回结果
        return is_detached

    def get_default_branch(self) -> Optional[str]:
        """
        获取默认分支名称

        Returns:
            Optional[str]: 默认分支名称
        """
        # 1. 尝试从远程获取默认分支
        result = self.execute_git_command(["symbolic-ref", "refs/remotes/origin/HEAD"])

        # 2. 处理结果
        if result:
            # 3. 提取分支名称
            default_branch = result.replace("refs/remotes/origin/", "")
            logger.info(f"默认分支: {default_branch}")
            return default_branch
        else:
            # 4. 尝试常见的默认分支名称
            for branch in ["main", "master"]:
                branch_exists = self.execute_git_command(
                    ["show-ref", "--verify", "--quiet", f"refs/heads/{branch}"]
                )
                if branch_exists is not None:
                    logger.info(f"找到默认分支: {branch}")
                    return branch

            # 5. 无法确定默认分支
            logger.warning("无法确定默认分支")
            return None

    def collect_repository_info(self) -> GitRepositoryInfo:
        """
        收集完整的Git仓库信息

        Returns:
            GitRepositoryInfo: 仓库信息对象
        """
        # 1. 检查是否为Git仓库
        if not self.is_git_repository():
            logger.warning("当前目录不是Git仓库")
            return GitRepositoryInfo(is_git_repository=False)

        # 2. 获取仓库根目录
        repo_root = self.get_repository_root()

        # 3. 获取所有远程仓库
        remotes = self.get_all_remotes()

        # 4. 获取远程URL（优先origin，否则使用第一个远程）
        remote_url = None
        if "origin" in remotes:
            remote_url = self.get_remote_url("origin")
        elif remotes:
            remote_url = self.get_remote_url(remotes[0])

        # 5. 检查detached HEAD状态
        is_detached = self.is_detached_head()

        # 6. 获取当前分支
        current_branch = None if is_detached else self.get_current_branch()

        # 7. 获取默认分支
        default_branch = self.get_default_branch()

        # 8. 创建仓库信息对象
        repo_info = GitRepositoryInfo(
            remote_url=remote_url,
            current_branch=current_branch,
            is_detached_head=is_detached,
            default_branch=default_branch,
            remotes=remotes,
            is_git_repository=True,
            repository_path=repo_root,
        )

        # 9. 记录收集结果
        logger.info(f"Git仓库信息收集完成: {repo_info}")

        # 10. 返回结果
        return repo_info


def create_git_info_collector(
    repository_path: Optional[Path] = None,
) -> GitInfoCollector:
    """
    创建Git信息收集器实例

    Args:
        repository_path: 仓库路径

    Returns:
        GitInfoCollector: 配置好的收集器实例
    """
    # 1. 创建收集器实例
    collector = GitInfoCollector(repository_path)

    # 2. 记录创建信息
    logger.info("Git信息收集器实例创建成功")

    # 3. 返回收集器实例
    return collector
