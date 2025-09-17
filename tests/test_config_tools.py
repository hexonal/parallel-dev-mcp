# -*- coding: utf-8 -*-
"""
配置工具测试套件

@description 测试环境变量管理系统的完整功能
"""

import os
import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.parallel_dev_mcp._internal.config_tools import (
    EnvConfig,
    ConfigValidationError,
    ClaudeCommandBuilder,
    ConfigFactory,
    get_environment_config,
    build_claude_command,
)


class TestEnvConfig:
    """EnvConfig类测试"""

    def setup_method(self):
        """每个测试方法前的准备"""
        # 1. 清理ConfigFactory单例状态
        ConfigFactory._instance = None

        # 2. 备份环境变量
        self.original_env = os.environ.copy()

        # 3. 创建临时MCP配置文件
        self.temp_dir = tempfile.mkdtemp()
        self.mcp_config_file = Path(self.temp_dir) / "test_mcp.json"
        self.mcp_config_file.write_text('{"mcpServers": {}}')

    def teardown_method(self):
        """每个测试方法后的清理"""
        # 1. 恢复环境变量
        os.environ.clear()
        os.environ.update(self.original_env)

        # 2. 清理ConfigFactory单例状态
        ConfigFactory._instance = None

        # 3. 清理临时文件
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_env_config_valid_required_fields(self):
        """测试有效的必填字段"""
        # 1. 设置环境变量
        os.environ["PROJECT_PREFIX"] = "test_project"
        os.environ["WEB_PORT"] = "5000"

        # 2. 创建配置实例
        config = EnvConfig()

        # 3. 验证字段值
        assert config.project_prefix == "test_project"
        assert config.web_port == 5000
        assert config.mcp_config_path is None
        assert config.dangerously_skip_permissions is False

    def test_env_config_valid_all_fields(self):
        """测试所有字段都有效的情况"""
        # 1. 设置环境变量
        os.environ["PROJECT_PREFIX"] = "full_test"
        os.environ["WEB_PORT"] = "8080"
        os.environ["MCP_CONFIG_PATH"] = str(self.mcp_config_file)
        os.environ["DANGEROUSLY_SKIP_PERMISSIONS"] = "true"

        # 2. 创建配置实例
        config = EnvConfig()

        # 3. 验证字段值
        assert config.project_prefix == "full_test"
        assert config.web_port == 8080
        assert config.mcp_config_path == str(self.mcp_config_file.resolve())
        assert config.dangerously_skip_permissions is True

    def test_project_prefix_validation_empty(self):
        """测试项目前缀为空的验证"""
        # 1. 设置无效环境变量
        os.environ["PROJECT_PREFIX"] = ""
        os.environ["WEB_PORT"] = "5000"

        # 2. 验证抛出异常
        with pytest.raises(ConfigValidationError) as exc_info:
            EnvConfig()

        assert "PROJECT_PREFIX不能为空" in str(exc_info.value)

    def test_project_prefix_validation_invalid_chars(self):
        """测试项目前缀包含无效字符"""
        # 1. 设置无效环境变量
        os.environ["PROJECT_PREFIX"] = "test@project!"
        os.environ["WEB_PORT"] = "5000"

        # 2. 验证抛出异常
        with pytest.raises(ConfigValidationError) as exc_info:
            EnvConfig()

        assert "只能包含字母、数字、下划线和横线" in str(exc_info.value)

    def test_project_prefix_validation_too_long(self):
        """测试项目前缀过长"""
        # 1. 设置过长的项目前缀
        long_prefix = "a" * 51
        os.environ["PROJECT_PREFIX"] = long_prefix
        os.environ["WEB_PORT"] = "5000"

        # 2. 验证抛出异常
        with pytest.raises(ConfigValidationError) as exc_info:
            EnvConfig()

        assert "长度必须在1-50个字符之间" in str(exc_info.value)

    def test_web_port_validation_invalid_range(self):
        """测试无效端口范围"""
        # 1. 测试端口过小
        os.environ["PROJECT_PREFIX"] = "test"
        os.environ["WEB_PORT"] = "80"

        with pytest.raises(ConfigValidationError) as exc_info:
            EnvConfig()
        assert "必须在1024-65535范围内" in str(exc_info.value)

        # 2. 测试端口过大
        os.environ["WEB_PORT"] = "70000"

        with pytest.raises(ConfigValidationError) as exc_info:
            EnvConfig()
        assert "必须在1024-65535范围内" in str(exc_info.value)

    def test_mcp_config_path_validation_nonexistent(self):
        """测试不存在的MCP配置文件路径"""
        # 1. 设置不存在的文件路径
        os.environ["PROJECT_PREFIX"] = "test"
        os.environ["WEB_PORT"] = "5000"
        os.environ["MCP_CONFIG_PATH"] = "/nonexistent/path/mcp.json"

        # 2. 验证抛出异常
        with pytest.raises(ConfigValidationError) as exc_info:
            EnvConfig()

        assert "MCP配置文件不存在" in str(exc_info.value)

    def test_mcp_config_path_validation_directory(self):
        """测试MCP配置路径指向目录而非文件"""
        # 1. 设置指向目录的路径
        os.environ["PROJECT_PREFIX"] = "test"
        os.environ["WEB_PORT"] = "5000"
        os.environ["MCP_CONFIG_PATH"] = str(self.temp_dir)

        # 2. 验证抛出异常
        with pytest.raises(ConfigValidationError) as exc_info:
            EnvConfig()

        assert "必须指向文件，而不是目录" in str(exc_info.value)

    def test_dangerously_skip_permissions_validation(self):
        """测试权限跳过标志验证"""
        test_cases = [
            ("true", True),
            ("1", True),
            ("yes", True),
            ("on", True),
            ("enabled", True),
            ("false", False),
            ("0", False),
            ("no", False),
            ("off", False),
            ("disabled", False),
            ("", False),
        ]

        for input_value, expected in test_cases:
            # 1. 设置环境变量
            os.environ["PROJECT_PREFIX"] = "test"
            os.environ["WEB_PORT"] = "5000"
            os.environ["DANGEROUSLY_SKIP_PERMISSIONS"] = input_value

            # 2. 创建配置并验证
            config = EnvConfig()
            assert (
                config.dangerously_skip_permissions == expected
            ), f"输入 '{input_value}' 应该得到 {expected}"

            # 3. 清理环境变量
            del os.environ["DANGEROUSLY_SKIP_PERMISSIONS"]

    def test_dangerously_skip_permissions_invalid_value(self):
        """测试无效的权限跳过标志值"""
        # 1. 设置无效值
        os.environ["PROJECT_PREFIX"] = "test"
        os.environ["WEB_PORT"] = "5000"
        os.environ["DANGEROUSLY_SKIP_PERMISSIONS"] = "invalid_value"

        # 2. 验证抛出异常
        with pytest.raises(ConfigValidationError) as exc_info:
            EnvConfig()

        assert "DANGEROUSLY_SKIP_PERMISSIONS无效值" in str(exc_info.value)


class TestClaudeCommandBuilder:
    """ClaudeCommandBuilder类测试"""

    def setup_method(self):
        """每个测试方法前的准备"""
        # 1. 创建临时MCP配置文件
        self.temp_dir = tempfile.mkdtemp()
        self.mcp_config_file = Path(self.temp_dir) / "test_mcp.json"
        self.mcp_config_file.write_text('{"mcpServers": {}}')

    def teardown_method(self):
        """每个测试方法后的清理"""
        # 1. 清理临时文件
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def create_test_config(self, **kwargs) -> EnvConfig:
        """创建测试配置"""
        default_config = {
            "project_prefix": "test",
            "web_port": 5000,
            "mcp_config_path": None,
            "dangerously_skip_permissions": False,
        }
        default_config.update(kwargs)
        return EnvConfig(**default_config)

    def test_build_command_minimal(self):
        """测试最小配置的命令构建"""
        # 1. 创建最小配置
        config = self.create_test_config()
        builder = ClaudeCommandBuilder(config)

        # 2. 构建命令
        command = builder.build_command()

        # 3. 验证基础命令
        assert command == ["claude"]

    def test_build_command_with_mcp_config(self):
        """测试包含MCP配置的命令构建"""
        # 1. 创建包含MCP配置的配置
        config = self.create_test_config(mcp_config_path=str(self.mcp_config_file))
        builder = ClaudeCommandBuilder(config)

        # 2. 构建命令
        command = builder.build_command()

        # 3. 验证命令包含MCP配置
        expected_command = ["claude", "--mcp-config", str(self.mcp_config_file)]
        assert command == expected_command

    def test_build_command_with_skip_permissions(self):
        """测试跳过权限的命令构建"""
        # 1. 创建跳过权限的配置
        config = self.create_test_config(dangerously_skip_permissions=True)
        builder = ClaudeCommandBuilder(config)

        # 2. 构建命令
        command = builder.build_command()

        # 3. 验证命令包含权限跳过参数
        expected_command = ["claude", "--dangerously-skip-permissions"]
        assert command == expected_command

    def test_build_command_full_options(self):
        """测试包含所有选项的命令构建"""
        # 1. 创建完整配置
        config = self.create_test_config(
            mcp_config_path=str(self.mcp_config_file), dangerously_skip_permissions=True
        )
        builder = ClaudeCommandBuilder(config)

        # 2. 构建命令
        command = builder.build_command()

        # 3. 验证完整命令
        expected_command = [
            "claude",
            "--mcp-config",
            str(self.mcp_config_file),
            "--dangerously-skip-permissions",
        ]
        assert command == expected_command

    def test_build_command_string(self):
        """测试命令字符串构建"""
        # 1. 创建配置
        config = self.create_test_config(
            mcp_config_path=str(self.mcp_config_file), dangerously_skip_permissions=True
        )
        builder = ClaudeCommandBuilder(config)

        # 2. 构建命令字符串
        command_string = builder.build_command_string()

        # 3. 验证命令字符串
        expected_string = (
            f"claude --mcp-config {self.mcp_config_file} --dangerously-skip-permissions"
        )
        assert command_string == expected_string

    def test_build_shell_command(self):
        """测试Shell命令构建"""
        # 1. 创建包含特殊字符的路径配置
        special_path = Path(self.temp_dir) / "path with spaces.json"
        special_path.write_text("{}")

        config = self.create_test_config(mcp_config_path=str(special_path))
        builder = ClaudeCommandBuilder(config)

        # 2. 构建shell命令
        shell_command = builder.build_shell_command()

        # 3. 验证shell命令正确转义
        assert "path with spaces.json" in shell_command
        # 检查是否正确转义（根据平台可能有不同的转义方式）
        assert shell_command.count("'") > 0 or shell_command.count('"') > 0

    def test_preview_command(self):
        """测试命令预览功能"""
        # 1. 创建配置
        config = self.create_test_config(
            mcp_config_path=str(self.mcp_config_file), dangerously_skip_permissions=True
        )
        builder = ClaudeCommandBuilder(config)

        # 2. 预览命令
        preview = builder.preview_command()

        # 3. 验证预览结果
        assert isinstance(preview, dict)
        assert "command_list" in preview
        assert "command_string" in preview
        assert "shell_command" in preview
        assert "parameter_analysis" in preview
        assert preview["execution_ready"] is True

        # 4. 验证参数分析
        analysis = preview["parameter_analysis"]
        assert analysis["base_command"] == "claude"
        assert analysis["mcp_config"]["enabled"] is True
        assert analysis["skip_permissions"]["enabled"] is True


class TestConfigFactory:
    """ConfigFactory类测试"""

    def setup_method(self):
        """每个测试方法前的准备"""
        # 1. 清理ConfigFactory单例状态
        ConfigFactory._instance = None

        # 2. 备份环境变量
        self.original_env = os.environ.copy()

        # 3. 创建临时MCP配置文件
        self.temp_dir = tempfile.mkdtemp()
        self.mcp_config_file = Path(self.temp_dir) / "test_mcp.json"
        self.mcp_config_file.write_text('{"mcpServers": {}}')

    def teardown_method(self):
        """每个测试方法后的清理"""
        # 1. 恢复环境变量
        os.environ.clear()
        os.environ.update(self.original_env)

        # 2. 清理ConfigFactory单例状态
        ConfigFactory._instance = None

        # 3. 清理临时文件
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_get_config_singleton(self):
        """测试单例模式"""
        # 1. 设置环境变量
        os.environ["PROJECT_PREFIX"] = "test"
        os.environ["WEB_PORT"] = "5000"

        # 2. 获取两个配置实例
        config1 = ConfigFactory.get_config()
        config2 = ConfigFactory.get_config()

        # 3. 验证是同一个实例
        assert config1 is config2

    def test_reload_config(self):
        """测试配置重新加载"""
        # 1. 设置初始环境变量
        os.environ["PROJECT_PREFIX"] = "initial"
        os.environ["WEB_PORT"] = "5000"

        # 2. 获取初始配置
        config1 = ConfigFactory.get_config()
        assert config1.project_prefix == "initial"

        # 3. 修改环境变量
        os.environ["PROJECT_PREFIX"] = "updated"

        # 4. 重新加载配置
        config2 = ConfigFactory.reload_config()

        # 5. 验证配置已更新
        assert config2.project_prefix == "updated"
        assert config1 is not config2

    def test_validate_config_success(self):
        """测试配置验证成功"""
        # 1. 设置有效环境变量
        os.environ["PROJECT_PREFIX"] = "test"
        os.environ["WEB_PORT"] = "5000"
        os.environ["MCP_CONFIG_PATH"] = str(self.mcp_config_file)

        # 2. 验证配置
        result = ConfigFactory.validate_config()

        # 3. 验证结果
        assert result["valid"] is True
        assert len(result["errors"]) == 0
        assert "config_summary" in result

    def test_validate_config_with_warnings(self):
        """测试配置验证带警告"""
        # 1. 设置环境变量
        os.environ["PROJECT_PREFIX"] = "test"
        os.environ["WEB_PORT"] = "5000"

        # 2. Mock端口占用检查
        with patch("socket.socket") as mock_socket:
            mock_context = MagicMock()
            mock_context.connect_ex.return_value = 0  # 端口被占用
            mock_socket.return_value.__enter__ = MagicMock(return_value=mock_context)

            # 3. 验证配置
            result = ConfigFactory.validate_config()

            # 4. 验证警告
            assert result["valid"] is True
            assert len(result["warnings"]) > 0
            assert any(
                "端口" in warning and "占用" in warning
                for warning in result["warnings"]
            )

    def test_to_dict_hide_sensitive(self):
        """测试配置导出为字典（隐藏敏感信息）"""
        # 1. 设置环境变量
        os.environ["PROJECT_PREFIX"] = "test"
        os.environ["WEB_PORT"] = "5000"
        os.environ["MCP_CONFIG_PATH"] = str(self.mcp_config_file)

        # 2. 导出配置字典（隐藏敏感信息）
        config_dict = ConfigFactory.to_dict(hide_sensitive=True)

        # 3. 验证敏感信息被隐藏
        assert config_dict["mcp_config_path"] == "[已配置]"
        assert config_dict["project_prefix"] == "test"
        assert config_dict["web_port"] == 5000

    def test_to_dict_show_sensitive(self):
        """测试配置导出为字典（显示敏感信息）"""
        # 1. 设置环境变量
        os.environ["PROJECT_PREFIX"] = "test"
        os.environ["WEB_PORT"] = "5000"
        os.environ["MCP_CONFIG_PATH"] = str(self.mcp_config_file)

        # 2. 导出配置字典（显示敏感信息）
        config_dict = ConfigFactory.to_dict(hide_sensitive=False)

        # 3. 验证敏感信息可见
        assert config_dict["mcp_config_path"] == str(self.mcp_config_file.resolve())

    def test_to_json(self):
        """测试配置导出为JSON"""
        # 1. 设置环境变量
        os.environ["PROJECT_PREFIX"] = "test"
        os.environ["WEB_PORT"] = "5000"

        # 2. 导出配置JSON
        config_json = ConfigFactory.to_json()

        # 3. 验证JSON格式正确
        parsed_config = json.loads(config_json)
        assert parsed_config["project_prefix"] == "test"
        assert parsed_config["web_port"] == 5000


class TestGlobalFunctions:
    """全局函数测试"""

    def setup_method(self):
        """每个测试方法前的准备"""
        # 1. 清理ConfigFactory单例状态
        ConfigFactory._instance = None

        # 2. 备份环境变量
        self.original_env = os.environ.copy()

    def teardown_method(self):
        """每个测试方法后的清理"""
        # 1. 恢复环境变量
        os.environ.clear()
        os.environ.update(self.original_env)

        # 2. 清理ConfigFactory单例状态
        ConfigFactory._instance = None

    def test_get_environment_config(self):
        """测试全局配置获取函数"""
        # 1. 设置环境变量
        os.environ["PROJECT_PREFIX"] = "global_test"
        os.environ["WEB_PORT"] = "8080"

        # 2. 获取配置
        config = get_environment_config()

        # 3. 验证配置
        assert isinstance(config, EnvConfig)
        assert config.project_prefix == "global_test"
        assert config.web_port == 8080

    def test_build_claude_command(self):
        """测试全局Claude命令构建函数"""
        # 1. 设置环境变量
        os.environ["PROJECT_PREFIX"] = "command_test"
        os.environ["WEB_PORT"] = "3000"

        # 2. 构建命令
        command = build_claude_command()

        # 3. 验证命令
        assert isinstance(command, list)
        assert command[0] == "claude"


class TestPerformance:
    """性能测试"""

    def setup_method(self):
        """每个测试方法前的准备"""
        # 1. 清理ConfigFactory单例状态
        ConfigFactory._instance = None

        # 2. 设置环境变量
        os.environ["PROJECT_PREFIX"] = "perf_test"
        os.environ["WEB_PORT"] = "5000"

    def teardown_method(self):
        """每个测试方法后的清理"""
        ConfigFactory._instance = None

    def test_config_loading_performance(self):
        """测试配置加载性能"""
        import time

        # 1. 测试首次加载时间
        start_time = time.time()
        config1 = ConfigFactory.get_config()
        first_load_time = time.time() - start_time

        # 2. 测试单例访问时间
        start_time = time.time()
        config2 = ConfigFactory.get_config()
        second_access_time = time.time() - start_time

        # 3. 验证性能要求
        assert first_load_time < 1.0  # 首次加载应小于1秒
        assert second_access_time < 0.01  # 单例访问应小于0.01秒
        assert config1 is config2

    def test_command_generation_performance(self):
        """测试命令生成效率"""
        import time

        # 1. 获取配置
        config = ConfigFactory.get_config()
        builder = ClaudeCommandBuilder(config)

        # 2. 测试命令生成时间
        start_time = time.time()
        for _ in range(1000):
            command = builder.build_command()
        generation_time = time.time() - start_time

        # 3. 验证性能要求
        assert generation_time < 0.1  # 1000次命令生成应小于0.1秒
        assert isinstance(command, list)


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])
