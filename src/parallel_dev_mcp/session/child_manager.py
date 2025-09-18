# -*- coding: utf-8 -*-
"""
Child会话管理器

@description 实现Child会话清理和等待逻辑，处理会话状态跟踪和清理超时
"""

import time
import logging
import subprocess
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum, unique

from .session_manager import MasterSessionDetector
from .child_reporter import ChildSessionReporter, report_session_end_quick
from .worktree_manager import WorktreeManager
from .._internal.config_tools import get_environment_config

# 配置日志系统
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@unique
class CleanupStatus(Enum):
    """清理状态枚举"""
    WAITING = "waiting"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    TIMEOUT = "timeout"
    FAILED = "failed"


@unique
class SessionState(Enum):
    """会话状态枚举"""
    ACTIVE = "active"
    ENDING = "ending"
    CLEANED = "cleaned"
    UNKNOWN = "unknown"


class CleanupConfig(BaseModel):
    """清理配置数据模型"""

    timeout_seconds: int = Field(300, description="清理超时时间（秒）", ge=30, le=3600)
    poll_interval_seconds: float = Field(2.0, description="轮询间隔（秒）", ge=0.5, le=10.0)
    max_retry_attempts: int = Field(3, description="最大重试次数", ge=1, le=10)
    notification_enabled: bool = Field(True, description="是否启用清理通知")
    worktree_cleanup_enabled: bool = Field(True, description="是否启用worktree清理")

    model_config = ConfigDict()


class CleanupResult(BaseModel):
    """清理结果数据模型"""

    task_id: str = Field(..., description="任务ID")
    session_name: str = Field(..., description="会话名称")
    status: CleanupStatus = Field(..., description="清理状态")
    start_time: datetime = Field(..., description="开始时间")
    end_time: Optional[datetime] = Field(None, description="结束时间")
    duration_seconds: Optional[float] = Field(None, description="持续时间（秒）")
    polling_count: int = Field(0, description="轮询次数", ge=0)
    error_message: Optional[str] = Field(None, description="错误信息")
    notification_sent: bool = Field(False, description="是否已发送通知")
    worktree_cleaned: bool = Field(False, description="是否已清理worktree")

    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()}
    )


class ChildSessionManager:
    """
    Child会话管理器

    负责Child会话的清理等待逻辑和状态跟踪
    """

    def __init__(self, config: Optional[CleanupConfig] = None) -> None:
        """
        初始化Child会话管理器

        Args:
            config: 清理配置，使用默认配置如果未提供
        """
        # 1. 设置清理配置
        self.config = config or CleanupConfig()

        # 2. 初始化组件
        self.detector = MasterSessionDetector()
        self.reporter = ChildSessionReporter()
        self.worktree_manager = WorktreeManager()

        # 3. 初始化状态跟踪
        self.cleanup_results: Dict[str, CleanupResult] = {}

        # 4. 获取环境配置
        try:
            self.env_config = get_environment_config()
        except Exception as e:
            logger.warning(f"获取环境配置失败，使用默认配置: {e}")
            self.env_config = None

        # 5. 记录初始化信息
        logger.info("Child会话管理器初始化完成")

    def wait_for_cleanup(
        self,
        task_id: str,
        timeout: Optional[int] = None,
        custom_config: Optional[CleanupConfig] = None
    ) -> CleanupResult:
        """
        等待Master删除tmux会话

        Args:
            task_id: 任务ID
            timeout: 自定义超时时间（秒），覆盖配置中的默认值
            custom_config: 自定义清理配置

        Returns:
            CleanupResult: 清理结果
        """
        # 1. 准备清理配置
        config = custom_config or self.config
        timeout_seconds = timeout or config.timeout_seconds

        # 2. 获取当前会话信息
        current_session = self.detector.get_current_tmux_session()
        if not current_session:
            raise ValueError("无法获取当前tmux会话名称")

        # 3. 验证是否为Child会话
        if not self.detector.is_child_session(current_session):
            raise ValueError(f"当前会话不是Child会话: {current_session}")

        # 4. 创建清理结果跟踪
        result = CleanupResult(
            task_id=task_id,
            session_name=current_session,
            status=CleanupStatus.WAITING,
            start_time=datetime.now()
        )

        try:
            # 5. 记录开始等待
            logger.info(f"开始等待Child会话清理: {current_session}, 超时: {timeout_seconds}秒")

            # 6. 执行等待循环
            result = self._wait_loop(result, timeout_seconds, config)

            # 7. 执行清理后处理
            result = self._post_cleanup_processing(result, config)

            # 8. 记录清理结果
            self.cleanup_results[task_id] = result

            # 9. 记录完成信息
            logger.info(f"Child会话清理完成: {task_id}, 状态: {result.status.value}")

            # 10. 返回清理结果
            return result

        except Exception as e:
            # 11. 处理清理异常
            result.status = CleanupStatus.FAILED
            result.end_time = datetime.now()
            result.error_message = str(e)

            logger.error(f"Child会话清理异常: {e}")
            self.cleanup_results[task_id] = result

            # 12. 返回失败结果
            return result

    def _wait_loop(
        self,
        result: CleanupResult,
        timeout_seconds: int,
        config: CleanupConfig
    ) -> CleanupResult:
        """
        执行等待循环

        Args:
            result: 清理结果对象
            timeout_seconds: 超时时间
            config: 清理配置

        Returns:
            CleanupResult: 更新后的清理结果
        """
        # 1. 计算超时时间点
        timeout_time = datetime.now() + timedelta(seconds=timeout_seconds)

        # 2. 开始轮询循环
        while datetime.now() < timeout_time:
            try:
                # 3. 检查会话状态
                session_state = self._check_session_state(result.session_name)
                result.polling_count += 1

                # 4. 根据状态处理
                if session_state == SessionState.CLEANED:
                    # 会话已被清理
                    result.status = CleanupStatus.COMPLETED
                    result.end_time = datetime.now()
                    logger.info(f"检测到会话已被清理: {result.session_name}")
                    break

                elif session_state == SessionState.UNKNOWN:
                    # 会话状态未知，可能已被删除
                    logger.warning(f"会话状态未知: {result.session_name}")

                # 5. 等待下一次轮询
                time.sleep(config.poll_interval_seconds)

                # 6. 记录轮询进度
                if result.polling_count % 10 == 0:
                    remaining_time = (timeout_time - datetime.now()).total_seconds()
                    logger.info(f"等待清理中... 轮询次数: {result.polling_count}, 剩余时间: {remaining_time:.1f}秒")

            except Exception as e:
                # 7. 处理轮询异常
                logger.error(f"轮询异常: {e}")
                time.sleep(config.poll_interval_seconds)

        # 8. 检查是否超时
        if result.status == CleanupStatus.WAITING:
            result.status = CleanupStatus.TIMEOUT
            result.end_time = datetime.now()
            result.error_message = f"等待清理超时: {timeout_seconds}秒"
            logger.warning(f"Child会话清理超时: {result.session_name}")

        # 9. 计算持续时间
        if result.end_time:
            result.duration_seconds = (result.end_time - result.start_time).total_seconds()

        # 10. 返回更新后的结果
        return result

    def _check_session_state(self, session_name: str) -> SessionState:
        """
        检查tmux会话状态

        Args:
            session_name: 会话名称

        Returns:
            SessionState: 会话状态
        """
        try:
            # 1. 执行tmux list-sessions命令
            result = subprocess.run(
                ["tmux", "list-sessions", "-F", "#{session_name}"],
                capture_output=True,
                text=True,
                timeout=10
            )

            # 2. 解析输出
            if result.returncode == 0:
                # 获取会话列表
                sessions = [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]

                # 3. 检查目标会话是否存在
                if session_name in sessions:
                    return SessionState.ACTIVE
                else:
                    return SessionState.CLEANED

            else:
                # 4. tmux命令失败
                logger.warning(f"tmux list-sessions失败: {result.stderr}")
                return SessionState.UNKNOWN

        except subprocess.TimeoutExpired:
            # 5. 处理命令超时
            logger.error("tmux list-sessions命令超时")
            return SessionState.UNKNOWN

        except Exception as e:
            # 6. 处理其他异常
            logger.error(f"检查会话状态异常: {e}")
            return SessionState.UNKNOWN

    def _post_cleanup_processing(
        self,
        result: CleanupResult,
        config: CleanupConfig
    ) -> CleanupResult:
        """
        执行清理后处理

        Args:
            result: 清理结果
            config: 清理配置

        Returns:
            CleanupResult: 更新后的清理结果
        """
        try:
            # 1. 发送清理状态通知
            if config.notification_enabled:
                result.notification_sent = self._send_cleanup_notification(result)

            # 2. 清理worktree
            if config.worktree_cleanup_enabled:
                result.worktree_cleaned = self._cleanup_worktree(result.task_id)

            # 3. 记录后处理完成
            logger.info(f"清理后处理完成: 通知={result.notification_sent}, worktree={result.worktree_cleaned}")

        except Exception as e:
            # 4. 处理后处理异常
            logger.error(f"清理后处理异常: {e}")
            if not result.error_message:
                result.error_message = f"清理后处理异常: {e}"

        # 5. 返回更新后的结果
        return result

    def _send_cleanup_notification(self, result: CleanupResult) -> bool:
        """
        发送清理状态通知到Master

        Args:
            result: 清理结果

        Returns:
            bool: 通知是否发送成功
        """
        try:
            # 1. 准备通知数据
            notification_data = {
                "type": "cleanup_status",
                "taskId": result.task_id,
                "sessionName": result.session_name,
                "status": result.status.value,
                "duration": result.duration_seconds,
                "pollingCount": result.polling_count,
                "timestamp": result.end_time.isoformat() if result.end_time else datetime.now().isoformat()
            }

            # 2. 构建请求
            master_url = f"http://{self.reporter.master_host}:{self.reporter.master_port}"
            endpoint_url = f"{master_url}/msg/cleanup-status"

            # 3. 发送通知请求
            response = self.reporter.session.post(
                endpoint_url,
                json=notification_data,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "parallel-dev-mcp-child-manager/1.0.0",
                },
                timeout=30
            )

            # 4. 检查响应状态
            if response.status_code == 200:
                logger.info(f"清理状态通知发送成功: {result.task_id}")
                return True
            else:
                logger.error(f"清理状态通知发送失败: {response.status_code}")
                return False

        except Exception as e:
            # 5. 处理通知发送异常
            logger.error(f"发送清理状态通知异常: {e}")
            return False

    def _cleanup_worktree(self, task_id: str) -> bool:
        """
        清理worktree目录

        Args:
            task_id: 任务ID

        Returns:
            bool: 清理是否成功
        """
        try:
            # 1. 执行worktree清理
            success = self.worktree_manager.remove_worktree(task_id)

            # 2. 记录清理结果
            if success:
                logger.info(f"Worktree清理成功: {task_id}")
            else:
                logger.warning(f"Worktree清理失败: {task_id}")

            # 3. 返回清理结果
            return success

        except Exception as e:
            # 4. 处理清理异常
            logger.error(f"Worktree清理异常: {e}")
            return False

    def force_cleanup(self, task_id: str) -> bool:
        """
        强制清理Child会话（超时情况下使用）

        Args:
            task_id: 任务ID

        Returns:
            bool: 强制清理是否成功
        """
        try:
            # 1. 获取会话名称
            current_session = self.detector.get_current_tmux_session()
            if not current_session:
                logger.error("无法获取当前会话名称进行强制清理")
                return False

            # 2. 记录强制清理
            logger.warning(f"执行强制清理: {current_session}")

            # 3. 发送SessionEnd上报
            try:
                report_session_end_quick(
                    task_id=task_id,
                    exit_status="timeout",
                    error_message="Child会话清理超时，执行强制清理"
                )
            except Exception as e:
                logger.error(f"强制清理时SessionEnd上报失败: {e}")

            # 4. 清理worktree
            try:
                self._cleanup_worktree(task_id)
            except Exception as e:
                logger.error(f"强制清理时worktree清理失败: {e}")

            # 5. 强制退出当前会话
            try:
                subprocess.run(
                    ["tmux", "kill-session", "-t", current_session],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                logger.info(f"强制删除会话成功: {current_session}")
            except Exception as e:
                logger.error(f"强制删除会话失败: {e}")

            # 6. 返回成功（尽力而为）
            return True

        except Exception as e:
            # 7. 处理强制清理异常
            logger.error(f"强制清理异常: {e}")
            return False

    def get_cleanup_result(self, task_id: str) -> Optional[CleanupResult]:
        """
        获取清理结果

        Args:
            task_id: 任务ID

        Returns:
            Optional[CleanupResult]: 清理结果，不存在时返回None
        """
        # 1. 返回清理结果
        return self.cleanup_results.get(task_id)

    def list_cleanup_results(self) -> List[CleanupResult]:
        """
        列出所有清理结果

        Returns:
            List[CleanupResult]: 清理结果列表
        """
        # 1. 获取所有结果
        results = list(self.cleanup_results.values())

        # 2. 按开始时间排序
        results.sort(key=lambda x: x.start_time, reverse=True)

        # 3. 返回结果列表
        return results

    def cleanup_old_results(self, max_age_hours: int = 24) -> int:
        """
        清理过期的清理结果记录

        Args:
            max_age_hours: 最大保留时间（小时）

        Returns:
            int: 清理的记录数量
        """
        # 1. 计算过期时间
        expiry_time = datetime.now() - timedelta(hours=max_age_hours)

        # 2. 找出过期记录
        expired_task_ids = []
        for task_id, result in self.cleanup_results.items():
            if result.start_time < expiry_time:
                expired_task_ids.append(task_id)

        # 3. 删除过期记录
        for task_id in expired_task_ids:
            del self.cleanup_results[task_id]

        # 4. 记录清理结果
        if expired_task_ids:
            logger.info(f"清理过期清理结果记录: {len(expired_task_ids)} 条")

        # 5. 返回清理数量
        return len(expired_task_ids)


def create_child_manager(config: Optional[CleanupConfig] = None) -> ChildSessionManager:
    """
    创建Child会话管理器实例

    Args:
        config: 清理配置

    Returns:
        ChildSessionManager: 配置好的管理器实例
    """
    # 1. 创建管理器实例
    manager = ChildSessionManager(config)

    # 2. 记录创建信息
    logger.info("Child会话管理器实例创建成功")

    # 3. 返回管理器实例
    return manager


def wait_for_cleanup_quick(
    task_id: str,
    timeout: int = 300,
    enable_notification: bool = True,
    enable_worktree_cleanup: bool = True
) -> CleanupResult:
    """
    快速等待清理的便捷函数

    Args:
        task_id: 任务ID
        timeout: 超时时间（秒）
        enable_notification: 是否启用通知
        enable_worktree_cleanup: 是否启用worktree清理

    Returns:
        CleanupResult: 清理结果
    """
    # 1. 创建自定义配置
    config = CleanupConfig(
        timeout_seconds=timeout,
        notification_enabled=enable_notification,
        worktree_cleanup_enabled=enable_worktree_cleanup
    )

    # 2. 创建管理器
    manager = create_child_manager(config)

    # 3. 执行等待清理
    return manager.wait_for_cleanup(task_id)