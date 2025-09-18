# -*- coding: utf-8 -*-
"""
Worktree自动管理器

@description 实现./worktree/目录的自动创建和管理，符合PRD要求
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

# 导入Git信息收集器
from .git_manager import GitInfoCollector

# 配置日志系统
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class WorktreeAutoManager:
    """
    Worktree自动管理器

    负责自动创建和管理./worktree/目录，实现PRD要求：
    - Master职责4: "自动创建 ./worktree/"
    - Child职责2: "在 ./worktree/{taskId} 挂载分支"
    """

    def __init__(self, project_root: Optional[str] = None):
        """
        初始化Worktree自动管理器

        Args:
            project_root: 项目根目录，默认为当前目录
        """
        # 1. 设置项目根目录
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.worktree_dir = self.project_root / "worktree"

        # 2. 初始化Git管理器
        self.git_collector = GitInfoCollector(self.project_root)

        # 3. 记录初始化
        logger.info(f"Worktree自动管理器初始化: {self.worktree_dir}")

    def ensure_worktree_directory(self) -> Dict[str, Any]:
        """
        确保worktree目录存在

        Master节点自动创建worktree目录。

        Returns:
            Dict[str, Any]: 创建结果
        """
        try:
            # 1. 检查Master权限
            from .master_detector import is_master_node
            if not is_master_node():
                return {
                    "success": False,
                    "error": "仅Master节点可以创建worktree目录",
                    "node_type": "non-master"
                }

            # 2. 检查目录是否已存在
            if self.worktree_dir.exists():
                logger.info(f"worktree目录已存在: {self.worktree_dir}")
                return {
                    "success": True,
                    "message": "worktree目录已存在",
                    "directory_path": str(self.worktree_dir),
                    "action": "existing"
                }

            # 3. 创建worktree目录
            self.worktree_dir.mkdir(parents=True, exist_ok=True)

            # 4. 验证创建
            if self.worktree_dir.exists() and self.worktree_dir.is_dir():
                logger.info(f"worktree目录创建成功: {self.worktree_dir}")

                # 5. 创建README文件说明
                readme_file = self.worktree_dir / "README.md"
                readme_content = f"""# Worktree Directory

此目录由parallel-dev-mcp系统自动创建，用于管理Child会话的Git worktree。

## 目录结构
```
worktree/
├── README.md           # 此说明文件
├── <taskId>/          # Child会话工作目录
│   ├── .git           # Git worktree元数据
│   └── <项目文件>      # 项目源码（独立分支）
```

## 注意事项
- 每个Child会话在独立的子目录中工作
- 子目录使用taskId命名
- 每个子目录都是独立的Git worktree
- 不要手动修改此目录结构

创建时间: {datetime.now().isoformat()}
"""
                with open(readme_file, 'w', encoding='utf-8') as f:
                    f.write(readme_content)

                return {
                    "success": True,
                    "message": "worktree目录创建成功",
                    "directory_path": str(self.worktree_dir),
                    "readme_created": True,
                    "action": "created"
                }
            else:
                return {
                    "success": False,
                    "error": "worktree目录创建失败，无法验证"
                }

        except Exception as e:
            # 6. 异常处理
            logger.error(f"确保worktree目录异常: {e}")
            return {
                "success": False,
                "error": f"创建失败: {str(e)}"
            }

    def create_child_worktree(self, task_id: str, branch_name: Optional[str] = None) -> Dict[str, Any]:
        """
        为Child会话创建worktree

        Args:
            task_id: 任务ID，用作子目录名称
            branch_name: 分支名称，如果不提供则创建新分支

        Returns:
            Dict[str, Any]: 创建结果
        """
        try:
            # 1. 参数验证
            if not task_id or not task_id.strip():
                return {
                    "success": False,
                    "error": "task_id不能为空"
                }

            task_id = task_id.strip()
            child_worktree_path = self.worktree_dir / task_id

            # 2. 检查是否已存在
            if child_worktree_path.exists():
                return {
                    "success": True,
                    "message": f"Child worktree已存在: {task_id}",
                    "worktree_path": str(child_worktree_path),
                    "task_id": task_id,
                    "action": "existing"
                }

            # 3. 确保主worktree目录存在
            ensure_result = self.ensure_worktree_directory()
            if not ensure_result.get("success"):
                return ensure_result

            # 4. 准备分支名称
            if not branch_name:
                branch_name = f"task/{task_id}"

            # 5. 检查Git仓库状态
            git_info = self.git_manager.get_git_info()
            if not git_info.get("success"):
                return {
                    "success": False,
                    "error": f"获取Git信息失败: {git_info.get('error')}",
                    "git_info": git_info
                }

            # 6. 创建分支（如果不存在）
            branch_result = self.git_manager.create_branch(branch_name)
            if not branch_result.get("success"):
                logger.warning(f"创建分支失败，尝试使用现有分支: {branch_result.get('error')}")

            # 7. 创建Git worktree
            worktree_result = self._create_git_worktree(str(child_worktree_path), branch_name)
            if not worktree_result.get("success"):
                return worktree_result

            # 8. 创建Child配置文件
            self._create_child_config(child_worktree_path, task_id, branch_name)

            # 9. 返回成功结果
            logger.info(f"Child worktree创建成功: {task_id} -> {branch_name}")
            return {
                "success": True,
                "message": f"Child worktree创建成功: {task_id}",
                "worktree_path": str(child_worktree_path),
                "task_id": task_id,
                "branch_name": branch_name,
                "action": "created"
            }

        except Exception as e:
            # 10. 异常处理
            logger.error(f"创建Child worktree异常: {e}")
            return {
                "success": False,
                "error": f"创建失败: {str(e)}"
            }

    def _create_git_worktree(self, worktree_path: str, branch_name: str) -> Dict[str, Any]:
        """
        创建Git worktree

        Args:
            worktree_path: worktree路径
            branch_name: 分支名称

        Returns:
            Dict[str, Any]: 创建结果
        """
        try:
            # 1. 使用git worktree add命令
            cmd = ["worktree", "add", worktree_path, branch_name]
            result = self.git_manager.execute_git_command(cmd)

            if result.returncode == 0:
                logger.info(f"Git worktree创建成功: {worktree_path}")
                return {
                    "success": True,
                    "message": "Git worktree创建成功",
                    "worktree_path": worktree_path,
                    "branch_name": branch_name
                }
            else:
                return {
                    "success": False,
                    "error": f"Git worktree创建失败: {result.stderr}",
                    "returncode": result.returncode
                }

        except Exception as e:
            # 2. 异常处理
            logger.error(f"创建Git worktree异常: {e}")
            return {
                "success": False,
                "error": f"Git worktree创建异常: {str(e)}"
            }

    def _create_child_config(self, worktree_path: Path, task_id: str, branch_name: str) -> None:
        """
        创建Child配置文件

        Args:
            worktree_path: worktree路径
            task_id: 任务ID
            branch_name: 分支名称
        """
        try:
            # 1. 创建.child_config.json文件
            config_file = worktree_path / ".child_config.json"
            config_data = {
                "task_id": task_id,
                "branch_name": branch_name,
                "created_at": datetime.now().isoformat(),
                "worktree_path": str(worktree_path),
                "session_type": "child"
            }

            import json
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)

            logger.info(f"Child配置文件创建: {config_file}")

        except Exception as e:
            # 2. 异常处理（非致命错误）
            logger.warning(f"创建Child配置文件失败: {e}")

    def list_child_worktrees(self) -> Dict[str, Any]:
        """
        列出所有Child worktree

        Returns:
            Dict[str, Any]: worktree列表
        """
        try:
            # 1. 检查worktree目录是否存在
            if not self.worktree_dir.exists():
                return {
                    "success": True,
                    "worktrees": [],
                    "count": 0,
                    "message": "worktree目录不存在"
                }

            # 2. 扫描子目录
            child_worktrees = []
            for child_dir in self.worktree_dir.iterdir():
                if child_dir.is_dir() and child_dir.name != ".git":
                    # 3. 读取配置信息
                    config_file = child_dir / ".child_config.json"
                    config_data = {}

                    if config_file.exists():
                        try:
                            import json
                            with open(config_file, 'r', encoding='utf-8') as f:
                                config_data = json.load(f)
                        except Exception as e:
                            logger.warning(f"读取Child配置失败: {config_file}, {e}")

                    # 4. 构造worktree信息
                    worktree_info = {
                        "task_id": config_data.get("task_id", child_dir.name),
                        "path": str(child_dir),
                        "branch_name": config_data.get("branch_name", "unknown"),
                        "created_at": config_data.get("created_at"),
                        "exists": child_dir.exists()
                    }

                    child_worktrees.append(worktree_info)

            # 5. 按task_id排序
            child_worktrees.sort(key=lambda x: x["task_id"])

            return {
                "success": True,
                "worktrees": child_worktrees,
                "count": len(child_worktrees),
                "worktree_directory": str(self.worktree_dir)
            }

        except Exception as e:
            # 6. 异常处理
            logger.error(f"列出Child worktree异常: {e}")
            return {
                "success": False,
                "error": f"列表获取失败: {str(e)}"
            }

    def cleanup_child_worktree(self, task_id: str) -> Dict[str, Any]:
        """
        清理Child worktree

        Args:
            task_id: 任务ID

        Returns:
            Dict[str, Any]: 清理结果
        """
        try:
            # 1. 参数验证
            if not task_id or not task_id.strip():
                return {
                    "success": False,
                    "error": "task_id不能为空"
                }

            task_id = task_id.strip()
            child_worktree_path = self.worktree_dir / task_id

            # 2. 检查是否存在
            if not child_worktree_path.exists():
                return {
                    "success": True,
                    "message": f"Child worktree不存在: {task_id}",
                    "action": "not_exists"
                }

            # 3. 删除Git worktree
            cmd = ["worktree", "remove", str(child_worktree_path)]
            result = self.git_manager.execute_git_command(cmd)

            if result.returncode == 0:
                logger.info(f"Child worktree清理成功: {task_id}")
                return {
                    "success": True,
                    "message": f"Child worktree清理成功: {task_id}",
                    "task_id": task_id,
                    "action": "removed"
                }
            else:
                return {
                    "success": False,
                    "error": f"Git worktree删除失败: {result.stderr}",
                    "returncode": result.returncode
                }

        except Exception as e:
            # 4. 异常处理
            logger.error(f"清理Child worktree异常: {e}")
            return {
                "success": False,
                "error": f"清理失败: {str(e)}"
            }

    def get_worktree_status(self) -> Dict[str, Any]:
        """
        获取worktree状态

        Returns:
            Dict[str, Any]: 状态信息
        """
        try:
            # 1. 检查主目录状态
            worktree_exists = self.worktree_dir.exists()

            # 2. 获取Child worktree列表
            child_list = self.list_child_worktrees()

            # 3. 检查Master权限
            from .master_detector import is_master_node
            can_manage = is_master_node()

            # 4. 构造状态信息
            status = {
                "success": True,
                "worktree_directory_exists": worktree_exists,
                "worktree_directory_path": str(self.worktree_dir),
                "can_manage_worktrees": can_manage,
                "child_worktrees": child_list.get("worktrees", []),
                "child_count": child_list.get("count", 0),
                "project_root": str(self.project_root),
                "timestamp": datetime.now().isoformat()
            }

            # 5. 添加目录信息
            if worktree_exists:
                stat = self.worktree_dir.stat()
                status.update({
                    "directory_permissions": oct(stat.st_mode)[-3:],
                    "last_modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                })

            return status

        except Exception as e:
            # 6. 异常处理
            logger.error(f"获取worktree状态异常: {e}")
            return {
                "success": False,
                "error": f"状态查询失败: {str(e)}"
            }

    def auto_ensure_worktree_directory(self) -> Dict[str, Any]:
        """
        自动确保worktree目录存在

        在Master节点启动时自动调用，实现PRD要求的自动化。

        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            # 1. 检查是否为Master节点
            from .master_detector import is_master_node
            if not is_master_node():
                return {
                    "success": True,
                    "message": "非Master节点，跳过worktree目录创建",
                    "action": "skipped"
                }

            # 2. 执行确保逻辑
            result = self.ensure_worktree_directory()
            result["action"] = f"auto_{result.get('action', 'unknown')}"

            if result.get("success"):
                logger.info(f"worktree目录自动确保完成: {result.get('action')}")
            else:
                logger.warning(f"worktree目录自动确保失败: {result.get('error')}")

            return result

        except Exception as e:
            # 3. 异常处理
            logger.error(f"自动确保worktree目录异常: {e}")
            return {
                "success": False,
                "error": f"自动处理失败: {str(e)}"
            }


# 全局Worktree自动管理器实例
_worktree_auto_manager = None


def get_worktree_auto_manager(project_root: Optional[str] = None) -> WorktreeAutoManager:
    """
    获取全局Worktree自动管理器实例

    Args:
        project_root: 项目根目录

    Returns:
        WorktreeAutoManager: 管理器实例
    """
    global _worktree_auto_manager

    if _worktree_auto_manager is None:
        _worktree_auto_manager = WorktreeAutoManager(project_root)
        logger.info("创建全局Worktree自动管理器实例")

    return _worktree_auto_manager


def auto_ensure_worktree_directory() -> Dict[str, Any]:
    """
    自动确保worktree目录存在

    在系统初始化时调用，实现PRD要求的自动化。

    Returns:
        Dict[str, Any]: 操作结果
    """
    try:
        # 1. 获取管理器实例
        manager = get_worktree_auto_manager()

        # 2. 执行自动确保逻辑
        result = manager.auto_ensure_worktree_directory()

        # 3. 记录结果
        if result.get("success"):
            logger.info(f"worktree目录自动确保完成: {result.get('action', 'unknown')}")
        else:
            logger.warning(f"worktree目录自动确保失败: {result.get('error')}")

        return result

    except Exception as e:
        # 4. 异常处理
        logger.error(f"自动确保worktree目录异常: {e}")
        return {
            "success": False,
            "error": f"自动处理异常: {str(e)}"
        }