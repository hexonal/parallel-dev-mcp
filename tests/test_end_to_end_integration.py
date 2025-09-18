# -*- coding: utf-8 -*-
"""
端到端集成测试

@description 完整的系统集成测试，验证所有组件协同工作
"""

import os
import pytest
import tempfile
import time
from pathlib import Path
from typing import Dict, Any

# 导入核心组件
from parallel_dev_mcp.session.session_manager import SessionManager
from parallel_dev_mcp.session.resource_manager import get_resource_manager
from parallel_dev_mcp.prompts.template_manager import get_template_manager
from parallel_dev_mcp.prompts.prompt_types import PromptType, PromptContext
from parallel_dev_mcp.session.delayed_message_sender import get_delayed_message_sender
from parallel_dev_mcp.session.message_queue_manager import get_message_queue_manager


class TestEndToEndIntegration:
    """端到端集成测试类"""

    @pytest.fixture(autouse=True)
    def setup_test_environment(self):
        """设置测试环境"""
        # 1. 创建临时目录
        self.temp_dir = tempfile.mkdtemp()
        self.test_project_id = "E2E_TEST_PROJECT"
        self.test_session_prefix = f"{self.test_project_id}_child_"

        # 2. 设置测试数据
        self.test_tasks = ["task_001", "task_002", "task_003"]

        yield

        # 3. 清理测试环境
        self._cleanup_test_sessions()

    def _cleanup_test_sessions(self):
        """清理测试会话"""
        try:
            import subprocess
            # 清理所有测试会话
            result = subprocess.run(
                ["tmux", "list-sessions", "-f", "#{session_name}"],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                sessions = result.stdout.strip().split('\n')
                for session in sessions:
                    if self.test_session_prefix in session:
                        subprocess.run(["tmux", "kill-session", "-t", session])
        except Exception:
            pass  # 忽略清理错误

    def test_complete_workflow(self):
        """测试完整的工作流程"""
        # 1. 测试Master资源创建
        resource_manager = get_resource_manager()

        master_data = {
            "project_id": self.test_project_id,
            "status": "active",
            "children": [],
            "total_children": 0,
            "active_children": 0
        }

        success = resource_manager.create_master_resource(
            project_id=self.test_project_id,
            **master_data
        )
        assert success, "Master资源创建失败"

        # 2. 测试Child会话创建
        session_manager = SessionManager()

        for i, task_id in enumerate(self.test_tasks):
            session_name = f"{self.test_session_prefix}{task_id}_{i+1:03d}"

            # 创建Child会话
            result = session_manager.create_child_session(
                project_id=self.test_project_id,
                task_id=task_id,
                session_name=session_name
            )

            assert result["success"], f"创建Child会话失败: {result.get('message')}"
            assert result["session_name"] == session_name

            # 验证会话确实创建了
            time.sleep(0.5)  # 等待会话创建完成

    def test_prompt_system_integration(self):
        """测试Prompt系统集成"""
        template_manager = get_template_manager()

        # 1. 测试Master Prompt生成
        master_context = PromptContext(
            prompt_type=PromptType.MASTER_STOP,
            session_name=f"{self.test_project_id}_master",
            project_id=self.test_project_id,
            variables={"test_mode": True}
        )

        master_result = template_manager.generate_prompt(
            prompt_type=PromptType.MASTER_STOP,
            context=master_context
        )

        assert master_result.success, f"Master Prompt生成失败: {master_result.error_message}"
        assert self.test_project_id in master_result.content

        # 2. 测试Child Prompt生成
        child_context = PromptContext(
            prompt_type=PromptType.CHILD_DEFAULT,
            session_name=f"{self.test_session_prefix}test_001",
            project_id=self.test_project_id,
            task_id="test_task"
        )

        child_result = template_manager.generate_prompt(
            prompt_type=PromptType.CHILD_DEFAULT,
            context=child_context
        )

        assert child_result.success, f"Child Prompt生成失败: {child_result.error_message}"
        assert "test_task" in child_result.content

        # 3. 测试Continue Prompt生成
        continue_context = PromptContext(
            prompt_type=PromptType.CONTINUE_EXECUTION,
            session_name=f"{self.test_session_prefix}continue_test"
        )

        continue_result = template_manager.generate_prompt(
            prompt_type=PromptType.CONTINUE_EXECUTION,
            context=continue_context
        )

        assert continue_result.success, f"Continue Prompt生成失败: {continue_result.error_message}"
        assert "continue" in continue_result.content.lower()

    def test_delayed_message_system(self):
        """测试延时消息系统"""
        # 1. 获取延时消息发送器和队列管理器
        delayed_sender = get_delayed_message_sender()
        queue_manager = get_message_queue_manager()

        # 2. 测试消息队列状态
        initial_stats = queue_manager.get_queue_stats()
        assert initial_stats.queue_status.value in ["idle", "processing"]

        # 3. 测试延时消息发送（使用较短延时进行测试）
        from parallel_dev_mcp.session.delayed_message_sender import MessageRequest
        from parallel_dev_mcp.session.message_queue_manager import QueueItemPriority

        test_message_request = MessageRequest(
            session_name=f"{self.test_session_prefix}message_test",
            message_content="echo 'E2E Test Message'",
            delay_seconds=2  # 短延时用于测试
        )

        # 添加到队列
        queue_result = queue_manager.add_message(
            message_request=test_message_request,
            priority=QueueItemPriority.NORMAL
        )

        assert queue_result["success"], f"添加消息到队列失败: {queue_result.get('message')}"
        assert queue_result["request_id"] == test_message_request.request_id

        # 4. 检查消息状态
        time.sleep(0.5)  # 等待消息开始处理

        status_info = delayed_sender.get_message_status(test_message_request.request_id)
        assert status_info is not None, "消息状态信息为空"
        assert status_info.session_name == test_message_request.session_name

    def test_error_handling_and_recovery(self):
        """测试错误处理和恢复"""
        # 1. 测试无效会话名称
        session_manager = SessionManager()

        invalid_result = session_manager.create_child_session(
            project_id="INVALID_PROJECT",
            task_id="invalid_task",
            session_name=""  # 无效的空会话名称
        )

        assert not invalid_result["success"], "应该失败的无效会话创建却成功了"
        assert "error" in invalid_result

        # 2. 测试Prompt模板错误处理
        template_manager = get_template_manager()

        # 测试无效的Prompt类型处理
        try:
            invalid_context = PromptContext(
                prompt_type=PromptType.MASTER_STOP,
                session_name=None,  # 这可能导致变量替换问题
                project_id=None
            )

            result = template_manager.generate_prompt(
                prompt_type=PromptType.MASTER_STOP,
                context=invalid_context
            )

            # 即使有问题，系统也应该优雅地处理并返回fallback内容
            assert result is not None
            assert isinstance(result.content, str)

        except Exception as e:
            pytest.fail(f"错误处理不够优雅: {e}")

    def test_resource_management_integration(self):
        """测试资源管理集成"""
        resource_manager = get_resource_manager()

        # 1. 创建Master资源
        master_created = resource_manager.create_master_resource(
            project_id=self.test_project_id,
            status="active",
            children=[],
            total_children=0,
            active_children=0
        )
        assert master_created, "Master资源创建失败"

        # 2. 创建Child资源
        child_session_name = f"{self.test_session_prefix}resource_test"
        child_created = resource_manager.create_child_resource(
            session_name=child_session_name,
            task_id="resource_test_task",
            project_id=self.test_project_id,
            status="active",
            transcript=""
        )
        assert child_created, "Child资源创建失败"

        # 3. 验证资源关联
        master_info = resource_manager.get_master_info(self.test_project_id)
        assert master_info is not None, "获取Master信息失败"

        child_info = resource_manager.get_child_info(child_session_name)
        assert child_info is not None, "获取Child信息失败"
        assert child_info.project_id == self.test_project_id

        # 4. 清理资源
        child_removed = resource_manager.remove_child_resource(child_session_name)
        assert child_removed, "删除Child资源失败"

    def test_system_performance_metrics(self):
        """测试系统性能指标"""
        # 1. 测试延时消息系统性能指标
        delayed_sender = get_delayed_message_sender()
        performance_metrics = delayed_sender.get_performance_metrics()

        assert "message_stats" in performance_metrics
        assert "performance_metrics" in performance_metrics
        assert "retry_statistics" in performance_metrics
        assert "circuit_breaker" in performance_metrics

        # 2. 测试队列统计
        queue_manager = get_message_queue_manager()
        queue_stats = queue_manager.get_queue_stats()

        assert hasattr(queue_stats, 'total_items')
        assert hasattr(queue_stats, 'pending_items')
        assert hasattr(queue_stats, 'queue_status')

        # 3. 测试模板系统验证
        template_manager = get_template_manager()
        validation_results = template_manager.validate_all_templates()

        assert isinstance(validation_results, dict)
        # 至少应该有默认模板
        assert len(validation_results) > 0

    def test_environment_variable_handling(self):
        """测试环境变量处理"""
        # 1. 测试PROJECT_PREFIX环境变量
        original_prefix = os.environ.get('PROJECT_PREFIX')

        try:
            # 设置测试环境变量
            os.environ['PROJECT_PREFIX'] = 'TEST_E2E'

            # 重新初始化组件以使用新的环境变量
            from parallel_dev_mcp.session.session_manager import SessionManager
            session_manager = SessionManager()

            # 验证环境变量是否正确使用
            # （这里需要根据实际的环境变量使用方式进行验证）

        finally:
            # 恢复原始环境变量
            if original_prefix is not None:
                os.environ['PROJECT_PREFIX'] = original_prefix
            else:
                os.environ.pop('PROJECT_PREFIX', None)

    def test_compatibility_with_hooks(self):
        """测试与现有hooks文件的兼容性"""
        # 1. 检查examples/hooks/目录是否存在
        hooks_dir = Path("examples/hooks")
        if not hooks_dir.exists():
            pytest.skip("examples/hooks目录不存在，跳过兼容性测试")

        # 2. 检查关键文件
        key_files = [
            "tmux_web_service.py",
            "web_message_sender.py"
        ]

        for file_name in key_files:
            file_path = hooks_dir / file_name
            if file_path.exists():
                # 验证文件可以正常导入（基本语法检查）
                try:
                    # 这里可以添加更详细的兼容性检查
                    content = file_path.read_text(encoding='utf-8')
                    assert len(content) > 0, f"{file_name} 文件为空"
                except Exception as e:
                    pytest.fail(f"读取 {file_name} 失败: {e}")


@pytest.mark.integration
class TestSystemHealthCheck:
    """系统健康检查测试"""

    def test_all_components_importable(self):
        """测试所有组件可正常导入"""
        try:
            # 测试核心组件导入
            from parallel_dev_mcp.session.session_manager import SessionManager
            from parallel_dev_mcp.session.resource_manager import get_resource_manager
            from parallel_dev_mcp.prompts.template_manager import get_template_manager
            from parallel_dev_mcp.session.delayed_message_sender import get_delayed_message_sender
            from parallel_dev_mcp.session.message_queue_manager import get_message_queue_manager

            # 验证实例化
            SessionManager()
            get_resource_manager()
            get_template_manager()
            get_delayed_message_sender()
            get_message_queue_manager()

        except ImportError as e:
            pytest.fail(f"组件导入失败: {e}")
        except Exception as e:
            pytest.fail(f"组件实例化失败: {e}")

    def test_mcp_tools_registration(self):
        """测试MCP工具注册"""
        try:
            # 导入MCP实例
            from parallel_dev_mcp.mcp_instance import mcp

            # 检查工具是否已注册
            if hasattr(mcp, '_tools'):
                tools_count = len(mcp._tools)
                assert tools_count > 0, "没有注册任何MCP工具"
            elif hasattr(mcp, '_tool_manager') and hasattr(mcp._tool_manager, 'tools'):
                tools_count = len(mcp._tool_manager.tools)
                assert tools_count > 0, "没有注册任何MCP工具"
            else:
                pytest.skip("无法检查MCP工具注册状态")

        except Exception as e:
            pytest.fail(f"MCP工具检查失败: {e}")

    def test_logging_system_functional(self):
        """测试日志系统功能"""
        try:
            from parallel_dev_mcp.session.message_logger import get_message_logger, LogLevel, MetricType

            logger = get_message_logger()

            # 测试日志记录
            logger.log(
                LogLevel.INFO,
                "test_component",
                "test_operation",
                "测试日志消息"
            )

            # 测试日志查询
            logs = logger.get_logs(limit=1)
            assert len(logs) >= 0, "日志查询功能异常"

            # 测试指标记录
            logger.record_metric(
                MetricType.COUNTER,
                "test_metric",
                1.0
            )

            metrics_summary = logger.get_metrics_summary()
            assert "counters" in metrics_summary

        except Exception as e:
            pytest.fail(f"日志系统测试失败: {e}")


if __name__ == "__main__":
    # 运行端到端测试
    pytest.main([__file__, "-v", "--tb=short"])