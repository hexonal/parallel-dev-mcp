# -*- coding: utf-8 -*-
"""
Master 会话资源管理器

@description 使用 @mcp.resource 装饰器实现 Master 会话信息的持久化存储
"""

import json
import logging
import subprocess
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict

from ..session.session_manager import SessionIDManager
from ..session.git_manager import GitInfoCollector

# 配置日志系统
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ChildSessionModel(BaseModel):
    """
    子会话信息数据模型

    用于存储子会话的状态和元数据
    """

    task_id: str = Field(..., description="任务ID")
    session_name: str = Field(..., description="tmux会话名称")
    status: str = Field("active", description="会话状态: active, completed, failed")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    last_seen: datetime = Field(
        default_factory=datetime.now, description="最后检测时间"
    )
    worktree_path: Optional[str] = Field(None, description="工作树路径")
    exit_status: Optional[int] = Field(None, description="退出状态码")

    model_config = ConfigDict(
        # 1. JSON编码器配置
        # json_encoders deprecated in V2 - datetime fields will use default serialization
    )


class MasterResourceModel(BaseModel):
    """
    Master 资源数据模型

    用于持久化 Master 会话的完整信息
    """

    session_id: str = Field(..., description="会话唯一标识")
    repo_url: Optional[str] = Field(None, description="Git仓库远程URL")
    current_branch: Optional[str] = Field(None, description="当前分支名称")
    default_branch: Optional[str] = Field(None, description="默认分支名称")
    repository_path: Optional[str] = Field(None, description="仓库根目录路径")
    is_detached_head: bool = Field(False, description="是否处于detached HEAD状态")
    remotes: List[str] = Field(default_factory=list, description="所有远程仓库")
    children: List[ChildSessionModel] = Field(
        default_factory=list, description="子会话清单"
    )
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
    version: int = Field(1, description="资源版本号")

    model_config = ConfigDict(
        # 1. JSON编码器配置
        # json_encoders deprecated in V2 - datetime fields will use default serialization
    )


class MasterResourceManager:
    """
    Master 资源管理器

    负责 Master 会话信息的收集、存储和版本控制
    """

    def __init__(self, resource_file: Optional[Path] = None) -> None:
        """
        初始化资源管理器

        Args:
            resource_file: 资源文件路径，默认为 master_info.json
        """
        # 1. 设置资源文件路径
        self.resource_file = resource_file or Path("master_info.json")

        # 2. 初始化锁对象
        self._lock = threading.RLock()

        # 3. 初始化组件
        self.session_manager = SessionIDManager()
        self.git_collector = GitInfoCollector()

        # 4. 记录初始化信息
        logger.info(f"Master资源管理器初始化: 文件={self.resource_file}")

    def collect_master_info(self) -> MasterResourceModel:
        """
        收集完整的 Master 会话信息

        Returns:
            MasterResourceModel: Master 会话信息模型
        """
        # 1. 获取会话ID
        session_id = self.session_manager.read_session_id()
        if not session_id:
            # 2. 如果没有会话ID，创建新的
            session_id = self.session_manager.create_session_id()
            if not session_id:
                raise RuntimeError("无法创建或获取会话ID")

        # 3. 收集Git仓库信息
        git_info = self.git_collector.collect_repository_info()

        # 4. 获取当前时间
        current_time = datetime.now()

        # 5. 创建Master资源模型
        master_info = MasterResourceModel(
            session_id=session_id,
            repo_url=git_info.remote_url,
            current_branch=git_info.current_branch,
            default_branch=git_info.default_branch,
            repository_path=git_info.repository_path,
            is_detached_head=git_info.is_detached_head,
            remotes=git_info.remotes,
            created_at=current_time,
            updated_at=current_time,
            version=1,
        )

        # 6. 记录收集信息
        logger.info(f"Master会话信息收集完成: {master_info.session_id}")

        # 7. 返回模型
        return master_info

    def load_resource(self) -> Optional[MasterResourceModel]:
        """
        从文件加载资源数据

        Returns:
            Optional[MasterResourceModel]: 加载的资源模型，失败时返回None
        """
        with self._lock:
            try:
                # 1. 检查文件是否存在
                if not self.resource_file.exists():
                    logger.debug(f"资源文件不存在: {self.resource_file}")
                    return None

                # 2. 读取文件内容
                with open(self.resource_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # 3. 创建模型实例
                resource = MasterResourceModel(**data)

                # 4. 记录加载成功
                logger.debug(f"资源加载成功: {resource.session_id}")

                # 5. 返回资源
                return resource

            except Exception as e:
                # 6. 处理加载失败
                logger.error(f"资源加载失败: {e}")
                return None

    def save_resource(self, resource: MasterResourceModel) -> bool:
        """
        保存资源数据到文件

        Args:
            resource: 要保存的资源模型

        Returns:
            bool: 保存是否成功
        """
        with self._lock:
            try:
                # 1. 更新时间和版本
                resource.updated_at = datetime.now()

                # 2. 加载现有资源检查版本冲突
                existing_resource = self.load_resource()
                if existing_resource and existing_resource.version >= resource.version:
                    # 3. 自动增加版本号
                    resource.version = existing_resource.version + 1

                # 4. 创建临时文件
                temp_file = Path(f"{self.resource_file}.tmp")

                # 5. 写入临时文件
                with open(temp_file, "w", encoding="utf-8") as f:
                    json.dump(
                        resource.model_dump(),
                        f,
                        ensure_ascii=False,
                        indent=2,
                        default=str,
                    )

                # 6. 原子性重命名
                temp_file.rename(self.resource_file)

                # 7. 记录保存成功
                logger.info(
                    f"资源保存成功: {resource.session_id}, 版本: {resource.version}"
                )

                # 8. 返回成功状态
                return True

            except Exception as e:
                # 9. 处理保存失败
                logger.error(f"资源保存失败: {e}")
                return False

    def update_resource(self) -> Optional[MasterResourceModel]:
        """
        更新资源信息

        Returns:
            Optional[MasterResourceModel]: 更新后的资源模型
        """
        with self._lock:
            try:
                # 1. 收集最新信息
                new_info = self.collect_master_info()

                # 2. 加载现有资源
                existing_resource = self.load_resource()

                # 3. 处理版本控制
                if existing_resource:
                    # 4. 保留创建时间和版本信息
                    new_info.created_at = existing_resource.created_at
                    new_info.version = existing_resource.version

                # 5. 保存更新后的资源
                if self.save_resource(new_info):
                    logger.info(f"资源更新成功: {new_info.session_id}")
                    return new_info
                else:
                    # 6. 保存失败
                    logger.error("资源更新失败")
                    return None

            except Exception as e:
                # 7. 处理更新失败
                logger.error(f"资源更新异常: {e}")
                return None

    def get_resource_content(self) -> Dict[str, Any]:
        """
        获取资源内容（用于MCP资源暴露）

        Returns:
            Dict[str, Any]: 资源内容字典
        """
        with self._lock:
            # 1. 加载资源
            resource = self.load_resource()

            # 2. 如果没有资源，尝试收集并创建
            if not resource:
                resource = self.collect_master_info()
                self.save_resource(resource)

            # 3. 返回资源字典
            resource_dict = resource.model_dump()

            # 4. 添加元数据
            resource_dict["_metadata"] = {
                "resource_type": "master_session_info",
                "schema_version": "1.0",
                "last_accessed": datetime.now().isoformat(),
            }

            # 5. 记录访问
            logger.debug(f"资源内容访问: {resource.session_id}")

            # 6. 返回内容
            return resource_dict

    def cleanup_expired_resources(self, max_age_hours: int = 168) -> bool:
        """
        清理过期资源（默认7天）

        Args:
            max_age_hours: 最大存活时间（小时）

        Returns:
            bool: 清理是否成功
        """
        with self._lock:
            try:
                # 1. 加载资源
                resource = self.load_resource()
                if not resource:
                    return True

                # 2. 检查是否过期
                age = datetime.now() - resource.created_at
                if age.total_seconds() > max_age_hours * 3600:
                    # 3. 删除过期资源
                    self.resource_file.unlink()
                    logger.info(f"已清理过期资源: {resource.session_id}")
                    return True

                # 4. 资源未过期
                logger.debug("资源未过期，无需清理")
                return True

            except Exception as e:
                # 5. 处理清理失败
                logger.error(f"资源清理失败: {e}")
                return False

    def scan_child_sessions(
        self, project_prefix: str = "parallel"
    ) -> List[ChildSessionModel]:
        """
        扫描所有子会话

        通过tmux list-sessions命令获取所有parallel_child_前缀的会话

        Args:
            project_prefix: 项目前缀

        Returns:
            List[ChildSessionModel]: 检测到的子会话列表
        """
        # 1. 构建子会话前缀
        child_prefix = f"{project_prefix}_child_"
        current_time = datetime.now()
        child_sessions = []

        try:
            # 2. 执行tmux list-sessions命令
            result = subprocess.run(
                ["tmux", "list-sessions", "-F", "#{session_name}"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            # 3. 解析会话列表
            if result.returncode == 0:
                sessions = result.stdout.strip().split("\n")
                for session_name in sessions:
                    if session_name.startswith(child_prefix):
                        # 4. 提取任务ID
                        task_id = session_name[len(child_prefix) :]

                        # 5. 创建子会话模型
                        child_session = ChildSessionModel(
                            task_id=task_id,
                            session_name=session_name,
                            status="active",
                            created_at=current_time,
                            last_seen=current_time,
                        )
                        child_sessions.append(child_session)

                # 6. 记录扫描结果
                logger.info(f"扫描到 {len(child_sessions)} 个子会话")

            else:
                # 7. 处理命令失败（可能没有tmux会话）
                logger.debug("tmux list-sessions失败，可能没有活动会话")

        except subprocess.TimeoutExpired:
            # 8. 处理超时
            logger.warning("tmux list-sessions命令超时")
        except FileNotFoundError:
            # 9. 处理tmux不存在
            logger.warning("tmux命令不存在，无法扫描子会话")
        except Exception as e:
            # 10. 处理其他异常
            logger.error(f"扫描子会话失败: {e}")

        # 11. 返回扫描结果
        return child_sessions

    def update_child_session(
        self,
        task_id: str,
        session_name: str,
        status: str = "active",
        exit_status: Optional[int] = None,
        worktree_path: Optional[str] = None,
    ) -> bool:
        """
        更新或添加子会话信息

        Args:
            task_id: 任务ID
            session_name: 会话名称
            status: 会话状态
            exit_status: 退出状态码
            worktree_path: 工作树路径

        Returns:
            bool: 更新是否成功
        """
        with self._lock:
            try:
                # 1. 加载现有资源
                resource = self.load_resource()
                if not resource:
                    resource = self.collect_master_info()

                # 2. 查找现有子会话
                existing_child = None
                for i, child in enumerate(resource.children):
                    if child.task_id == task_id:
                        existing_child = i
                        break

                # 3. 创建或更新子会话
                current_time = datetime.now()
                if existing_child is not None:
                    # 4. 更新现有子会话
                    child = resource.children[existing_child]
                    child.status = status
                    child.last_seen = current_time
                    if exit_status is not None:
                        child.exit_status = exit_status
                    if worktree_path is not None:
                        child.worktree_path = worktree_path
                else:
                    # 5. 添加新子会话
                    new_child = ChildSessionModel(
                        task_id=task_id,
                        session_name=session_name,
                        status=status,
                        created_at=current_time,
                        last_seen=current_time,
                        exit_status=exit_status,
                        worktree_path=worktree_path,
                    )
                    resource.children.append(new_child)

                # 6. 保存更新后的资源
                success = self.save_resource(resource)
                if success:
                    logger.info(f"子会话状态更新成功: {task_id} -> {status}")
                else:
                    logger.error(f"子会话状态更新失败: {task_id}")

                # 7. 返回更新结果
                return success

            except Exception as e:
                # 8. 处理更新失败
                logger.error(f"子会话更新异常: {e}")
                return False

    def cleanup_completed_sessions(self, project_prefix: str = "parallel") -> int:
        """
        清理已完成的子会话

        使用tmux kill-session清理状态为completed的会话

        Args:
            project_prefix: 项目前缀

        Returns:
            int: 清理的会话数量
        """
        with self._lock:
            try:
                # 1. 加载资源
                resource = self.load_resource()
                if not resource:
                    return 0

                # 2. 查找已完成的会话
                cleaned_count = 0
                updated_children = []

                for child in resource.children:
                    if child.status == "completed":
                        # 3. 尝试清理tmux会话
                        try:
                            subprocess.run(
                                ["tmux", "kill-session", "-t", child.session_name],
                                capture_output=True,
                                timeout=5,
                                check=True,
                            )
                            logger.info(f"已清理会话: {child.session_name}")
                            cleaned_count += 1
                        except subprocess.CalledProcessError as e:
                            # 4. 会话可能已经不存在，仍然从列表中移除
                            if "can't find session" in str(e.stderr).lower():
                                logger.info(
                                    f"会话已不存在，从列表移除: {child.session_name}"
                                )
                                cleaned_count += 1
                            else:
                                # 5. 其他错误，保留在列表中
                                logger.warning(
                                    f"清理会话失败: {child.session_name} - {e}"
                                )
                                updated_children.append(child)
                        except Exception as e:
                            # 6. 其他异常，保留在列表中
                            logger.warning(f"清理会话异常: {child.session_name} - {e}")
                            updated_children.append(child)
                    else:
                        # 7. 非completed状态，保留在列表中
                        updated_children.append(child)

                # 8. 更新子会话列表
                if cleaned_count > 0:
                    resource.children = updated_children
                    self.save_resource(resource)
                    logger.info(f"清理完成，共清理 {cleaned_count} 个会话")

                # 9. 返回清理数量
                return cleaned_count

            except Exception as e:
                # 10. 处理清理失败
                logger.error(f"清理已完成会话异常: {e}")
                return 0

    def refresh_children_list(self, project_prefix: str = "parallel") -> bool:
        """
        刷新子会话清单

        扫描所有活动子会话并更新资源状态

        Args:
            project_prefix: 项目前缀

        Returns:
            bool: 刷新是否成功
        """
        with self._lock:
            try:
                # 1. 扫描活动子会话
                active_sessions = self.scan_child_sessions(project_prefix)

                # 2. 加载现有资源
                resource = self.load_resource()
                if not resource:
                    resource = self.collect_master_info()

                # 3. 创建活动会话映射
                active_task_ids = {session.task_id for session in active_sessions}

                # 4. 更新现有子会话状态
                updated_children = []
                current_time = datetime.now()

                for child in resource.children:
                    if child.task_id in active_task_ids:
                        # 5. 会话仍然活动，更新last_seen
                        child.last_seen = current_time
                        child.status = "active"
                        updated_children.append(child)
                        active_task_ids.remove(child.task_id)
                    elif child.status == "active":
                        # 6. 会话不再活动，标记为completed
                        child.status = "completed"
                        child.last_seen = current_time
                        updated_children.append(child)
                        logger.info(f"子会话已完成: {child.task_id}")
                    else:
                        # 7. 保持其他状态不变
                        updated_children.append(child)

                # 8. 添加新发现的会话
                for session in active_sessions:
                    if session.task_id in active_task_ids:
                        updated_children.append(session)
                        logger.info(f"发现新子会话: {session.task_id}")

                # 9. 更新资源
                resource.children = updated_children
                success = self.save_resource(resource)

                if success:
                    logger.debug(
                        f"子会话清单刷新成功，当前活动会话: {len(active_sessions)}"
                    )
                else:
                    logger.error("子会话清单刷新失败")

                # 10. 返回刷新结果
                return success

            except Exception as e:
                # 11. 处理刷新失败
                logger.error(f"刷新子会话清单异常: {e}")
                return False


# 全局资源管理器实例
master_resource_manager = MasterResourceManager()


def get_master_info_resource() -> Dict[str, Any]:
    """
    获取 Master 会话信息资源（MCP资源接口）

    Returns:
        Dict[str, Any]: Master 会话信息资源内容
    """
    # 1. 使用全局管理器获取资源内容
    return master_resource_manager.get_resource_content()


def update_master_info_resource() -> bool:
    """
    更新 Master 会话信息资源

    Returns:
        bool: 更新是否成功
    """
    # 1. 使用全局管理器更新资源
    result = master_resource_manager.update_resource()

    # 2. 返回更新状态
    return result is not None


def create_master_resource_manager(
    resource_file: Optional[Path] = None,
) -> MasterResourceManager:
    """
    创建 Master 资源管理器实例

    Args:
        resource_file: 资源文件路径

    Returns:
        MasterResourceManager: 配置好的资源管理器实例
    """
    # 1. 创建管理器实例
    manager = MasterResourceManager(resource_file)

    # 2. 记录创建信息
    logger.info("Master资源管理器实例创建成功")

    # 3. 返回管理器实例
    return manager
