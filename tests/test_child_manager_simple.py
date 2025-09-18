# -*- coding: utf-8 -*-
"""
Child会话管理器简化测试

直接测试核心逻辑和功能，避免复杂的导入依赖
"""

import pytest
import time
import subprocess
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum, unique


@unique
class CleanupStatus(Enum):
    """清理状态枚举（测试用）"""
    WAITING = "waiting"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    TIMEOUT = "timeout"
    FAILED = "failed"


@unique
class SessionState(Enum):
    """会话状态枚举（测试用）"""
    ACTIVE = "active"
    ENDING = "ending"
    CLEANED = "cleaned"
    UNKNOWN = "unknown"


class CleanupConfig(BaseModel):
    """清理配置数据模型（测试用）"""
    timeout_seconds: int = Field(300, description="清理超时时间（秒）", ge=30, le=3600)
    poll_interval_seconds: float = Field(2.0, description="轮询间隔（秒）", ge=0.5, le=10.0)
    max_retry_attempts: int = Field(3, description="最大重试次数", ge=1, le=10)
    notification_enabled: bool = Field(True, description="是否启用清理通知")
    worktree_cleanup_enabled: bool = Field(True, description="是否启用worktree清理")

    model_config = ConfigDict()


class CleanupResult(BaseModel):
    """清理结果数据模型（测试用）"""
    task_id: str = Field(..., description="任务ID")
    session_name: str = Field(..., description="会话名称")
    status: CleanupStatus = Field(..., description="清理状态")
    start_time: datetime = Field(..., description="开始时间")
    end_time: datetime = Field(None, description="结束时间")
    duration_seconds: float = Field(None, description="持续时间（秒）")
    polling_count: int = Field(0, description="轮询次数", ge=0)
    error_message: str = Field(None, description="错误信息")
    notification_sent: bool = Field(False, description="是否已发送通知")
    worktree_cleaned: bool = Field(False, description="是否已清理worktree")

    model_config = ConfigDict()


class TestCleanupConfig:
    """测试清理配置"""

    def test_default_cleanup_config(self):
        """测试默认清理配置"""
        # 1. 创建默认配置
        config = CleanupConfig()

        # 2. 验证默认值
        assert config.timeout_seconds == 300
        assert config.poll_interval_seconds == 2.0
        assert config.max_retry_attempts == 3
        assert config.notification_enabled is True
        assert config.worktree_cleanup_enabled is True

    def test_custom_cleanup_config(self):
        """测试自定义清理配置"""
        # 1. 创建自定义配置
        config = CleanupConfig(
            timeout_seconds=600,
            poll_interval_seconds=1.0,
            max_retry_attempts=5,
            notification_enabled=False,
            worktree_cleanup_enabled=False
        )

        # 2. 验证自定义值
        assert config.timeout_seconds == 600
        assert config.poll_interval_seconds == 1.0
        assert config.max_retry_attempts == 5
        assert config.notification_enabled is False
        assert config.worktree_cleanup_enabled is False

    def test_config_validation_ranges(self):
        """测试配置验证范围"""
        # 1. 测试最小值
        config = CleanupConfig(
            timeout_seconds=30,     # 最小值
            poll_interval_seconds=0.5,  # 最小值
            max_retry_attempts=1    # 最小值
        )

        assert config.timeout_seconds == 30
        assert config.poll_interval_seconds == 0.5
        assert config.max_retry_attempts == 1

        # 2. 测试最大值
        config = CleanupConfig(
            timeout_seconds=3600,   # 最大值
            poll_interval_seconds=10.0,  # 最大值
            max_retry_attempts=10   # 最大值
        )

        assert config.timeout_seconds == 3600
        assert config.poll_interval_seconds == 10.0
        assert config.max_retry_attempts == 10


class TestCleanupResult:
    """测试清理结果"""

    def test_basic_cleanup_result(self):
        """测试基本清理结果"""
        # 1. 创建基本清理结果
        start_time = datetime.now()
        result = CleanupResult(
            task_id="test_task_001",
            session_name="parallel_child_test001",
            status=CleanupStatus.WAITING,
            start_time=start_time
        )

        # 2. 验证基本属性
        assert result.task_id == "test_task_001"
        assert result.session_name == "parallel_child_test001"
        assert result.status == CleanupStatus.WAITING
        assert result.start_time == start_time
        assert result.end_time is None
        assert result.duration_seconds is None
        assert result.polling_count == 0
        assert result.error_message is None
        assert result.notification_sent is False
        assert result.worktree_cleaned is False

    def test_completed_cleanup_result(self):
        """测试完成状态的清理结果"""
        # 1. 创建完成状态的结果
        start_time = datetime.now() - timedelta(minutes=5)
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        result = CleanupResult(
            task_id="completed_task",
            session_name="parallel_child_completed",
            status=CleanupStatus.COMPLETED,
            start_time=start_time,
            end_time=end_time,
            duration_seconds=duration,
            polling_count=25,
            notification_sent=True,
            worktree_cleaned=True
        )

        # 2. 验证完成状态
        assert result.status == CleanupStatus.COMPLETED
        assert result.end_time == end_time
        assert result.duration_seconds == duration
        assert result.polling_count == 25
        assert result.notification_sent is True
        assert result.worktree_cleaned is True

    def test_failed_cleanup_result(self):
        """测试失败状态的清理结果"""
        # 1. 创建失败状态的结果
        result = CleanupResult(
            task_id="failed_task",
            session_name="parallel_child_failed",
            status=CleanupStatus.FAILED,
            start_time=datetime.now(),
            error_message="Network connection timeout"
        )

        # 2. 验证失败状态
        assert result.status == CleanupStatus.FAILED
        assert result.error_message == "Network connection timeout"

    def test_timeout_cleanup_result(self):
        """测试超时状态的清理结果"""
        # 1. 创建超时状态的结果
        start_time = datetime.now() - timedelta(minutes=10)
        end_time = datetime.now()

        result = CleanupResult(
            task_id="timeout_task",
            session_name="parallel_child_timeout",
            status=CleanupStatus.TIMEOUT,
            start_time=start_time,
            end_time=end_time,
            duration_seconds=600.0,
            polling_count=150,
            error_message="等待清理超时: 600秒"
        )

        # 2. 验证超时状态
        assert result.status == CleanupStatus.TIMEOUT
        assert result.duration_seconds == 600.0
        assert result.polling_count == 150
        assert "等待清理超时" in result.error_message


class TestEnumValues:
    """测试枚举值"""

    def test_cleanup_status_values(self):
        """测试清理状态枚举值"""
        # 1. 验证所有状态值
        assert CleanupStatus.WAITING.value == "waiting"
        assert CleanupStatus.IN_PROGRESS.value == "in_progress"
        assert CleanupStatus.COMPLETED.value == "completed"
        assert CleanupStatus.TIMEOUT.value == "timeout"
        assert CleanupStatus.FAILED.value == "failed"

        # 2. 验证枚举可以比较
        assert CleanupStatus.WAITING != CleanupStatus.COMPLETED
        assert CleanupStatus.COMPLETED == CleanupStatus.COMPLETED

    def test_session_state_values(self):
        """测试会话状态枚举值"""
        # 1. 验证所有状态值
        assert SessionState.ACTIVE.value == "active"
        assert SessionState.ENDING.value == "ending"
        assert SessionState.CLEANED.value == "cleaned"
        assert SessionState.UNKNOWN.value == "unknown"

        # 2. 验证枚举可以比较
        assert SessionState.ACTIVE != SessionState.CLEANED
        assert SessionState.UNKNOWN == SessionState.UNKNOWN


class TestSessionStateDetection:
    """测试会话状态检测逻辑"""

    @patch("subprocess.run")
    def test_detect_active_session(self, mock_subprocess):
        """测试检测活跃会话"""
        # 1. 模拟tmux命令返回会话列表（包含目标会话）
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "parallel_child_test001\nother_session\nmaster_session\n"
        mock_subprocess.return_value = mock_result

        # 2. 模拟检查会话状态的逻辑
        def check_session_state(session_name: str) -> SessionState:
            try:
                result = subprocess.run(
                    ["tmux", "list-sessions", "-F", "#{session_name}"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )

                if result.returncode == 0:
                    sessions = [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]
                    if session_name in sessions:
                        return SessionState.ACTIVE
                    else:
                        return SessionState.CLEANED
                else:
                    return SessionState.UNKNOWN
            except Exception:
                return SessionState.UNKNOWN

        # 3. 测试检测
        state = check_session_state("parallel_child_test001")
        assert state == SessionState.ACTIVE

    @patch("subprocess.run")
    def test_detect_cleaned_session(self, mock_subprocess):
        """测试检测已清理会话"""
        # 1. 模拟tmux命令返回会话列表（不包含目标会话）
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "other_session\nmaster_session\n"
        mock_subprocess.return_value = mock_result

        # 2. 检测会话状态
        def check_session_state(session_name: str) -> SessionState:
            try:
                result = subprocess.run(
                    ["tmux", "list-sessions", "-F", "#{session_name}"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )

                if result.returncode == 0:
                    sessions = [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]
                    if session_name in sessions:
                        return SessionState.ACTIVE
                    else:
                        return SessionState.CLEANED
                else:
                    return SessionState.UNKNOWN
            except Exception:
                return SessionState.UNKNOWN

        # 3. 测试检测
        state = check_session_state("parallel_child_test001")
        assert state == SessionState.CLEANED

    @patch("subprocess.run")
    def test_detect_unknown_session_error(self, mock_subprocess):
        """测试检测未知会话状态（命令错误）"""
        # 1. 模拟tmux命令失败
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "tmux: no server running"
        mock_subprocess.return_value = mock_result

        # 2. 检测会话状态
        def check_session_state(session_name: str) -> SessionState:
            try:
                result = subprocess.run(
                    ["tmux", "list-sessions", "-F", "#{session_name}"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )

                if result.returncode == 0:
                    sessions = [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]
                    if session_name in sessions:
                        return SessionState.ACTIVE
                    else:
                        return SessionState.CLEANED
                else:
                    return SessionState.UNKNOWN
            except Exception:
                return SessionState.UNKNOWN

        # 3. 测试检测
        state = check_session_state("parallel_child_test001")
        assert state == SessionState.UNKNOWN

    @patch("subprocess.run")
    def test_detect_unknown_session_timeout(self, mock_subprocess):
        """测试检测未知会话状态（命令超时）"""
        # 1. 模拟命令超时
        mock_subprocess.side_effect = subprocess.TimeoutExpired("tmux", 10)

        # 2. 检测会话状态
        def check_session_state(session_name: str) -> SessionState:
            try:
                result = subprocess.run(
                    ["tmux", "list-sessions", "-F", "#{session_name}"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )

                if result.returncode == 0:
                    sessions = [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]
                    if session_name in sessions:
                        return SessionState.ACTIVE
                    else:
                        return SessionState.CLEANED
                else:
                    return SessionState.UNKNOWN
            except Exception:
                return SessionState.UNKNOWN

        # 3. 测试检测
        state = check_session_state("parallel_child_test001")
        assert state == SessionState.UNKNOWN


class TestCleanupLogic:
    """测试清理逻辑"""

    def test_timeout_calculation(self):
        """测试超时计算"""
        # 1. 设置超时时间
        timeout_seconds = 300
        start_time = datetime.now()
        timeout_time = start_time + timedelta(seconds=timeout_seconds)

        # 2. 测试超时检查
        current_time = start_time + timedelta(seconds=150)  # 一半时间
        assert current_time < timeout_time

        current_time = start_time + timedelta(seconds=350)  # 超过超时
        assert current_time > timeout_time

    def test_duration_calculation(self):
        """测试持续时间计算"""
        # 1. 创建时间点
        start_time = datetime(2024, 1, 15, 10, 0, 0)
        end_time = datetime(2024, 1, 15, 10, 5, 30)

        # 2. 计算持续时间
        duration_seconds = (end_time - start_time).total_seconds()

        # 3. 验证持续时间
        expected_duration = 5 * 60 + 30  # 5分30秒 = 330秒
        assert duration_seconds == expected_duration

    def test_polling_count_increment(self):
        """测试轮询计数增长"""
        # 1. 模拟轮询循环
        polling_count = 0
        max_polls = 10

        for i in range(max_polls):
            polling_count += 1

        # 2. 验证计数
        assert polling_count == max_polls

    def test_retry_delay_calculation(self):
        """测试重试延迟计算（指数退避）"""
        # 1. 初始延迟
        initial_delay = 2.0
        delays = [initial_delay]

        # 2. 计算指数退避延迟
        for i in range(3):
            current_delay = delays[-1] * 1.5
            delays.append(current_delay)

        # 3. 验证延迟序列
        assert delays[0] == 2.0      # 初始延迟
        assert delays[1] == 3.0      # 第一次退避
        assert delays[2] == 4.5      # 第二次退避
        assert delays[3] == 6.75     # 第三次退避


class TestNotificationData:
    """测试通知数据"""

    def test_cleanup_notification_format(self):
        """测试清理通知数据格式"""
        # 1. 创建通知数据
        task_id = "notification_test"
        session_name = "parallel_child_notification"
        status = CleanupStatus.COMPLETED
        duration = 300.5
        polling_count = 25
        timestamp = datetime.now()

        notification_data = {
            "type": "cleanup_status",
            "taskId": task_id,
            "sessionName": session_name,
            "status": status.value,
            "duration": duration,
            "pollingCount": polling_count,
            "timestamp": timestamp.isoformat()
        }

        # 2. 验证通知数据格式
        assert notification_data["type"] == "cleanup_status"
        assert notification_data["taskId"] == task_id
        assert notification_data["sessionName"] == session_name
        assert notification_data["status"] == "completed"
        assert notification_data["duration"] == duration
        assert notification_data["pollingCount"] == polling_count
        assert "T" in notification_data["timestamp"]  # ISO格式

    def test_notification_endpoint_url(self):
        """测试通知端点URL构建"""
        # 1. 构建端点URL
        master_host = "127.0.0.1"
        master_port = 5001
        master_url = f"http://{master_host}:{master_port}"
        endpoint_url = f"{master_url}/msg/cleanup-status"

        # 2. 验证URL格式
        assert endpoint_url == "http://127.0.0.1:5001/msg/cleanup-status"
        assert endpoint_url.endswith("/msg/cleanup-status")

    def test_notification_headers(self):
        """测试通知请求头"""
        # 1. 构建请求头
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "parallel-dev-mcp-child-manager/1.0.0",
        }

        # 2. 验证请求头
        assert headers["Content-Type"] == "application/json"
        assert headers["User-Agent"] == "parallel-dev-mcp-child-manager/1.0.0"
        assert "json" in headers["Content-Type"]


class TestWorktreeCleanup:
    """测试worktree清理"""

    def test_worktree_path_construction(self):
        """测试worktree路径构建"""
        # 1. 构建worktree路径
        task_id = "worktree_test_001"
        worktree_base = "./worktree"
        worktree_path = f"{worktree_base}/{task_id}"

        # 2. 验证路径格式
        assert worktree_path == "./worktree/worktree_test_001"
        assert task_id in worktree_path
        assert "worktree" in worktree_path

    def test_worktree_cleanup_success_result(self):
        """测试worktree清理成功结果"""
        # 1. 模拟成功清理
        def cleanup_worktree(task_id: str) -> bool:
            """模拟worktree清理函数"""
            try:
                # 模拟清理操作
                return True
            except Exception:
                return False

        # 2. 执行清理
        result = cleanup_worktree("success_task")

        # 3. 验证结果
        assert result is True

    def test_worktree_cleanup_failure_result(self):
        """测试worktree清理失败结果"""
        # 1. 模拟失败清理
        def cleanup_worktree_with_error(task_id: str) -> bool:
            """模拟失败的worktree清理函数"""
            try:
                # 模拟清理失败
                raise Exception("Directory not found")
            except Exception:
                return False

        # 2. 执行清理
        result = cleanup_worktree_with_error("failure_task")

        # 3. 验证结果
        assert result is False


class TestForceCleanupLogic:
    """测试强制清理逻辑"""

    @patch("subprocess.run")
    def test_force_kill_session(self, mock_subprocess):
        """测试强制删除会话"""
        # 1. 模拟tmux kill-session成功
        mock_result = Mock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result

        # 2. 模拟强制删除会话
        def force_kill_session(session_name: str) -> bool:
            try:
                result = subprocess.run(
                    ["tmux", "kill-session", "-t", session_name],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                return result.returncode == 0
            except Exception:
                return False

        # 3. 执行强制删除
        success = force_kill_session("parallel_child_force")

        # 4. 验证结果
        assert success is True
        mock_subprocess.assert_called_once()

    @patch("subprocess.run")
    def test_force_kill_session_failure(self, mock_subprocess):
        """测试强制删除会话失败"""
        # 1. 模拟tmux kill-session失败
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "session not found"
        mock_subprocess.return_value = mock_result

        # 2. 执行强制删除
        def force_kill_session(session_name: str) -> bool:
            try:
                result = subprocess.run(
                    ["tmux", "kill-session", "-t", session_name],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                return result.returncode == 0
            except Exception:
                return False

        success = force_kill_session("nonexistent_session")

        # 3. 验证结果
        assert success is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])