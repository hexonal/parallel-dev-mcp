# -*- coding: utf-8 -*-
"""
Master 会话检测和注册机制

@description 实现Master会话识别、session_id管理和文件锁机制
"""

import fcntl
import json
import logging
import os
import subprocess
import uuid
from pathlib import Path
from typing import Optional, Dict, List
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, timedelta

# 配置日志系统
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class SessionInfo(BaseModel):
    """
    会话信息数据模型

    包含会话ID、类型、创建时间等基本信息
    """

    session_id: str = Field(..., description="会话唯一标识")
    session_type: str = Field(..., description="会话类型：master/child")
    created_at: datetime = Field(..., description="创建时间")
    tmux_session_name: Optional[str] = Field(None, description="tmux会话名称")
    is_active: bool = Field(True, description="是否活跃")

    model_config = ConfigDict(
        # 1. JSON编码器配置
        # json_encoders deprecated in V2 - datetime fields will use default serialization
    )


class MasterSessionDetector:
    """
    Master 会话检测器

    基于tmux会话名称判断当前会话是否为Master会话
    """

    def __init__(self, master_prefix: str = "parallel_master_") -> None:
        """
        初始化Master会话检测器

        Args:
            master_prefix: Master会话名称前缀
        """
        # 1. 设置Master前缀
        self.master_prefix = master_prefix

        # 2. 记录初始化信息
        logger.info(f"Master会话检测器初始化: 前缀={master_prefix}")

    def get_current_tmux_session(self) -> Optional[str]:
        """
        获取当前tmux会话名称

        Returns:
            Optional[str]: 当前会话名称，如果获取失败返回None
        """
        try:
            # 1. 执行tmux命令获取当前会话名称
            result = subprocess.run(
                ["tmux", "display-message", "-p", "#S"],
                capture_output=True,
                text=True,
                timeout=5,
                check=True,
            )

            # 2. 返回会话名称
            session_name = result.stdout.strip()
            logger.debug(f"获取当前tmux会话名称: {session_name}")
            return session_name

        except subprocess.CalledProcessError as e:
            # 3. 处理tmux命令执行错误
            logger.warning(f"获取tmux会话名称失败: {e}")
            return None

        except subprocess.TimeoutExpired:
            # 4. 处理超时
            logger.warning("获取tmux会话名称超时")
            return None

        except Exception as e:
            # 5. 处理其他异常
            logger.error(f"获取tmux会话名称时发生未知错误: {e}")
            return None

    def is_master_session(self, session_name: Optional[str] = None) -> bool:
        """
        检测是否为Master会话

        Args:
            session_name: 会话名称，如果为None则自动获取当前会话

        Returns:
            bool: 是否为Master会话
        """
        # 1. 获取会话名称
        if session_name is None:
            session_name = self.get_current_tmux_session()

        # 2. 检查会话名称是否有效
        if not session_name:
            logger.warning("无法获取会话名称，判断为非Master会话")
            return False

        # 3. 检查前缀匹配
        is_master = session_name.startswith(self.master_prefix)

        # 4. 记录检测结果
        if is_master:
            logger.info(f"检测到Master会话: {session_name}")
        else:
            logger.debug(f"非Master会话: {session_name}")

        # 5. 返回检测结果
        return is_master

    def get_session_type(self, session_name: Optional[str] = None) -> str:
        """
        获取会话类型

        Args:
            session_name: 会话名称

        Returns:
            str: 会话类型 (master/child/unknown)
        """
        # 1. 获取会话名称
        if session_name is None:
            session_name = self.get_current_tmux_session()

        # 2. 检查会话名称
        if not session_name:
            return "unknown"

        # 3. 判断会话类型
        if session_name.startswith(self.master_prefix):
            return "master"
        elif session_name.startswith("parallel_child_"):
            return "child"
        else:
            return "unknown"

    def is_child_session(self, session_name: Optional[str] = None) -> bool:
        """
        检测是否为Child会话

        Args:
            session_name: 会话名称，如果为None则自动获取当前会话

        Returns:
            bool: 是否为Child会话
        """
        # 1. 获取会话名称
        if session_name is None:
            session_name = self.get_current_tmux_session()

        # 2. 检查会话名称是否有效
        if not session_name:
            logger.warning("无法获取会话名称，判断为非Child会话")
            return False

        # 3. 检查前缀匹配
        is_child = session_name.startswith("parallel_child_")

        # 4. 记录检测结果
        if is_child:
            logger.info(f"检测到Child会话: {session_name}")
        else:
            logger.debug(f"非Child会话: {session_name}")

        # 5. 返回检测结果
        return is_child

    def create_child_session(self, project_prefix: str, task_id: str) -> Optional[str]:
        """
        创建Child会话

        Args:
            project_prefix: 项目前缀
            task_id: 任务ID

        Returns:
            Optional[str]: 创建的会话名称，失败时返回None
        """
        # 1. 构建会话名称
        session_name = f"{project_prefix}_child_{task_id}"

        try:
            # 2. 检查会话是否已存在
            if self._check_session_exists(session_name):
                logger.warning(f"会话已存在: {session_name}")
                return None

            # 3. 创建tmux会话
            result = subprocess.run(
                ["tmux", "new-session", "-d", "-s", session_name],
                capture_output=True,
                text=True,
                timeout=10,
                check=True,
            )

            # 4. 验证会话创建成功
            if self._check_session_exists(session_name):
                logger.info(f"Child会话创建成功: {session_name}")
                return session_name
            else:
                logger.error(f"会话创建验证失败: {session_name}")
                return None

        except subprocess.CalledProcessError as e:
            # 5. 处理tmux命令执行错误
            error_msg = e.stderr.strip() if e.stderr else str(e)
            logger.error(f"创建Child会话失败: {session_name}, 错误: {error_msg}")
            return None

        except subprocess.TimeoutExpired:
            # 6. 处理超时
            logger.error(f"创建Child会话超时: {session_name}")
            return None

        except Exception as e:
            # 7. 处理其他异常
            logger.error(f"创建Child会话时发生未知错误: {session_name}, 错误: {e}")
            return None

    def _check_session_exists(self, session_name: str) -> bool:
        """
        检查tmux会话是否存在

        Args:
            session_name: 会话名称

        Returns:
            bool: 会话是否存在
        """
        try:
            # 1. 执行tmux命令检查会话
            result = subprocess.run(
                ["tmux", "has-session", "-t", session_name],
                capture_output=True,
                text=True,
                timeout=5,
            )

            # 2. 返回检查结果
            exists = result.returncode == 0
            logger.debug(f"会话存在性检查: {session_name} -> {exists}")
            return exists

        except subprocess.TimeoutExpired:
            # 3. 处理超时
            logger.warning(f"检查会话存在性超时: {session_name}")
            return False

        except Exception as e:
            # 4. 处理其他异常
            logger.error(f"检查会话存在性时发生异常: {session_name}, 错误: {e}")
            return False

    def kill_child_session(self, session_name: str) -> bool:
        """
        终止Child会话

        Args:
            session_name: 会话名称

        Returns:
            bool: 是否成功终止
        """
        try:
            # 1. 检查会话是否存在
            if not self._check_session_exists(session_name):
                logger.info(f"会话不存在，无需终止: {session_name}")
                return True

            # 2. 执行tmux kill-session命令
            result = subprocess.run(
                ["tmux", "kill-session", "-t", session_name],
                capture_output=True,
                text=True,
                timeout=10,
                check=True,
            )

            # 3. 验证会话是否已终止
            if not self._check_session_exists(session_name):
                logger.info(f"Child会话终止成功: {session_name}")
                return True
            else:
                logger.error(f"会话终止验证失败: {session_name}")
                return False

        except subprocess.CalledProcessError as e:
            # 4. 处理tmux命令执行错误
            error_msg = e.stderr.strip() if e.stderr else str(e)
            logger.error(f"终止Child会话失败: {session_name}, 错误: {error_msg}")
            return False

        except subprocess.TimeoutExpired:
            # 5. 处理超时
            logger.error(f"终止Child会话超时: {session_name}")
            return False

        except Exception as e:
            # 6. 处理其他异常
            logger.error(f"终止Child会话时发生未知错误: {session_name}, 错误: {e}")
            return False


class ChildSessionInfo(BaseModel):
    """
    Child会话信息数据模型

    用于跟踪Child会话的状态和元数据
    """

    task_id: str = Field(..., description="任务ID")
    session_name: str = Field(..., description="tmux会话名称")
    project_prefix: str = Field(..., description="项目前缀")
    status: str = Field("created", description="会话状态: created/active/completed/failed")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    started_at: Optional[datetime] = Field(None, description="启动时间")
    ended_at: Optional[datetime] = Field(None, description="结束时间")
    error_message: Optional[str] = Field(None, description="错误信息")

    model_config = ConfigDict(
        # 1. JSON编码器配置
        # json_encoders deprecated in V2 - datetime fields will use default serialization
    )


class ChildSessionTracker:
    """
    Child会话状态跟踪器

    管理Child会话的生命周期和状态
    """

    def __init__(self, tracking_file: str = "child_sessions.json") -> None:
        """
        初始化Child会话跟踪器

        Args:
            tracking_file: 跟踪文件路径
        """
        # 1. 设置跟踪文件路径
        self.tracking_file = Path(tracking_file)
        self._sessions: Dict[str, ChildSessionInfo] = {}

        # 2. 加载现有会话信息
        self._load_sessions()

        # 3. 记录初始化信息
        logger.info(f"Child会话跟踪器初始化: 文件={self.tracking_file}")

    def create_session_record(
        self,
        task_id: str,
        session_name: str,
        project_prefix: str
    ) -> ChildSessionInfo:
        """
        创建会话记录

        Args:
            task_id: 任务ID
            session_name: 会话名称
            project_prefix: 项目前缀

        Returns:
            ChildSessionInfo: 创建的会话信息
        """
        # 1. 创建会话信息对象
        session_info = ChildSessionInfo(
            task_id=task_id,
            session_name=session_name,
            project_prefix=project_prefix,
            status="created",
            created_at=datetime.now()
        )

        # 2. 添加到跟踪字典
        self._sessions[session_name] = session_info

        # 3. 保存到文件
        self._save_sessions()

        # 4. 记录创建信息
        logger.info(f"Child会话记录创建: {session_name} -> {task_id}")

        # 5. 返回会话信息
        return session_info

    def update_session_status(
        self,
        session_name: str,
        status: str,
        error_message: Optional[str] = None
    ) -> bool:
        """
        更新会话状态

        Args:
            session_name: 会话名称
            status: 新状态
            error_message: 错误信息（可选）

        Returns:
            bool: 更新是否成功
        """
        # 1. 检查会话是否存在
        if session_name not in self._sessions:
            logger.warning(f"尝试更新不存在的会话状态: {session_name}")
            return False

        # 2. 获取会话信息
        session_info = self._sessions[session_name]

        # 3. 更新状态和时间戳
        old_status = session_info.status
        session_info.status = status

        if status == "active" and old_status == "created":
            session_info.started_at = datetime.now()
        elif status in ["completed", "failed"]:
            session_info.ended_at = datetime.now()

        if error_message:
            session_info.error_message = error_message

        # 4. 保存到文件
        self._save_sessions()

        # 5. 记录状态更新
        logger.info(f"Child会话状态更新: {session_name} {old_status} -> {status}")

        # 6. 返回成功状态
        return True

    def get_session_info(self, session_name: str) -> Optional[ChildSessionInfo]:
        """
        获取会话信息

        Args:
            session_name: 会话名称

        Returns:
            Optional[ChildSessionInfo]: 会话信息，不存在时返回None
        """
        # 1. 返回会话信息
        return self._sessions.get(session_name)

    def list_sessions(self, status_filter: Optional[str] = None) -> List[ChildSessionInfo]:
        """
        列出所有会话

        Args:
            status_filter: 状态过滤器

        Returns:
            List[ChildSessionInfo]: 会话信息列表
        """
        # 1. 获取所有会话
        sessions = list(self._sessions.values())

        # 2. 应用状态过滤
        if status_filter:
            sessions = [s for s in sessions if s.status == status_filter]

        # 3. 按创建时间排序
        sessions.sort(key=lambda x: x.created_at, reverse=True)

        # 4. 返回会话列表
        return sessions

    def cleanup_completed_sessions(self, max_age_hours: int = 24) -> int:
        """
        清理已完成的会话记录

        Args:
            max_age_hours: 最大保留时间（小时）

        Returns:
            int: 清理的会话数量
        """
        # 1. 计算过期时间
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        cleaned_count = 0

        # 2. 查找过期的已完成会话
        sessions_to_remove = []
        for session_name, session_info in self._sessions.items():
            if (session_info.status in ["completed", "failed"] and
                session_info.ended_at and
                session_info.ended_at < cutoff_time):
                sessions_to_remove.append(session_name)

        # 3. 删除过期会话
        for session_name in sessions_to_remove:
            del self._sessions[session_name]
            cleaned_count += 1
            logger.info(f"清理过期会话记录: {session_name}")

        # 4. 保存到文件
        if cleaned_count > 0:
            self._save_sessions()

        # 5. 返回清理数量
        return cleaned_count

    def _load_sessions(self) -> None:
        """
        从文件加载会话信息

        内部方法，加载持久化的会话数据
        """
        try:
            # 1. 检查文件是否存在
            if not self.tracking_file.exists():
                logger.debug("跟踪文件不存在，使用空会话列表")
                return

            # 2. 读取文件内容
            with open(self.tracking_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            # 3. 转换为会话信息对象
            for session_name, session_data in data.items():
                session_info = ChildSessionInfo(**session_data)
                self._sessions[session_name] = session_info

            # 4. 记录加载结果
            logger.debug(f"加载了 {len(self._sessions)} 个会话记录")

        except Exception as e:
            # 5. 处理加载失败
            logger.error(f"加载会话跟踪文件失败: {e}")
            self._sessions = {}

    def _save_sessions(self) -> None:
        """
        保存会话信息到文件

        内部方法，持久化会话数据
        """
        try:
            # 1. 转换为JSON格式
            data = {}
            for session_name, session_info in self._sessions.items():
                data[session_name] = session_info.model_dump()

            # 2. 写入文件
            with open(self.tracking_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)

            # 3. 记录保存结果
            logger.debug(f"保存了 {len(self._sessions)} 个会话记录")

        except Exception as e:
            # 4. 处理保存失败
            logger.error(f"保存会话跟踪文件失败: {e}")


class SessionIDManager:
    """
    Session ID 管理器

    处理session_id.txt文件的创建、读取、锁定和生命周期管理
    """

    def __init__(self, session_file_path: str = "session_id.txt") -> None:
        """
        初始化SessionID管理器

        Args:
            session_file_path: session_id文件路径
        """
        # 1. 设置文件路径
        self.session_file = Path(session_file_path)

        # 2. 初始化锁文件路径
        self.lock_file = Path(f"{session_file_path}.lock")

        # 3. 记录初始化信息
        logger.info(f"SessionID管理器初始化: 文件={self.session_file}")

    def _acquire_file_lock(self, lock_file_path: Path) -> Optional[int]:
        """
        获取文件锁

        Args:
            lock_file_path: 锁文件路径

        Returns:
            Optional[int]: 文件描述符，获取失败返回None
        """
        try:
            # 1. 打开锁文件
            lock_fd = os.open(str(lock_file_path), os.O_CREAT | os.O_WRONLY)

            # 2. 尝试获取独占锁
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)

            # 3. 记录成功信息
            logger.debug(f"成功获取文件锁: {lock_file_path}")
            return lock_fd

        except (OSError, IOError) as e:
            # 4. 处理锁获取失败
            logger.warning(f"获取文件锁失败: {lock_file_path} - {e}")
            return None

    def _release_file_lock(self, lock_fd: int) -> None:
        """
        释放文件锁

        Args:
            lock_fd: 文件描述符
        """
        try:
            # 1. 释放锁
            fcntl.flock(lock_fd, fcntl.LOCK_UN)

            # 2. 关闭文件
            os.close(lock_fd)

            # 3. 记录成功信息
            logger.debug("文件锁已释放")

        except Exception as e:
            # 4. 处理释放失败
            logger.error(f"释放文件锁失败: {e}")

    def create_session_id(self, force: bool = False, task_id: Optional[str] = None) -> Optional[str]:
        """
        创建新的session_id

        Args:
            force: 是否强制覆盖已存在的文件
            task_id: 任务ID（Child会话必需）

        Returns:
            Optional[str]: 创建的session_id，失败返回None
        """
        # 1. 检查文件写入权限
        can_write, reason = self.can_write_session_file()

        # 2. 生成session_id
        session_id = str(uuid.uuid4())

        if not can_write:
            # 3. Child会话使用替代存储
            logger.info(f"使用Child会话替代存储: {reason}")

            # 4. 检查task_id是否提供
            if not task_id:
                # 5. 尝试从tmux会话名称提取task_id
                detector = MasterSessionDetector()
                current_session = detector.get_current_tmux_session()
                if current_session and current_session.startswith("parallel_child_"):
                    # 6. 提取task_id: parallel_child_xxx -> xxx
                    task_id = current_session.replace("parallel_child_", "")
                else:
                    logger.error("Child会话创建session_id失败: 缺少task_id参数")
                    return None

            # 7. 创建Child会话存储
            storage_path = self.create_child_session_storage(session_id, task_id)
            if storage_path:
                logger.info(f"Child会话session_id创建成功: {session_id} -> {storage_path}")
                return session_id
            else:
                logger.error("Child会话存储创建失败")
                return None

        # 8. Master会话正常流程
        # 9. 检查是否已存在且不强制覆盖
        if self.session_file.exists() and not force:
            logger.warning("session_id.txt已存在，跳过创建")
            return self.read_session_id()

        # 10. 尝试获取文件锁
        lock_fd = self._acquire_file_lock(self.lock_file)
        if lock_fd is None:
            logger.error("无法获取文件锁，session_id创建失败")
            return None

        try:
            # 11. 原子性写入文件
            temp_file = Path(f"{self.session_file}.tmp")
            with open(temp_file, "w", encoding="utf-8") as f:
                f.write(session_id)
                f.flush()
                os.fsync(f.fileno())

            # 12. 原子性重命名
            temp_file.rename(self.session_file)

            # 13. 记录成功信息
            logger.info(f"Master会话session_id创建成功: {session_id}")

            # 14. 返回session_id
            return session_id

        except Exception as e:
            # 15. 处理创建失败
            logger.error(f"创建session_id失败: {e}")
            return None

        finally:
            # 16. 释放文件锁
            self._release_file_lock(lock_fd)

    def read_session_id(self) -> Optional[str]:
        """
        读取session_id

        Returns:
            Optional[str]: session_id，读取失败返回None
        """
        try:
            # 1. 检查文件是否存在
            if not self.session_file.exists():
                logger.debug("session_id.txt文件不存在")

                # 2. 检查是否为Child会话，尝试从替代存储读取
                detector = MasterSessionDetector()
                current_session = detector.get_current_tmux_session()

                if detector.is_child_session(current_session):
                    # 3. 提取task_id从Child会话名称
                    if current_session and current_session.startswith("parallel_child_"):
                        task_id = current_session.replace("parallel_child_", "")
                        logger.debug(f"Child会话检测到，尝试从替代存储读取: task_id={task_id}")

                        # 4. 从Child会话存储读取
                        child_session_id = self.read_child_session_storage(task_id)
                        if child_session_id:
                            logger.debug(f"从Child会话存储成功读取session_id: {child_session_id}")
                            return child_session_id

                # 5. 所有尝试都失败
                return None

            # 6. 读取主session_id.txt文件内容
            with open(self.session_file, "r", encoding="utf-8") as f:
                session_id = f.read().strip()

            # 7. 验证session_id格式
            if not session_id:
                logger.warning("session_id.txt文件为空")
                return None

            # 8. 记录读取成功
            logger.debug(f"成功读取session_id: {session_id}")

            # 9. 返回session_id
            return session_id

        except Exception as e:
            # 10. 处理读取失败
            logger.error(f"读取session_id失败: {e}")
            return None

    def is_valid_session_id(self, session_id: str) -> bool:
        """
        验证session_id格式

        Args:
            session_id: 待验证的session_id

        Returns:
            bool: 是否有效
        """
        try:
            # 1. 尝试解析为UUID
            uuid.UUID(session_id)

            # 2. 记录验证成功
            logger.debug(f"session_id格式验证通过: {session_id}")
            return True

        except ValueError:
            # 3. 处理格式错误
            logger.warning(f"session_id格式无效: {session_id}")
            return False

    def cleanup_expired_session(self, max_age_hours: int = 24) -> bool:
        """
        清理过期的session文件

        Args:
            max_age_hours: 最大存活时间（小时）

        Returns:
            bool: 是否成功清理
        """
        try:
            # 1. 检查文件是否存在
            if not self.session_file.exists():
                logger.debug("session_id.txt文件不存在，无需清理")
                return True

            # 2. 获取文件修改时间
            file_mtime = datetime.fromtimestamp(self.session_file.stat().st_mtime)

            # 3. 计算过期时间
            expiry_time = datetime.now() - timedelta(hours=max_age_hours)

            # 4. 检查是否过期
            if file_mtime < expiry_time:
                # 5. 删除过期文件
                self.session_file.unlink()
                logger.info(f"已清理过期session文件: {self.session_file}")
                return True
            else:
                # 6. 文件未过期
                logger.debug("session文件未过期，无需清理")
                return True

        except Exception as e:
            # 7. 处理清理失败
            logger.error(f"清理过期session失败: {e}")
            return False

    def get_session_info(self) -> Optional[SessionInfo]:
        """
        获取完整的会话信息

        Returns:
            Optional[SessionInfo]: 会话信息对象
        """
        # 1. 读取session_id
        session_id = self.read_session_id()
        if not session_id:
            return None

        # 2. 获取当前tmux会话名称
        detector = MasterSessionDetector()
        tmux_session = detector.get_current_tmux_session()

        # 3. 获取会话类型
        session_type = detector.get_session_type(tmux_session)

        # 4. 获取文件创建时间
        try:
            if self.session_file.exists():
                created_at = datetime.fromtimestamp(self.session_file.stat().st_ctime)
            else:
                created_at = datetime.now()
        except Exception:
            created_at = datetime.now()

        # 5. 创建SessionInfo对象
        return SessionInfo(
            session_id=session_id,
            session_type=session_type,
            created_at=created_at,
            tmux_session_name=tmux_session,
            is_active=True,
        )

    def can_write_session_file(self) -> tuple[bool, str]:
        """
        检查当前会话是否有权限写入session_id.txt文件

        Returns:
            tuple[bool, str]: (是否允许写入, 原因说明)
        """
        try:
            # 1. 获取当前tmux会话名称
            detector = MasterSessionDetector()
            current_session = detector.get_current_tmux_session()

            # 2. 检查是否为Child会话
            if detector.is_child_session(current_session):
                # 3. Child会话不允许写入session_id.txt
                reason = f"Child会话 {current_session} 禁止写入session_id.txt文件"
                logger.warning(reason)
                return False, reason

            # 4. Master会话允许写入
            reason = f"Master会话 {current_session} 允许写入session_id.txt文件"
            logger.debug(reason)
            return True, reason

        except Exception as e:
            # 5. 出现异常时保守处理，禁止写入
            reason = f"检查会话权限时发生异常: {e}"
            logger.error(reason)
            return False, reason

    def create_child_session_storage(self, session_id: str, task_id: str) -> Optional[Path]:
        """
        为Child会话创建替代存储文件

        Args:
            session_id: 会话ID
            task_id: 任务ID

        Returns:
            Optional[Path]: 创建的存储文件路径，失败时返回None
        """
        try:
            # 1. 创建Child会话存储目录
            storage_dir = Path(".child_sessions")
            storage_dir.mkdir(exist_ok=True)

            # 2. 生成存储文件路径
            storage_file = storage_dir / f"child_session_{task_id}.txt"

            # 3. 写入会话ID到存储文件
            with open(storage_file, "w", encoding="utf-8") as f:
                f.write(session_id)
                f.flush()
                os.fsync(f.fileno())

            # 4. 记录存储成功
            logger.info(f"Child会话存储文件创建成功: {storage_file}")

            # 5. 返回存储文件路径
            return storage_file

        except Exception as e:
            # 6. 处理存储失败
            logger.error(f"创建Child会话存储文件失败: {e}")
            return None

    def read_child_session_storage(self, task_id: str) -> Optional[str]:
        """
        读取Child会话存储文件中的session_id

        Args:
            task_id: 任务ID

        Returns:
            Optional[str]: 会话ID，读取失败时返回None
        """
        try:
            # 1. 构建存储文件路径
            storage_dir = Path(".child_sessions")
            storage_file = storage_dir / f"child_session_{task_id}.txt"

            # 2. 检查文件是否存在
            if not storage_file.exists():
                logger.debug(f"Child会话存储文件不存在: {storage_file}")
                return None

            # 3. 读取会话ID
            with open(storage_file, "r", encoding="utf-8") as f:
                session_id = f.read().strip()

            # 4. 验证会话ID格式
            if not session_id or not self.is_valid_session_id(session_id):
                logger.warning(f"Child会话存储文件中的session_id无效: {session_id}")
                return None

            # 5. 记录读取成功
            logger.debug(f"Child会话存储文件读取成功: {storage_file}")

            # 6. 返回会话ID
            return session_id

        except Exception as e:
            # 7. 处理读取失败
            logger.error(f"读取Child会话存储文件失败: {e}")
            return None

    def cleanup_child_session_storage(self, task_id: str) -> bool:
        """
        清理Child会话存储文件

        Args:
            task_id: 任务ID

        Returns:
            bool: 清理是否成功
        """
        try:
            # 1. 构建存储文件路径
            storage_dir = Path(".child_sessions")
            storage_file = storage_dir / f"child_session_{task_id}.txt"

            # 2. 检查文件是否存在
            if not storage_file.exists():
                logger.debug(f"Child会话存储文件不存在，无需清理: {storage_file}")
                return True

            # 3. 删除存储文件
            storage_file.unlink()

            # 4. 记录清理成功
            logger.info(f"Child会话存储文件清理成功: {storage_file}")

            # 5. 返回成功状态
            return True

        except Exception as e:
            # 6. 处理清理失败
            logger.error(f"清理Child会话存储文件失败: {e}")
            return False


def create_master_session_manager() -> tuple[MasterSessionDetector, SessionIDManager]:
    """
    创建Master会话管理器实例

    Returns:
        tuple: (检测器实例, SessionID管理器实例)
    """
    # 1. 创建检测器实例
    detector = MasterSessionDetector()

    # 2. 创建SessionID管理器实例
    session_manager = SessionIDManager()

    # 3. 记录创建信息
    logger.info("Master会话管理器实例创建成功")

    # 4. 返回实例
    return detector, session_manager


def create_child_session_manager() -> tuple[MasterSessionDetector, ChildSessionTracker]:
    """
    创建Child会话管理器实例

    Returns:
        tuple: (检测器实例, Child会话跟踪器实例)
    """
    # 1. 创建检测器实例
    detector = MasterSessionDetector()

    # 2. 创建Child会话跟踪器实例
    tracker = ChildSessionTracker()

    # 3. 记录创建信息
    logger.info("Child会话管理器实例创建成功")

    # 4. 返回实例
    return detector, tracker


def create_and_track_child_session(
    project_prefix: str,
    task_id: str,
    tracker: Optional[ChildSessionTracker] = None
) -> Optional[str]:
    """
    创建并跟踪Child会话

    Args:
        project_prefix: 项目前缀
        task_id: 任务ID
        tracker: Child会话跟踪器（可选）

    Returns:
        Optional[str]: 创建的会话名称，失败时返回None
    """
    # 1. 创建检测器实例
    detector = MasterSessionDetector()

    # 2. 创建跟踪器实例（如果未提供）
    if tracker is None:
        tracker = ChildSessionTracker()

    # 3. 创建Child会话
    session_name = detector.create_child_session(project_prefix, task_id)

    # 4. 检查创建是否成功
    if session_name is None:
        logger.error(f"Child会话创建失败: {project_prefix}_child_{task_id}")
        return None

    # 5. 创建会话跟踪记录
    session_info = tracker.create_session_record(
        task_id=task_id,
        session_name=session_name,
        project_prefix=project_prefix
    )

    # 6. 更新会话状态为活跃
    tracker.update_session_status(session_name, "active")

    # 7. 记录成功信息
    logger.info(f"Child会话创建并跟踪成功: {session_name}")

    # 8. 返回会话名称
    return session_name


def get_current_session_info() -> Optional[SessionInfo]:
    """
    获取当前会话信息

    Returns:
        Optional[SessionInfo]: 当前会话信息
    """
    # 1. 创建检测器
    detector = MasterSessionDetector()

    # 2. 获取当前会话名称
    session_name = detector.get_current_tmux_session()
    if not session_name:
        return None

    # 3. 获取会话类型
    session_type = detector.get_session_type(session_name)

    # 4. 生成session_id（如果是Master会话，尝试从文件读取）
    session_id = None
    if session_type == "master":
        session_manager = SessionIDManager()
        session_id = session_manager.read_session_id()

    if not session_id:
        session_id = str(uuid.uuid4())

    # 5. 创建SessionInfo对象
    return SessionInfo(
        session_id=session_id,
        session_type=session_type,
        created_at=datetime.now(),
        tmux_session_name=session_name,
        is_active=True
    )


def is_master_session() -> bool:
    """
    检查当前是否为Master会话

    Returns:
        bool: 是否为Master会话
    """
    # 1. 创建检测器
    detector = MasterSessionDetector()

    # 2. 返回检测结果
    return detector.is_master_session()


def is_child_session() -> bool:
    """
    检查当前是否为Child会话

    Returns:
        bool: 是否为Child会话
    """
    # 1. 创建检测器
    detector = MasterSessionDetector()

    # 2. 返回检测结果
    return detector.is_child_session()
