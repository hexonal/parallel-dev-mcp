# -*- coding: utf-8 -*-
"""
Git资源管理器

@description 将Git信息落盘到MCP资源系统，实现PRD要求的Git状态持久化
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

# 导入Git信息收集器
from .git_manager import GitInfoCollector

# 导入MCP资源管理器
from .resource_manager import get_resource_manager

# 配置日志系统
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class GitResourceManager:
    """
    Git资源管理器

    负责将Git信息（remote + branch）持久化到MCP资源系统，
    符合PRD要求："落盘 Git 信息（remote + branch）到 @mcp.resource"
    """

    def __init__(self, project_root: Optional[str] = None):
        """
        初始化Git资源管理器

        Args:
            project_root: 项目根目录
        """
        # 1. 初始化Git信息收集器
        from pathlib import Path
        repo_path = Path(project_root) if project_root else None
        self.git_collector = GitInfoCollector(repo_path)

        # 2. 记录初始化
        logger.info("Git资源管理器初始化完成")

    def sync_git_info_to_resources(self) -> Dict[str, Any]:
        """
        同步Git信息到MCP资源

        获取当前Git状态并更新到MCP资源系统中。

        Returns:
            Dict[str, Any]: 同步结果
        """
        try:
            # 1. 检查Master权限
            from .master_detector import is_master_node
            if not is_master_node():
                return {
                    "success": False,
                    "error": "仅Master节点可以同步Git信息到MCP资源",
                    "node_type": "non-master"
                }

            # 2. 获取Git信息
            try:
                git_repo_info = self.git_collector.collect_repository_info()
                if not git_repo_info.is_git_repository:
                    return {
                        "success": False,
                        "error": "当前目录不是Git仓库",
                        "git_info": git_repo_info.model_dump()
                    }
            except Exception as e:
                return {
                    "success": False,
                    "error": f"获取Git信息失败: {str(e)}"
                }

            # 3. 构造资源数据
            resource_data = {
                "git_remote_url": git_repo_info.remote_url,
                "git_branch": git_repo_info.current_branch,
                "git_repository_path": git_repo_info.repository_path,
                "git_default_branch": git_repo_info.default_branch,
                "git_remotes": git_repo_info.remotes,
                "git_is_detached_head": git_repo_info.is_detached_head,
                "last_sync_time": datetime.now().isoformat(),
                "sync_source": "master_node"
            }

            # 4. 获取资源管理器
            resource_manager = get_resource_manager()
            if not resource_manager:
                return {
                    "success": False,
                    "error": "无法获取MCP资源管理器实例"
                }

            # 5. 更新Master资源中的Git信息
            # 获取当前Master资源
            masters = resource_manager.get_masters()
            if not masters:
                # 如果没有Master资源，创建一个
                project_id = git_info.get("repository_name", "unknown_project")
                master_id = f"master_{project_id}"

                master_resource = {
                    "id": master_id,
                    "project_id": project_id,
                    "session_type": "master",
                    "git_info": resource_data,
                    "created_at": datetime.now().isoformat(),
                    "status": "active"
                }

                resource_manager.masters[master_id] = master_resource
                logger.info(f"创建新的Master资源并同步Git信息: {master_id}")
            else:
                # 更新现有Master资源
                for master_id, master_resource in masters.items():
                    master_resource["git_info"] = resource_data
                    master_resource["last_updated"] = datetime.now().isoformat()
                    logger.info(f"更新Master资源的Git信息: {master_id}")

            # 6. 强制刷新资源
            resource_manager._notify_resource_change()

            # 7. 返回成功结果
            logger.info("Git信息成功同步到MCP资源")
            return {
                "success": True,
                "message": "Git信息已同步到MCP资源",
                "git_info": resource_data,
                "master_count": len(masters) if masters else 1,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            # 8. 异常处理
            logger.error(f"同步Git信息到资源异常: {e}")
            return {
                "success": False,
                "error": f"同步失败: {str(e)}"
            }

    def get_git_resource_status(self) -> Dict[str, Any]:
        """
        获取Git资源状态

        Returns:
            Dict[str, Any]: Git资源状态
        """
        try:
            # 1. 获取当前Git信息
            git_repo_info = self.git_collector.collect_repository_info()

            # 2. 获取MCP资源中的Git信息
            resource_manager = get_resource_manager()
            masters = resource_manager.get_masters() if resource_manager else {}

            # 3. 提取资源中的Git信息
            resource_git_info = {}
            if masters:
                for master_id, master_resource in masters.items():
                    if "git_info" in master_resource:
                        resource_git_info[master_id] = master_resource["git_info"]

            # 4. 比较当前Git状态和资源状态
            current_git_dict = git_repo_info.model_dump()
            status = {
                "success": True,
                "current_git_info": current_git_dict,
                "resource_git_info": resource_git_info,
                "is_synced": self._compare_git_info(current_git_dict, resource_git_info),
                "master_count": len(masters) if masters else 0,
                "timestamp": datetime.now().isoformat()
            }

            return status

        except Exception as e:
            # 5. 异常处理
            logger.error(f"获取Git资源状态异常: {e}")
            return {
                "success": False,
                "error": f"状态查询失败: {str(e)}"
            }

    def _compare_git_info(self, current_git: Dict[str, Any], resource_git: Dict[str, Any]) -> bool:
        """
        比较当前Git信息和资源中的Git信息

        Args:
            current_git: 当前Git信息
            resource_git: 资源中的Git信息

        Returns:
            bool: 是否同步
        """
        try:
            # 1. 检查Git信息有效性
            if not current_git.get("is_git_repository") or not resource_git:
                return False

            # 2. 提取关键信息进行比较
            current_remote = current_git.get("remote_url")
            current_branch = current_git.get("current_branch")

            # 3. 检查所有Master资源
            for master_id, git_data in resource_git.items():
                resource_remote = git_data.get("git_remote_url")
                resource_branch = git_data.get("git_branch")

                # 如果有任一Master资源与当前Git信息匹配
                if (current_remote == resource_remote and
                    current_branch == resource_branch):
                    return True

            # 4. 如果没有匹配的资源，返回False
            return False

        except Exception as e:
            # 5. 异常处理
            logger.error(f"比较Git信息异常: {e}")
            return False

    def auto_sync_git_info(self) -> Dict[str, Any]:
        """
        自动同步Git信息

        在Master节点启动时自动调用，实现PRD要求的自动化。

        Returns:
            Dict[str, Any]: 同步结果
        """
        try:
            # 1. 检查是否为Master节点
            from .master_detector import is_master_node
            if not is_master_node():
                return {
                    "success": True,
                    "message": "非Master节点，跳过Git信息同步",
                    "action": "skipped"
                }

            # 2. 检查同步状态
            status = self.get_git_resource_status()
            if status.get("is_synced"):
                logger.info("Git信息已同步，无需重复操作")
                return {
                    "success": True,
                    "message": "Git信息已是最新状态",
                    "action": "already_synced"
                }

            # 3. 执行同步
            sync_result = self.sync_git_info_to_resources()
            sync_result["action"] = "auto_synced"

            if sync_result.get("success"):
                logger.info("Git信息自动同步完成")
            else:
                logger.warning(f"Git信息自动同步失败: {sync_result.get('error')}")

            return sync_result

        except Exception as e:
            # 4. 异常处理
            logger.error(f"自动同步Git信息异常: {e}")
            return {
                "success": False,
                "error": f"自动同步失败: {str(e)}"
            }


# 全局Git资源管理器实例
_git_resource_manager = None


def get_git_resource_manager(project_root: Optional[str] = None) -> GitResourceManager:
    """
    获取全局Git资源管理器实例

    Args:
        project_root: 项目根目录

    Returns:
        GitResourceManager: 管理器实例
    """
    global _git_resource_manager

    if _git_resource_manager is None:
        _git_resource_manager = GitResourceManager(project_root)
        logger.info("创建全局Git资源管理器实例")

    return _git_resource_manager


def auto_sync_git_to_resources() -> Dict[str, Any]:
    """
    自动同步Git信息到资源

    在系统初始化时调用，实现PRD要求的自动化。

    Returns:
        Dict[str, Any]: 同步结果
    """
    try:
        # 1. 获取管理器实例
        manager = get_git_resource_manager()

        # 2. 执行自动同步
        result = manager.auto_sync_git_info()

        # 3. 记录结果
        if result.get("success"):
            logger.info(f"Git信息自动同步完成: {result.get('action', 'unknown')}")
        else:
            logger.warning(f"Git信息自动同步失败: {result.get('error')}")

        return result

    except Exception as e:
        # 4. 异常处理
        logger.error(f"自动同步Git信息异常: {e}")
        return {
            "success": False,
            "error": f"自动同步异常: {str(e)}"
        }