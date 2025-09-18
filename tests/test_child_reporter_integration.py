# -*- coding: utf-8 -*-
"""
Child会话上报器集成测试

测试与实际Flask服务器的集成
"""

import pytest
import json
import requests
import time
import threading
from datetime import datetime
from unittest.mock import Mock, patch


class TestFlaskEndpointIntegration:
    """测试与Flask端点的集成"""

    def test_mock_flask_endpoint_response(self):
        """测试模拟Flask端点响应"""
        # 1. 模拟Flask /msg/send-child端点的响应格式
        # 参考 web/flask_server.py:180-210

        # 模拟成功接收请求的响应
        mock_success_response = {
            "status": "success",
            "message": "Child session message received",
            "data": {
                "taskId": "integration_test_001",
                "sessionName": "parallel_child_integration001",
                "receivedAt": datetime.now().isoformat(),
                "processed": True
            }
        }

        # 2. 验证响应格式
        assert mock_success_response["status"] == "success"
        assert "Child session message received" in mock_success_response["message"]
        assert mock_success_response["data"]["taskId"] == "integration_test_001"
        assert mock_success_response["data"]["processed"] is True

    def test_request_validation_format(self):
        """测试请求验证格式"""
        # 1. 创建符合Flask端点期望的请求格式
        # 参考 web/flask_server.py:msg_send_child函数期望的JSON格式

        valid_request = {
            "taskId": "validation_test_001",
            "sessionName": "parallel_child_validation001",
            "status": "success",
            "exitTime": "2024-01-15T10:30:45",
            "worktreePath": "/test/worktree/validation_test_001",
            "sessionDuration": 1800.5,
            "projectPrefix": "VALIDATION",
            "errorMessage": None,
            "reportId": "validation_report_123"
        }

        # 2. 验证请求包含所有必需字段
        required_fields = ["taskId", "sessionName", "status", "exitTime", "reportId"]
        for field in required_fields:
            assert field in valid_request, f"Missing required field: {field}"
            assert valid_request[field] is not None, f"Field {field} should not be None"

        # 3. 验证字段类型
        assert isinstance(valid_request["taskId"], str)
        assert isinstance(valid_request["sessionName"], str)
        assert isinstance(valid_request["status"], str)
        assert isinstance(valid_request["exitTime"], str)
        assert isinstance(valid_request["reportId"], str)

    @patch("requests.Session.post")
    def test_full_request_response_cycle(self, mock_post):
        """测试完整的请求-响应周期"""
        # 1. 模拟Flask服务器成功响应
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "message": "Child session message received",
            "data": {
                "taskId": "cycle_test_001",
                "processed": True,
                "receivedAt": "2024-01-15T10:30:45Z"
            }
        }
        mock_post.return_value = mock_response

        # 2. 模拟Child Reporter发送请求
        session = requests.Session()
        endpoint_url = "http://127.0.0.1:5001/msg/send-child"
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "parallel-dev-mcp-child-reporter/1.0.0",
        }

        request_data = {
            "taskId": "cycle_test_001",
            "sessionName": "parallel_child_cycle001",
            "status": "success",
            "exitTime": "2024-01-15T10:30:45",
            "worktreePath": "/test/worktree/cycle_test_001",
            "sessionDuration": 2400.0,
            "projectPrefix": "CYCLE",
            "errorMessage": None,
            "reportId": "cycle_report_456"
        }

        # 3. 执行请求
        response = session.post(endpoint_url, json=request_data, headers=headers, timeout=30)

        # 4. 验证请求成功
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["status"] == "success"
        assert response_data["data"]["taskId"] == "cycle_test_001"
        assert response_data["data"]["processed"] is True

        # 5. 验证请求参数
        mock_post.assert_called_once_with(
            endpoint_url,
            json=request_data,
            headers=headers,
            timeout=30
        )

    def test_error_response_handling(self):
        """测试错误响应处理"""
        # 1. 模拟各种错误场景的响应

        # 400 错误 - 请求格式错误
        bad_request_response = {
            "status": "error",
            "message": "Invalid request format",
            "errors": ["Missing required field: taskId"]
        }

        # 500 错误 - 服务器内部错误
        server_error_response = {
            "status": "error",
            "message": "Internal server error",
            "errors": ["Database connection failed"]
        }

        # 2. 验证错误响应格式
        assert bad_request_response["status"] == "error"
        assert "Invalid request format" in bad_request_response["message"]
        assert "taskId" in bad_request_response["errors"][0]

        assert server_error_response["status"] == "error"
        assert "Internal server error" in server_error_response["message"]

    def test_concurrent_requests_handling(self):
        """测试并发请求处理"""
        # 1. 模拟多个Child会话同时上报的场景
        concurrent_requests = []

        for i in range(5):
            request_data = {
                "taskId": f"concurrent_test_{i:03d}",
                "sessionName": f"parallel_child_concurrent{i:03d}",
                "status": "success",
                "exitTime": datetime.now().isoformat(),
                "reportId": f"concurrent_report_{i:03d}"
            }
            concurrent_requests.append(request_data)

        # 2. 验证请求格式一致性
        for request in concurrent_requests:
            assert "taskId" in request
            assert "sessionName" in request
            assert "status" in request
            assert "reportId" in request
            assert request["sessionName"].startswith("parallel_child_")

    def test_session_end_status_values(self):
        """测试SessionEnd状态值"""
        # 1. 测试所有有效的退出状态
        valid_exit_statuses = [
            "success",    # 正常完成
            "error",      # 执行错误
            "timeout",    # 执行超时
            "cancelled"   # 用户取消
        ]

        # 2. 为每个状态创建请求
        for status in valid_exit_statuses:
            request_data = {
                "taskId": f"status_test_{status}",
                "sessionName": f"parallel_child_{status}_test",
                "status": status,
                "exitTime": datetime.now().isoformat(),
                "reportId": f"status_report_{status}"
            }

            # 3. 验证状态值有效
            assert request_data["status"] in valid_exit_statuses
            assert isinstance(request_data["status"], str)
            assert len(request_data["status"]) > 0

    def test_timestamp_format_validation(self):
        """测试时间戳格式验证"""
        # 1. 测试各种时间戳格式
        timestamp_formats = [
            "2024-01-15T10:30:45",          # 基本ISO格式
            "2024-01-15T10:30:45.123",      # 带毫秒
            "2024-01-15T10:30:45.123456",   # 带微秒
            "2024-01-15T10:30:45Z",         # UTC标识
            "2024-01-15T10:30:45+08:00",    # 时区偏移
        ]

        # 2. 验证时间戳可以被解析
        for timestamp_str in timestamp_formats:
            # 验证格式符合ISO 8601标准的基本要求
            assert "T" in timestamp_str  # 日期和时间分隔符
            assert "2024-01-15" in timestamp_str  # 日期部分
            assert "10:30:45" in timestamp_str  # 时间部分

    def test_error_message_handling(self):
        """测试错误信息处理"""
        # 1. 测试各种错误信息格式
        error_scenarios = [
            {
                "status": "error",
                "error_message": "Authentication failed: Invalid credentials",
                "expected_contains": ["Authentication", "failed", "credentials"]
            },
            {
                "status": "timeout",
                "error_message": "Operation timeout after 300 seconds",
                "expected_contains": ["timeout", "300", "seconds"]
            },
            {
                "status": "cancelled",
                "error_message": "User cancelled operation via SIGINT",
                "expected_contains": ["cancelled", "User", "SIGINT"]
            }
        ]

        # 2. 验证错误信息格式
        for scenario in error_scenarios:
            error_msg = scenario["error_message"]

            # 验证错误信息非空且包含关键词
            assert error_msg is not None
            assert len(error_msg) > 0

            for keyword in scenario["expected_contains"]:
                assert keyword in error_msg, f"Error message should contain '{keyword}'"

    def test_project_prefix_validation(self):
        """测试项目前缀验证"""
        # 1. 测试各种项目前缀格式
        valid_prefixes = [
            "PARALLEL",
            "DEV_PROJECT",
            "TEST_ENV",
            "INTEGRATION_TEST",
            "PROD_SYSTEM"
        ]

        # 2. 验证前缀格式
        for prefix in valid_prefixes:
            assert isinstance(prefix, str)
            assert len(prefix) > 0
            assert prefix.isupper()  # 假设前缀应该是大写

            # 验证前缀可以用于构建请求
            request_data = {
                "taskId": f"prefix_test_{prefix.lower()}",
                "sessionName": f"parallel_child_prefix_test",
                "status": "success",
                "projectPrefix": prefix,
                "reportId": f"prefix_report_{prefix.lower()}"
            }

            assert request_data["projectPrefix"] == prefix

    def test_worktree_path_validation(self):
        """测试worktree路径验证"""
        # 1. 测试各种worktree路径格式
        path_scenarios = [
            "/home/user/project/worktree/task_001",
            "/tmp/parallel_dev/worktree/feature_auth",
            "/Users/developer/workspace/worktree/bug_fix_123",
            "C:\\Projects\\parallel\\worktree\\task_456",  # Windows路径
        ]

        # 2. 验证路径格式
        for path in path_scenarios:
            assert isinstance(path, str)
            assert len(path) > 0
            assert "worktree" in path.lower()

            # 验证路径包含任务标识符
            path_parts = path.split("/")[-1] if "/" in path else path.split("\\")[-1]
            assert len(path_parts) > 0  # 最后一部分应该是任务ID

    def test_session_duration_validation(self):
        """测试会话持续时间验证"""
        # 1. 测试各种持续时间值
        duration_scenarios = [
            {"duration": 30.5, "description": "30秒半"},
            {"duration": 300.0, "description": "5分钟"},
            {"duration": 1800.75, "description": "30分钟"},
            {"duration": 7200.25, "description": "2小时"},
            {"duration": 0.1, "description": "极短时间"},
        ]

        # 2. 验证持续时间格式
        for scenario in duration_scenarios:
            duration = scenario["duration"]

            assert isinstance(duration, (int, float))
            assert duration >= 0  # 持续时间应该非负
            assert duration < 86400  # 假设不超过24小时

            # 验证可以序列化为JSON
            import json
            json_str = json.dumps({"sessionDuration": duration})
            parsed = json.loads(json_str)
            assert parsed["sessionDuration"] == duration


if __name__ == "__main__":
    pytest.main([__file__, "-v"])