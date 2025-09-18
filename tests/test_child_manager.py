# -*- coding: utf-8 -*-
"""
Child会话管理器测试

测试Child会话清理和等待逻辑
"""

import pytest
import time
import subprocess
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from requests.exceptions import RequestException

import sys
import os
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Import specific module without triggering full package import
import importlib.util
spec = importlib.util.spec_from_file_location(
    "child_manager",
    Path(__file__).parent.parent / "src" / "parallel_dev_mcp" / "session" / "child_manager.py"
)
child_manager = importlib.util.module_from_spec(spec)

# Mock dependencies before loading
sys.modules['parallel_dev_mcp.session.session_manager'] = Mock()
sys.modules['parallel_dev_mcp.session.child_reporter'] = Mock()
sys.modules['parallel_dev_mcp.session.worktree_manager'] = Mock()
sys.modules['parallel_dev_mcp._internal.config_tools'] = Mock()

spec.loader.exec_module(child_manager)

# Import classes from loaded module
ChildSessionManager = child_manager.ChildSessionManager
CleanupConfig = child_manager.CleanupConfig
CleanupResult = child_manager.CleanupResult
CleanupStatus = child_manager.CleanupStatus
SessionState = child_manager.SessionState
create_child_manager = child_manager.create_child_manager
wait_for_cleanup_quick = child_manager.wait_for_cleanup_quick


class TestCleanupConfig:
    """测试清理配置"""

    def test_default_config(self):
        """测试默认配置"""
        # 1. 创建默认配置
        config = CleanupConfig()

        # 2. 验证默认值
        assert config.timeout_seconds == 300
        assert config.poll_interval_seconds == 2.0
        assert config.max_retry_attempts == 3
        assert config.notification_enabled is True
        assert config.worktree_cleanup_enabled is True

    def test_custom_config(self):
        """测试自定义配置"""
        # 1. 创建自定义配置
        config = CleanupConfig(
            timeout_seconds=600,
            poll_interval_seconds=1.5,
            max_retry_attempts=5,
            notification_enabled=False,
            worktree_cleanup_enabled=False
        )

        # 2. 验证自定义值
        assert config.timeout_seconds == 600
        assert config.poll_interval_seconds == 1.5
        assert config.max_retry_attempts == 5
        assert config.notification_enabled is False
        assert config.worktree_cleanup_enabled is False

    def test_config_validation(self):
        """测试配置验证"""
        # 1. 测试有效范围
        config = CleanupConfig(
            timeout_seconds=60,    # 最小值
            poll_interval_seconds=0.5  # 最小值
        )
        assert config.timeout_seconds == 60
        assert config.poll_interval_seconds == 0.5


class TestCleanupResult:
    """测试清理结果"""

    def test_create_cleanup_result(self):
        """测试创建清理结果"""
        # 1. 创建清理结果
        result = CleanupResult(
            task_id="test_task_001",
            session_name="parallel_child_test001",
            status=CleanupStatus.WAITING,
            start_time=datetime.now(),
        )

        # 2. 验证结果
        assert result.task_id == "test_task_001"
        assert result.session_name == "parallel_child_test001"
        assert result.status == CleanupStatus.WAITING
        assert result.polling_count == 0
        assert result.notification_sent is False
        assert result.worktree_cleaned is False

    def test_cleanup_result_with_completion(self):
        """测试完成状态的清理结果"""
        # 1. 创建完成状态的结果
        start_time = datetime.now() - timedelta(minutes=5)
        end_time = datetime.now()

        result = CleanupResult(
            task_id="completed_task",
            session_name="parallel_child_completed",
            status=CleanupStatus.COMPLETED,
            start_time=start_time,
            end_time=end_time,
            duration_seconds=300.5,
            polling_count=25,
            notification_sent=True,
            worktree_cleaned=True
        )

        # 2. 验证完成状态
        assert result.status == CleanupStatus.COMPLETED
        assert result.end_time is not None
        assert result.duration_seconds == 300.5
        assert result.polling_count == 25
        assert result.notification_sent is True
        assert result.worktree_cleaned is True


class TestSessionState:
    """测试会话状态"""

    def test_session_state_values(self):
        """测试会话状态值"""
        # 1. 验证状态值
        assert SessionState.ACTIVE.value == "active"
        assert SessionState.ENDING.value == "ending"
        assert SessionState.CLEANED.value == "cleaned"
        assert SessionState.UNKNOWN.value == "unknown"

    def test_cleanup_status_values(self):
        """测试清理状态值"""
        # 1. 验证清理状态值
        assert CleanupStatus.WAITING.value == "waiting"
        assert CleanupStatus.IN_PROGRESS.value == "in_progress"
        assert CleanupStatus.COMPLETED.value == "completed"
        assert CleanupStatus.TIMEOUT.value == "timeout"
        assert CleanupStatus.FAILED.value == "failed"


class TestChildSessionManager:
    """测试Child会话管理器"""

    @pytest.fixture
    def mock_detector(self):
        """模拟会话检测器"""
        detector = Mock()
        detector.get_current_tmux_session.return_value = "parallel_child_test001"
        detector.is_child_session.return_value = True
        return detector

    @pytest.fixture
    def mock_reporter(self):
        """模拟上报器"""
        reporter = Mock()
        reporter.master_host = "127.0.0.1"
        reporter.master_port = 5001
        reporter.session = Mock()
        return reporter

    @pytest.fixture
    def mock_worktree_manager(self):
        """模拟worktree管理器"""
        manager = Mock()
        manager.remove_worktree.return_value = True
        return manager

    @pytest.fixture
    def manager(self, mock_detector, mock_reporter, mock_worktree_manager):
        """创建测试用的管理器实例"""
        with patch.object(child_manager, "MasterSessionDetector", return_value=mock_detector):
            with patch.object(child_manager, "ChildSessionReporter", return_value=mock_reporter):
                with patch.object(child_manager, "WorktreeManager", return_value=mock_worktree_manager):
                    with patch.object(child_manager, "get_environment_config", return_value=Mock()):
                        return ChildSessionManager()

    def test_manager_initialization(self, manager):
        """测试管理器初始化"""
        # 1. 验证初始化
        assert manager.config is not None
        assert manager.detector is not None
        assert manager.reporter is not None
        assert manager.worktree_manager is not None
        assert manager.cleanup_results == {}

    def test_manager_initialization_with_custom_config(self):
        """测试使用自定义配置的管理器初始化"""
        # 1. 创建自定义配置
        custom_config = CleanupConfig(timeout_seconds=600)

        # 2. 模拟依赖
        with patch.object(child_manager, "MasterSessionDetector"):
            with patch.object(child_manager, "ChildSessionReporter"):
                with patch.object(child_manager, "WorktreeManager"):
                    with patch.object(child_manager, "get_environment_config", return_value=Mock()):
                        manager = ChildSessionManager(custom_config)

        # 3. 验证自定义配置
        assert manager.config.timeout_seconds == 600

    @patch("subprocess.run")
    def test_check_session_state_active(self, mock_subprocess, manager):
        """测试检查活跃会话状态"""
        # 1. 模拟tmux命令成功，会话存在
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "parallel_child_test001\nother_session\n"
        mock_subprocess.return_value = mock_result

        # 2. 检查会话状态
        state = manager._check_session_state("parallel_child_test001")

        # 3. 验证状态
        assert state == SessionState.ACTIVE

    @patch("subprocess.run")
    def test_check_session_state_cleaned(self, mock_subprocess, manager):
        """测试检查已清理会话状态"""
        # 1. 模拟tmux命令成功，会话不存在
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "other_session1\nother_session2\n"
        mock_subprocess.return_value = mock_result

        # 2. 检查会话状态
        state = manager._check_session_state("parallel_child_test001")

        # 3. 验证状态
        assert state == SessionState.CLEANED

    @patch("subprocess.run")
    def test_check_session_state_unknown_error(self, mock_subprocess, manager):
        """测试检查会话状态错误"""
        # 1. 模拟tmux命令失败
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "tmux: no server running"
        mock_subprocess.return_value = mock_result

        # 2. 检查会话状态
        state = manager._check_session_state("parallel_child_test001")

        # 3. 验证状态
        assert state == SessionState.UNKNOWN

    @patch("subprocess.run")
    def test_check_session_state_timeout(self, mock_subprocess, manager):
        """测试检查会话状态超时"""
        # 1. 模拟命令超时
        mock_subprocess.side_effect = subprocess.TimeoutExpired("tmux", 10)

        # 2. 检查会话状态
        state = manager._check_session_state("parallel_child_test001")

        # 3. 验证状态
        assert state == SessionState.UNKNOWN

    def test_send_cleanup_notification_success(self, manager):
        """测试发送清理通知成功"""
        # 1. 准备清理结果
        result = CleanupResult(
            task_id="notification_test",
            session_name="parallel_child_notification",
            status=CleanupStatus.COMPLETED,
            start_time=datetime.now() - timedelta(minutes=5),
            end_time=datetime.now(),
            duration_seconds=300.0,
            polling_count=20
        )

        # 2. 模拟成功响应
        mock_response = Mock()
        mock_response.status_code = 200
        manager.reporter.session.post.return_value = mock_response

        # 3. 发送通知
        success = manager._send_cleanup_notification(result)

        # 4. 验证结果
        assert success is True
        manager.reporter.session.post.assert_called_once()

    def test_send_cleanup_notification_failure(self, manager):
        """测试发送清理通知失败"""
        # 1. 准备清理结果
        result = CleanupResult(
            task_id="notification_failure",
            session_name="parallel_child_failure",
            status=CleanupStatus.FAILED,
            start_time=datetime.now(),
            error_message="Test error"
        )

        # 2. 模拟失败响应
        mock_response = Mock()
        mock_response.status_code = 500
        manager.reporter.session.post.return_value = mock_response

        # 3. 发送通知
        success = manager._send_cleanup_notification(result)

        # 4. 验证结果
        assert success is False

    def test_send_cleanup_notification_exception(self, manager):
        """测试发送清理通知异常"""
        # 1. 准备清理结果
        result = CleanupResult(
            task_id="notification_exception",
            session_name="parallel_child_exception",
            status=CleanupStatus.COMPLETED,
            start_time=datetime.now()
        )

        # 2. 模拟网络异常
        manager.reporter.session.post.side_effect = RequestException("Network error")

        # 3. 发送通知
        success = manager._send_cleanup_notification(result)

        # 4. 验证结果
        assert success is False

    def test_cleanup_worktree_success(self, manager):
        """测试worktree清理成功"""
        # 1. 模拟清理成功
        manager.worktree_manager.remove_worktree.return_value = True

        # 2. 执行清理
        success = manager._cleanup_worktree("test_task")

        # 3. 验证结果
        assert success is True
        manager.worktree_manager.remove_worktree.assert_called_once_with("test_task")

    def test_cleanup_worktree_failure(self, manager):
        """测试worktree清理失败"""
        # 1. 模拟清理失败
        manager.worktree_manager.remove_worktree.return_value = False

        # 2. 执行清理
        success = manager._cleanup_worktree("test_task")

        # 3. 验证结果
        assert success is False

    def test_cleanup_worktree_exception(self, manager):
        """测试worktree清理异常"""
        # 1. 模拟清理异常
        manager.worktree_manager.remove_worktree.side_effect = Exception("Cleanup error")

        # 2. 执行清理
        success = manager._cleanup_worktree("test_task")

        # 3. 验证结果
        assert success is False

    def test_wait_for_cleanup_invalid_session(self, manager):
        """测试等待清理时无效会话"""
        # 1. 模拟无当前会话
        manager.detector.get_current_tmux_session.return_value = None

        # 2. 验证异常
        with pytest.raises(ValueError, match="无法获取当前tmux会话名称"):
            manager.wait_for_cleanup("test_task")

    def test_wait_for_cleanup_not_child_session(self, manager):
        """测试等待清理时非Child会话"""
        # 1. 模拟非Child会话
        manager.detector.is_child_session.return_value = False

        # 2. 验证异常
        with pytest.raises(ValueError, match="当前会话不是Child会话"):
            manager.wait_for_cleanup("test_task")

    @patch("time.sleep")
    @patch("subprocess.run")
    def test_wait_for_cleanup_completed(self, mock_subprocess, mock_sleep, manager):
        """测试等待清理完成"""
        # 1. 模拟第一次检查会话存在，第二次检查会话已清理
        mock_results = [
            Mock(returncode=0, stdout="parallel_child_test001\n"),  # 第一次：会话存在
            Mock(returncode=0, stdout="other_session\n"),  # 第二次：会话已清理
        ]
        mock_subprocess.side_effect = mock_results

        # 2. 执行等待清理
        result = manager.wait_for_cleanup("test_task", timeout=10)

        # 3. 验证结果
        assert result.status == CleanupStatus.COMPLETED
        assert result.task_id == "test_task"
        assert result.session_name == "parallel_child_test001"
        assert result.end_time is not None
        assert result.duration_seconds is not None

    @patch("time.sleep")
    @patch("subprocess.run")
    def test_wait_for_cleanup_timeout(self, mock_subprocess, mock_sleep, manager):
        """测试等待清理超时"""
        # 1. 模拟会话一直存在（不被清理）
        mock_result = Mock(returncode=0, stdout="parallel_child_test001\n")
        mock_subprocess.return_value = mock_result

        # 2. 执行等待清理（短超时）
        result = manager.wait_for_cleanup("timeout_task", timeout=1)

        # 3. 验证超时结果
        assert result.status == CleanupStatus.TIMEOUT
        assert "等待清理超时" in result.error_message
        assert result.end_time is not None

    @patch("subprocess.run")
    def test_force_cleanup(self, mock_subprocess, manager):
        """测试强制清理"""
        # 1. 模拟tmux kill-session成功
        mock_subprocess.return_value = Mock(returncode=0)

        # 2. 模拟依赖函数
        with patch.object(child_manager, "report_session_end_quick") as mock_report:
            mock_report.return_value = True

            # 3. 执行强制清理
            success = manager.force_cleanup("force_task")

        # 4. 验证结果
        assert success is True
        mock_subprocess.assert_called()

    def test_get_cleanup_result(self, manager):
        """测试获取清理结果"""
        # 1. 添加测试结果
        test_result = CleanupResult(
            task_id="get_test",
            session_name="test_session",
            status=CleanupStatus.COMPLETED,
            start_time=datetime.now()
        )
        manager.cleanup_results["get_test"] = test_result

        # 2. 获取结果
        retrieved_result = manager.get_cleanup_result("get_test")

        # 3. 验证结果
        assert retrieved_result is not None
        assert retrieved_result.task_id == "get_test"

        # 4. 获取不存在的结果
        missing_result = manager.get_cleanup_result("missing_task")
        assert missing_result is None

    def test_list_cleanup_results(self, manager):
        """测试列出清理结果"""
        # 1. 添加多个测试结果
        results = []
        for i in range(3):
            result = CleanupResult(
                task_id=f"list_test_{i}",
                session_name=f"test_session_{i}",
                status=CleanupStatus.COMPLETED,
                start_time=datetime.now() - timedelta(minutes=i)
            )
            manager.cleanup_results[f"list_test_{i}"] = result
            results.append(result)

        # 2. 获取结果列表
        result_list = manager.list_cleanup_results()

        # 3. 验证结果
        assert len(result_list) == 3
        # 验证按时间排序（最新的在前）
        assert result_list[0].task_id == "list_test_0"
        assert result_list[2].task_id == "list_test_2"

    def test_cleanup_old_results(self, manager):
        """测试清理过期结果"""
        # 1. 添加新旧结果
        old_result = CleanupResult(
            task_id="old_task",
            session_name="old_session",
            status=CleanupStatus.COMPLETED,
            start_time=datetime.now() - timedelta(hours=25)  # 超过24小时
        )

        new_result = CleanupResult(
            task_id="new_task",
            session_name="new_session",
            status=CleanupStatus.COMPLETED,
            start_time=datetime.now() - timedelta(hours=1)   # 1小时内
        )

        manager.cleanup_results["old_task"] = old_result
        manager.cleanup_results["new_task"] = new_result

        # 2. 清理过期结果
        cleaned_count = manager.cleanup_old_results(max_age_hours=24)

        # 3. 验证清理结果
        assert cleaned_count == 1
        assert "old_task" not in manager.cleanup_results
        assert "new_task" in manager.cleanup_results


class TestFactoryFunctions:
    """测试工厂函数"""

    def test_create_child_manager(self):
        """测试创建Child会话管理器"""
        # 1. 模拟依赖
        with patch.object(child_manager, "MasterSessionDetector"):
            with patch.object(child_manager, "ChildSessionReporter"):
                with patch.object(child_manager, "WorktreeManager"):
                    with patch.object(child_manager, "get_environment_config", return_value=Mock()):
                        # 2. 创建管理器
                        manager = create_child_manager()

        # 3. 验证管理器
        assert manager is not None
        assert isinstance(manager, ChildSessionManager)

    def test_create_child_manager_with_config(self):
        """测试使用配置创建Child会话管理器"""
        # 1. 创建自定义配置
        config = CleanupConfig(timeout_seconds=600)

        # 2. 模拟依赖
        with patch.object(child_manager, "MasterSessionDetector"):
            with patch.object(child_manager, "ChildSessionReporter"):
                with patch.object(child_manager, "WorktreeManager"):
                    with patch.object(child_manager, "get_environment_config", return_value=Mock()):
                        # 3. 创建管理器
                        manager = create_child_manager(config)

        # 4. 验证配置
        assert manager.config.timeout_seconds == 600

    @patch.object(child_manager, "create_child_manager")
    def test_wait_for_cleanup_quick(self, mock_create_manager):
        """测试快速等待清理函数"""
        # 1. 模拟管理器和结果
        mock_result = CleanupResult(
            task_id="quick_test",
            session_name="test_session",
            status=CleanupStatus.COMPLETED,
            start_time=datetime.now()
        )

        mock_manager = Mock()
        mock_manager.wait_for_cleanup.return_value = mock_result
        mock_create_manager.return_value = mock_manager

        # 2. 执行快速等待清理
        result = wait_for_cleanup_quick(
            task_id="quick_test",
            timeout=600,
            enable_notification=False,
            enable_worktree_cleanup=False
        )

        # 3. 验证结果
        assert result.task_id == "quick_test"
        assert result.status == CleanupStatus.COMPLETED

        # 4. 验证配置传递
        call_args = mock_create_manager.call_args[0]
        config = call_args[0]
        assert config.timeout_seconds == 600
        assert config.notification_enabled is False
        assert config.worktree_cleanup_enabled is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])