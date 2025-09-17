# -*- coding: utf-8 -*-
"""
Master 会话检测和注册机制

@description 实现Master会话识别、session_id管理和文件锁机制
"""

import fcntl
import logging
import os
import subprocess
import uuid
from pathlib import Path
from typing import Optional
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
        json_encoders={datetime: lambda v: v.isoformat()}
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

    def create_session_id(self, force: bool = False) -> Optional[str]:
        """
        创建新的session_id

        Args:
            force: 是否强制覆盖已存在的文件

        Returns:
            Optional[str]: 创建的session_id，失败返回None
        """
        # 1. 检查是否已存在且不强制覆盖
        if self.session_file.exists() and not force:
            logger.warning("session_id.txt已存在，跳过创建")
            return self.read_session_id()

        # 2. 尝试获取文件锁
        lock_fd = self._acquire_file_lock(self.lock_file)
        if lock_fd is None:
            logger.error("无法获取文件锁，session_id创建失败")
            return None

        try:
            # 3. 生成唯一session_id
            session_id = str(uuid.uuid4())

            # 4. 原子性写入文件
            temp_file = Path(f"{self.session_file}.tmp")
            with open(temp_file, "w", encoding="utf-8") as f:
                f.write(session_id)
                f.flush()
                os.fsync(f.fileno())

            # 5. 原子性重命名
            temp_file.rename(self.session_file)

            # 6. 记录成功信息
            logger.info(f"成功创建session_id: {session_id}")

            # 7. 返回session_id
            return session_id

        except Exception as e:
            # 8. 处理创建失败
            logger.error(f"创建session_id失败: {e}")
            return None

        finally:
            # 9. 释放文件锁
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
                return None

            # 2. 读取文件内容
            with open(self.session_file, "r", encoding="utf-8") as f:
                session_id = f.read().strip()

            # 3. 验证session_id格式
            if not session_id:
                logger.warning("session_id.txt文件为空")
                return None

            # 4. 记录读取成功
            logger.debug(f"成功读取session_id: {session_id}")

            # 5. 返回session_id
            return session_id

        except Exception as e:
            # 6. 处理读取失败
            logger.error(f"读取session_id失败: {e}")
            return None

    def validate_session_id(self, session_id: str) -> bool:
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
