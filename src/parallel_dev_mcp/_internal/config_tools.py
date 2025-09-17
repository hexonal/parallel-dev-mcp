# -*- coding: utf-8 -*-
"""
环境变量管理系统

@description 基于Pydantic Settings的环境变量配置管理，支持动态Claude命令构建
"""

import re
import os
import shlex
from typing import Optional, Dict, List, Any, ClassVar
from pathlib import Path
from threading import Lock
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ConfigValidationError(Exception):
    """
    配置验证异常类

    用于处理特定的配置验证异常情况
    """

    def __init__(self, message: str, field_name: Optional[str] = None) -> None:
        """
        初始化配置验证异常

        Args:
            message: 错误消息
            field_name: 出错的字段名称
        """
        # 1. 初始化基础异常信息
        super().__init__(message)

        # 2. 设置扩展属性
        self.field_name = field_name
        self.message = message


class EnvConfig(BaseSettings):
    """
    环境变量配置类

    基于Pydantic Settings的环境变量管理，提供类型安全的配置访问
    """

    # 必填字段
    project_prefix: str = Field(
        ..., description="项目前缀，用于tmux会话命名", min_length=1, max_length=50
    )

    web_port: int = Field(..., description="Flask Web服务端口", ge=1024, le=65535)

    # 可选字段
    mcp_config_path: Optional[str] = Field(None, description="MCP配置文件路径")

    dangerously_skip_permissions: bool = Field(False, description="是否跳过权限检查")

    model_config = SettingsConfigDict(
        # 1. 环境变量配置
        env_prefix="",  # 不使用全局前缀，直接匹配字段名
        case_sensitive=False,  # 不区分大小写
        # 2. 验证配置
        validate_default=True,  # 验证默认值
        # 3. 示例数据
        json_schema_extra={
            "example": {
                "project_prefix": "myproject",
                "web_port": 5000,
                "mcp_config_path": "/path/to/mcp.json",
                "dangerously_skip_permissions": False,
            }
        },
    )

    @field_validator("project_prefix")
    @classmethod
    def validate_project_prefix(cls, v: str) -> str:
        """
        验证项目前缀格式

        Args:
            v: 项目前缀字符串

        Returns:
            str: 验证后的项目前缀

        Raises:
            ConfigValidationError: 项目前缀格式无效时抛出
        """
        # 1. 检查非空
        if not v or not v.strip():
            raise ConfigValidationError(
                "PROJECT_PREFIX不能为空", field_name="project_prefix"
            )

        # 2. 检查长度限制
        v = v.strip()
        if len(v) < 1 or len(v) > 50:
            raise ConfigValidationError(
                "PROJECT_PREFIX长度必须在1-50个字符之间", field_name="project_prefix"
            )

        # 3. 检查字符合法性（只允许字母、数字、下划线、横线）
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ConfigValidationError(
                "PROJECT_PREFIX只能包含字母、数字、下划线和横线",
                field_name="project_prefix",
            )

        # 4. 返回验证后的值
        return v

    @field_validator("web_port")
    @classmethod
    def validate_web_port(cls, v: int) -> int:
        """
        验证Web服务端口

        Args:
            v: 端口号

        Returns:
            int: 验证后的端口号

        Raises:
            ConfigValidationError: 端口号无效时抛出
        """
        # 1. 检查端口范围
        if not isinstance(v, int):
            raise ConfigValidationError("WEB_PORT必须是整数类型", field_name="web_port")

        # 2. 检查有效端口范围（避免系统保留端口）
        if v < 1024 or v > 65535:
            raise ConfigValidationError(
                "WEB_PORT必须在1024-65535范围内", field_name="web_port"
            )

        # 3. 返回验证后的端口
        return v

    @field_validator("mcp_config_path")
    @classmethod
    def validate_mcp_config_path(cls, v: Optional[str]) -> Optional[str]:
        """
        验证MCP配置文件路径

        Args:
            v: MCP配置文件路径

        Returns:
            Optional[str]: 验证后的文件路径

        Raises:
            ConfigValidationError: 文件路径无效时抛出
        """
        # 1. 如果为空则跳过验证
        if not v:
            return v

        # 2. 处理路径字符串
        v = v.strip()
        if not v:
            return None

        # 3. 验证文件路径存在性和可读性
        try:
            path = Path(v).resolve()

            # 4. 检查文件是否存在
            if not path.exists():
                raise ConfigValidationError(
                    f"MCP配置文件不存在: {path}", field_name="mcp_config_path"
                )

            # 5. 检查是否为文件
            if not path.is_file():
                raise ConfigValidationError(
                    f"MCP_CONFIG_PATH必须指向文件，而不是目录: {path}",
                    field_name="mcp_config_path",
                )

            # 6. 检查文件可读性
            if not os.access(path, os.R_OK):
                raise ConfigValidationError(
                    f"MCP配置文件不可读: {path}", field_name="mcp_config_path"
                )

        except (OSError, ValueError) as e:
            raise ConfigValidationError(
                f"MCP配置文件路径无效: {v} - {str(e)}", field_name="mcp_config_path"
            )

        # 7. 返回绝对路径字符串
        return str(path)

    @field_validator("dangerously_skip_permissions")
    @classmethod
    def validate_dangerously_skip_permissions(cls, v: Any) -> bool:
        """
        验证权限跳过标志

        Args:
            v: 权限跳过标志值

        Returns:
            bool: 验证后的布尔值

        Raises:
            ConfigValidationError: 布尔值转换失败时抛出
        """
        # 1. 如果已经是布尔类型，直接返回
        if isinstance(v, bool):
            return v

        # 2. 处理字符串类型的布尔值
        if isinstance(v, str):
            v = v.strip().lower()

            # 3. 支持的真值字符串
            if v in ("true", "1", "yes", "on", "enabled"):
                return True

            # 4. 支持的假值字符串
            if v in ("false", "0", "no", "off", "disabled", ""):
                return False

            # 5. 无效的字符串值
            raise ConfigValidationError(
                f"DANGEROUSLY_SKIP_PERMISSIONS无效值: '{v}', 支持的值: true/false, 1/0, yes/no, on/off, enabled/disabled",
                field_name="dangerously_skip_permissions",
            )

        # 6. 尝试转换其他类型
        try:
            return bool(v)
        except (ValueError, TypeError):
            raise ConfigValidationError(
                f"DANGEROUSLY_SKIP_PERMISSIONS无法转换为布尔值: {v}",
                field_name="dangerously_skip_permissions",
            )


class ClaudeCommandBuilder:
    """
    Claude命令构建器

    动态构建Claude启动命令，支持不同的环境变量组合
    """

    def __init__(self, config: EnvConfig) -> None:
        """
        初始化命令构建器

        Args:
            config: 环境变量配置实例
        """
        # 1. 存储配置实例
        self.config = config

    def build_command(self) -> List[str]:
        """
        构建Claude命令列表

        Returns:
            List[str]: Claude启动命令参数列表
        """
        # 1. 基础命令
        command = ["claude"]

        # 2. 根据配置添加MCP配置参数
        if self.config.mcp_config_path:
            command.extend(["--mcp-config", self.config.mcp_config_path])

        # 3. 根据配置添加权限跳过参数
        if self.config.dangerously_skip_permissions:
            command.append("--dangerously-skip-permissions")

        # 4. 返回完整命令
        return command

    def build_command_string(self) -> str:
        """
        构建Claude命令字符串

        Returns:
            str: 完整的命令字符串（用于日志和调试）
        """
        # 1. 获取命令列表
        command = self.build_command()

        # 2. 使用空格连接命令
        return " ".join(command)

    def build_shell_command(self) -> str:
        """
        构建适合shell执行的转义命令

        Returns:
            str: 适合shell执行的转义命令字符串
        """
        # 1. 获取命令列表
        command = self.build_command()

        # 2. 使用shlex进行转义
        return shlex.join(command)

    def preview_command(self) -> Dict[str, Any]:
        """
        预览命令构建结果（dry-run模式）

        Returns:
            Dict[str, Any]: 命令预览信息
        """
        # 1. 构建命令信息
        command_list = self.build_command()
        command_string = self.build_command_string()
        shell_command = self.build_shell_command()

        # 2. 分析参数配置
        has_mcp_config = bool(self.config.mcp_config_path)
        skip_permissions = self.config.dangerously_skip_permissions

        # 3. 返回预览信息
        return {
            "command_list": command_list,
            "command_string": command_string,
            "shell_command": shell_command,
            "parameter_analysis": {
                "base_command": "claude",
                "mcp_config": {
                    "enabled": has_mcp_config,
                    "path": self.config.mcp_config_path,
                },
                "skip_permissions": {"enabled": skip_permissions},
            },
            "execution_ready": True,
        }


class ConfigFactory:
    """
    配置工厂类

    实现单例模式的配置管理，提供全局配置访问
    """

    _instance: Optional[EnvConfig] = None
    _lock: ClassVar[Lock] = Lock()

    @classmethod
    def get_config(cls, reload: bool = False) -> EnvConfig:
        """
        获取配置实例

        Args:
            reload: 是否强制重新加载配置

        Returns:
            EnvConfig: 配置实例
        """
        # 1. 检查是否需要重新加载或首次加载
        if cls._instance is None or reload:
            with cls._lock:
                # 2. 双重检查锁定模式
                if cls._instance is None or reload:
                    try:
                        # 3. 从环境变量加载配置
                        cls._instance = EnvConfig()
                    except Exception as e:
                        raise ConfigValidationError(f"配置加载失败: {str(e)}")

        # 4. 返回配置实例
        return cls._instance

    @classmethod
    def reload_config(cls) -> EnvConfig:
        """
        重新加载配置

        Returns:
            EnvConfig: 新的配置实例
        """
        # 1. 强制重新加载配置
        return cls.get_config(reload=True)

    @classmethod
    def validate_config(cls, config: Optional[EnvConfig] = None) -> Dict[str, Any]:
        """
        验证配置完整性

        Args:
            config: 要验证的配置实例，如果为None则使用当前配置

        Returns:
            Dict[str, Any]: 验证结果
        """
        # 1. 获取要验证的配置
        if config is None:
            config = cls.get_config()

        # 2. 执行完整性检查
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "config_summary": {
                "project_prefix": config.project_prefix,
                "web_port": config.web_port,
                "has_mcp_config": bool(config.mcp_config_path),
                "skip_permissions": config.dangerously_skip_permissions,
            },
        }

        # 3. 检查端口是否被占用
        try:
            import socket

            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                result = s.connect_ex(("localhost", config.web_port))
                if result == 0:
                    validation_result["warnings"].append(
                        f"端口 {config.web_port} 可能已被占用"
                    )
        except Exception as e:
            validation_result["warnings"].append(f"无法检查端口占用情况: {str(e)}")

        # 4. 检查MCP配置文件可访问性
        if config.mcp_config_path:
            try:
                path = Path(config.mcp_config_path)
                if not path.exists():
                    validation_result["errors"].append(f"MCP配置文件不存在: {path}")
                    validation_result["valid"] = False
                elif not os.access(path, os.R_OK):
                    validation_result["errors"].append(f"MCP配置文件不可读: {path}")
                    validation_result["valid"] = False
            except Exception as e:
                validation_result["errors"].append(f"MCP配置文件路径错误: {str(e)}")
                validation_result["valid"] = False

        # 5. 返回验证结果
        return validation_result

    @classmethod
    def to_dict(
        cls, config: Optional[EnvConfig] = None, hide_sensitive: bool = True
    ) -> Dict[str, Any]:
        """
        将配置导出为字典

        Args:
            config: 要导出的配置实例
            hide_sensitive: 是否隐藏敏感信息

        Returns:
            Dict[str, Any]: 配置字典
        """
        # 1. 获取要导出的配置
        if config is None:
            config = cls.get_config()

        # 2. 导出配置字典
        config_dict = config.model_dump()

        # 3. 根据需要隐藏敏感信息
        if hide_sensitive:
            # 隐藏MCP配置文件的具体路径，只显示是否存在
            if config_dict.get("mcp_config_path"):
                config_dict["mcp_config_path"] = "[已配置]"

        # 4. 返回配置字典
        return config_dict

    @classmethod
    def to_json(
        cls, config: Optional[EnvConfig] = None, hide_sensitive: bool = True
    ) -> str:
        """
        将配置导出为JSON字符串

        Args:
            config: 要导出的配置实例
            hide_sensitive: 是否隐藏敏感信息

        Returns:
            str: JSON格式的配置字符串
        """
        # 1. 获取配置字典
        config_dict = cls.to_dict(config, hide_sensitive)

        # 2. 转换为JSON字符串
        import json

        return json.dumps(config_dict, indent=2, ensure_ascii=False)


# 配置变更监听器接口
class ConfigChangeListener:
    """
    配置变更监听器基类

    用于监听配置变更事件的回调接口
    """

    def on_config_changed(
        self, old_config: Optional[EnvConfig], new_config: EnvConfig
    ) -> None:
        """
        配置变更回调

        Args:
            old_config: 旧的配置实例
            new_config: 新的配置实例
        """
        pass


# 全局配置访问函数
def get_environment_config() -> EnvConfig:
    """
    获取环境变量配置

    便捷函数，用于获取全局配置实例

    Returns:
        EnvConfig: 环境变量配置实例
    """
    # 1. 通过配置工厂获取配置
    return ConfigFactory.get_config()


def build_claude_command(config: Optional[EnvConfig] = None) -> List[str]:
    """
    构建Claude启动命令

    便捷函数，用于快速构建Claude命令

    Args:
        config: 配置实例，如果为None则使用全局配置

    Returns:
        List[str]: Claude启动命令列表
    """
    # 1. 获取配置实例
    if config is None:
        config = get_environment_config()

    # 2. 构建命令
    builder = ClaudeCommandBuilder(config)
    return builder.build_command()
