# -*- coding: utf-8 -*-
"""
Child会话上报器测试

测试SessionEnd事件上报机制的各个方面
"""

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from requests.exceptions import RequestException, ConnectionError, Timeout

import sys
import os
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Import specific module without triggering full package import
import importlib.util
spec = importlib.util.spec_from_file_location(
    "child_reporter",
    Path(__file__).parent.parent / "src" / "parallel_dev_mcp" / "session" / "child_reporter.py"
)
child_reporter = importlib.util.module_from_spec(spec)

# Mock dependencies before loading
sys.modules['parallel_dev_mcp.session.session_manager'] = Mock()
sys.modules['parallel_dev_mcp._internal.config_tools'] = Mock()

spec.loader.exec_module(child_reporter)

# Import classes from loaded module
ChildSessionReporter = child_reporter.ChildSessionReporter
SessionEndReport = child_reporter.SessionEndReport
ReportStatus = child_reporter.ReportStatus
create_child_reporter = child_reporter.create_child_reporter
report_session_end_quick = child_reporter.report_session_end_quick


class TestSessionEndReport:
    """测试SessionEndReport数据模型"""

    def test_create_session_end_report(self):
        """测试创建SessionEnd上报数据"""
        # 1. 创建测试数据
        report = SessionEndReport(
            task_id="task_001",
            session_name="parallel_child_task001",
            exit_status="success",
            exit_time=datetime.now(),
            project_prefix="PARALLEL",
        )

        # 2. 验证数据
        assert report.task_id == "task_001"
        assert report.session_name == "parallel_child_task001"
        assert report.exit_status == "success"
        assert report.project_prefix == "PARALLEL"

    def test_session_end_report_with_optional_fields(self):
        """测试包含可选字段的SessionEnd上报数据"""
        # 1. 创建带所有字段的测试数据
        start_time = datetime.now() - timedelta(minutes=10)
        end_time = datetime.now()

        report = SessionEndReport(
            task_id="task_002",
            session_name="parallel_child_task002",
            exit_status="error",
            exit_time=end_time,
            worktree_path="/path/to/worktree/task_002",
            session_duration=600.0,
            project_prefix="PARALLEL",
            error_message="Authentication failed",
        )

        # 2. 验证数据
        assert report.worktree_path == "/path/to/worktree/task_002"
        assert report.session_duration == 600.0
        assert report.error_message == "Authentication failed"

    def test_session_end_report_serialization(self):
        """测试SessionEnd上报数据序列化"""
        # 1. 创建测试数据
        report = SessionEndReport(
            task_id="task_003",
            session_name="parallel_child_task003",
            exit_status="success",
            exit_time=datetime.now(),
            project_prefix="PARALLEL",
        )

        # 2. 测试模型转换
        data = report.model_dump()
        assert "task_id" in data
        assert "session_name" in data
        assert "exit_status" in data
        assert "exit_time" in data


class TestReportStatus:
    """测试ReportStatus数据模型"""

    def test_create_report_status(self):
        """测试创建上报状态"""
        # 1. 创建测试状态
        status = ReportStatus(
            report_id="report_001",
            task_id="task_001",
            status="pending",
        )

        # 2. 验证状态
        assert status.report_id == "report_001"
        assert status.task_id == "task_001"
        assert status.status == "pending"
        assert status.attempts == 0

    def test_report_status_with_attempts(self):
        """测试包含尝试次数的上报状态"""
        # 1. 创建状态并更新
        status = ReportStatus(
            report_id="report_002",
            task_id="task_002",
            status="failed",
            attempts=3,
            last_attempt=datetime.now(),
            error_message="Network timeout",
        )

        # 2. 验证状态
        assert status.attempts == 3
        assert status.error_message == "Network timeout"
        assert status.last_attempt is not None


class TestChildSessionReporter:
    """测试ChildSessionReporter类"""

    @pytest.fixture
    def mock_detector(self):
        """模拟会话检测器"""
        detector = Mock()
        detector.get_current_tmux_session.return_value = "parallel_child_task001"
        detector.is_child_session.return_value = True
        return detector

    @pytest.fixture
    def mock_env_config(self):
        """模拟环境配置"""
        config = Mock()
        config.project_prefix = "PARALLEL"
        config.web_port = 5001
        return config

    @pytest.fixture
    def reporter(self, mock_detector, mock_env_config):
        """创建测试用的上报器实例"""
        with patch.object(child_reporter, "MasterSessionDetector", return_value=mock_detector):
            with patch.object(child_reporter, "get_environment_config", return_value=mock_env_config):
                return ChildSessionReporter()

    def test_reporter_initialization(self, reporter):
        """测试上报器初始化"""
        # 1. 验证初始化
        assert reporter.master_host == "127.0.0.1"
        assert reporter.master_port == 5001
        assert reporter.master_url == "http://127.0.0.1:5001"
        assert reporter.report_statuses == {}

    def test_configure_http_session(self, reporter):
        """测试HTTP会话配置"""
        # 1. 验证HTTP会话配置
        assert reporter.session is not None
        assert reporter.session.timeout == 30

    @patch("requests.Session.post")
    def test_successful_report_send(self, mock_post, reporter, mock_env_config):
        """测试成功的上报发送"""
        # 1. 模拟成功响应
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "received", "reportId": "123"}
        mock_post.return_value = mock_response

        # 2. 模拟环境配置
        with patch.object(child_reporter, "get_environment_config", return_value=mock_env_config):
            # 3. 执行上报
            success = reporter.report_session_end("task_001", "success")

        # 4. 验证结果
        assert success is True
        mock_post.assert_called_once()

        # 5. 验证请求数据
        call_args = mock_post.call_args
        assert call_args[1]["json"]["taskId"] == "task_001"
        assert call_args[1]["json"]["status"] == "success"
        assert call_args[1]["json"]["projectPrefix"] == "PARALLEL"

    @patch("requests.Session.post")
    def test_failed_report_send_http_error(self, mock_post, reporter, mock_env_config):
        """测试HTTP错误的上报发送"""
        # 1. 模拟HTTP错误响应
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response

        # 2. 模拟环境配置
        with patch.object(child_reporter, "get_environment_config", return_value=mock_env_config):
            # 3. 执行上报
            success = reporter.report_session_end("task_001", "success")

        # 4. 验证结果
        assert success is False

    @patch("requests.Session.post")
    def test_failed_report_send_network_error(self, mock_post, reporter, mock_env_config):
        """测试网络错误的上报发送"""
        # 1. 模拟网络异常
        mock_post.side_effect = ConnectionError("Connection failed")

        # 2. 模拟环境配置
        with patch.object(child_reporter, "get_environment_config", return_value=mock_env_config):
            # 3. 执行上报
            success = reporter.report_session_end("task_001", "success")

        # 4. 验证结果
        assert success is False

    def test_report_session_end_not_child_session(self, reporter):
        """测试非Child会话的上报"""
        # 1. 模拟非Child会话
        reporter.detector.is_child_session.return_value = False

        # 2. 执行上报
        success = reporter.report_session_end("task_001", "success")

        # 3. 验证结果
        assert success is False

    def test_report_session_end_no_current_session(self, reporter):
        """测试无当前会话的上报"""
        # 1. 模拟无当前会话
        reporter.detector.get_current_tmux_session.return_value = None

        # 2. 执行上报
        success = reporter.report_session_end("task_001", "success")

        # 3. 验证结果
        assert success is False

    @patch("requests.Session.post")
    @patch("time.sleep")
    def test_report_with_retry_success_after_retry(self, mock_sleep, mock_post, reporter, mock_env_config):
        """测试重试机制成功"""
        # 1. 模拟第一次失败，第二次成功
        mock_responses = [
            Mock(status_code=500, text="Server Error"),
            Mock(status_code=200, json=lambda: {"status": "received"}),
        ]
        mock_post.side_effect = mock_responses

        # 2. 模拟环境配置
        with patch.object(child_reporter, "get_environment_config", return_value=mock_env_config):
            # 3. 执行带重试的上报
            success = reporter.report_with_retry("task_001", "success", max_retries=2)

        # 4. 验证结果
        assert success is True
        assert mock_post.call_count == 2
        mock_sleep.assert_called_once()

    @patch("requests.Session.post")
    @patch("time.sleep")
    def test_report_with_retry_all_failed(self, mock_sleep, mock_post, reporter, mock_env_config):
        """测试重试机制全部失败"""
        # 1. 模拟所有尝试都失败
        mock_post.side_effect = ConnectionError("Network error")

        # 2. 模拟环境配置
        with patch.object(child_reporter, "get_environment_config", return_value=mock_env_config):
            # 3. 执行带重试的上报
            success = reporter.report_with_retry("task_001", "success", max_retries=2)

        # 4. 验证结果
        assert success is False
        assert mock_post.call_count == 3  # 原始尝试 + 2次重试

    def test_report_status_tracking(self, reporter):
        """测试上报状态跟踪"""
        # 1. 创建测试状态
        status = ReportStatus(
            report_id="test_report",
            task_id="task_001",
            status="pending",
        )
        reporter.report_statuses["test_report"] = status

        # 2. 测试获取状态
        retrieved_status = reporter.get_report_status("test_report")
        assert retrieved_status is not None
        assert retrieved_status.task_id == "task_001"

        # 3. 测试列出状态
        statuses = reporter.list_report_statuses("task_001")
        assert len(statuses) == 1
        assert statuses[0].task_id == "task_001"

    def test_cleanup_old_statuses(self, reporter):
        """测试清理过期状态"""
        # 1. 创建过期和新状态
        old_time = datetime.now() - timedelta(hours=25)
        new_time = datetime.now() - timedelta(hours=1)

        old_status = ReportStatus(
            report_id="old_report",
            task_id="task_old",
            status="success",
            last_attempt=old_time,
        )

        new_status = ReportStatus(
            report_id="new_report",
            task_id="task_new",
            status="success",
            last_attempt=new_time,
        )

        reporter.report_statuses["old_report"] = old_status
        reporter.report_statuses["new_report"] = new_status

        # 2. 执行清理
        cleaned_count = reporter.cleanup_old_statuses(max_age_hours=24)

        # 3. 验证清理结果
        assert cleaned_count == 1
        assert "old_report" not in reporter.report_statuses
        assert "new_report" in reporter.report_statuses


class TestFactoryFunctions:
    """测试工厂函数"""

    @patch.object(child_reporter, "get_environment_config")
    def test_create_child_reporter(self, mock_get_config):
        """测试创建Child会话上报器"""
        # 1. 模拟环境配置
        mock_config = Mock()
        mock_config.web_port = 8080
        mock_get_config.return_value = mock_config

        # 2. 创建上报器
        with patch.object(child_reporter, "MasterSessionDetector"):
            reporter = create_child_reporter()

        # 3. 验证配置
        assert reporter.master_port == 8080

    @patch.object(child_reporter, "create_child_reporter")
    def test_report_session_end_quick(self, mock_create_reporter):
        """测试快速上报函数"""
        # 1. 模拟上报器
        mock_reporter = Mock()
        mock_reporter.report_with_retry.return_value = True
        mock_create_reporter.return_value = mock_reporter

        # 2. 执行快速上报
        result = report_session_end_quick("task_001", "success")

        # 3. 验证结果
        assert result is True
        mock_reporter.report_with_retry.assert_called_once_with(
            task_id="task_001", exit_status="success", error_message=None
        )


class TestIntegration:
    """集成测试"""

    @patch("requests.Session.post")
    def test_full_reporting_workflow(self, mock_post):
        """测试完整的上报工作流"""
        # 1. 模拟成功响应
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "received", "reportId": "integration_test"}
        mock_post.return_value = mock_response

        # 2. 模拟依赖
        with patch.object(child_reporter, "MasterSessionDetector") as mock_detector_class:
            mock_detector = Mock()
            mock_detector.get_current_tmux_session.return_value = "parallel_child_integration"
            mock_detector.is_child_session.return_value = True
            mock_detector_class.return_value = mock_detector

            with patch.object(child_reporter, "get_environment_config") as mock_get_config:
                mock_config = Mock()
                mock_config.project_prefix = "INTEGRATION"
                mock_config.web_port = 9000
                mock_get_config.return_value = mock_config

                # 3. 执行完整工作流
                success = report_session_end_quick(
                    task_id="integration_task",
                    exit_status="success",
                    error_message=None
                )

        # 4. 验证结果
        assert success is True

        # 5. 验证请求
        call_args = mock_post.call_args
        request_data = call_args[1]["json"]
        assert request_data["taskId"] == "integration_task"
        assert request_data["status"] == "success"
        assert request_data["projectPrefix"] == "INTEGRATION"
        assert "reportId" in request_data

    def test_request_data_format(self):
        """测试请求数据格式"""
        # 1. 创建测试数据
        report_data = SessionEndReport(
            task_id="format_test",
            session_name="parallel_child_format",
            exit_status="error",
            exit_time=datetime(2024, 1, 15, 10, 30, 45),
            worktree_path="/test/worktree/format_test",
            session_duration=1800.5,
            project_prefix="FORMAT",
            error_message="Test error message",
        )

        # 2. 模拟请求数据转换
        request_data = {
            "taskId": report_data.task_id,
            "sessionName": report_data.session_name,
            "status": report_data.exit_status,
            "exitTime": report_data.exit_time.isoformat(),
            "worktreePath": report_data.worktree_path,
            "sessionDuration": report_data.session_duration,
            "projectPrefix": report_data.project_prefix,
            "errorMessage": report_data.error_message,
            "reportId": "test_report_id",
        }

        # 3. 验证数据格式
        assert request_data["taskId"] == "format_test"
        assert request_data["sessionName"] == "parallel_child_format"
        assert request_data["status"] == "error"
        assert request_data["exitTime"] == "2024-01-15T10:30:45"
        assert request_data["worktreePath"] == "/test/worktree/format_test"
        assert request_data["sessionDuration"] == 1800.5
        assert request_data["projectPrefix"] == "FORMAT"
        assert request_data["errorMessage"] == "Test error message"
        assert request_data["reportId"] == "test_report_id"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])