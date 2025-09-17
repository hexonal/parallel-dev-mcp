# -*- coding: utf-8 -*-
"""
FastMCP 服务器入口

@description Claude Code并行开发系统的FastMCP服务器实现
"""

import logging
from datetime import datetime
from typing import Dict, Any
from pydantic import BaseModel, Field, field_validator, ConfigDict
from fastmcp import FastMCP

# 导入MCP工具和资源
# 导入tmux工具 - 自动注册到mcp实例
from .tmux import tmux_tools

# 导入session工具 - 自动注册到mcp实例
from .session import session_tools

# 导入session资源 - 自动注册到mcp实例
from .session import mcp_resources

# 导入Prompt工具 - 自动注册到mcp实例
from .prompts import prompt_tools

# 导入延时消息工具 - 自动注册到mcp实例
from .session import message_tools

# 导入session lifecycle集成
from .session.lifecycle_integration import get_lifecycle_integration

# 导入共享的FastMCP实例
from .mcp_instance import mcp

# 注意：通过导入上述模块，所有 @mcp.tool 和 @mcp.resource 装饰的函数
# 会自动注册到这个mcp实例中。包括：
# - tmux_tools: list_tmux_sessions, kill_tmux_session, send_keys_to_tmux_session, get_tmux_session_info
# - session_tools: create_session, update_master_resource, update_child_resource, remove_child_resource
# - mcp_resources: masters_resource, children_resource, master_detail_resource, child_detail_resource, stats_resource
# - prompt_tools: generate_prompt_tool, list_templates_tool, reload_template_tool, validate_templates_tool, get_template_info_tool, generate_continue_prompt_tool
# - message_tools: send_delayed_message_tool, get_message_status_tool, get_queue_status_tool, cancel_message_tool, clear_message_queue_tool, get_performance_metrics_tool, get_system_logs_tool

# 配置日志系统
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class SystemInfoModel(BaseModel):
    """
    系统信息数据模型

    用于系统状态查询的数据验证和序列化
    """

    status: str = Field("running", description="系统状态")
    version: str = Field("1.0.0", description="版本号")
    description: str = Field("", description="系统描述")
    tools_count: int = Field(0, description="注册的工具数量", ge=0)

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        """
        验证系统状态格式

        Args:
            v: 状态字符串

        Returns:
            str: 验证后的状态
        """
        # 1. 检查状态值有效性
        valid_statuses = ["running", "stopped", "error"]
        if v not in valid_statuses:
            raise ValueError(f"状态必须是以下之一: {valid_statuses}")

        # 2. 返回验证后的状态
        return v

    model_config = ConfigDict(
        # 1. 启用JSON编码器
        json_encoders={},
        # 2. 示例数据
        json_schema_extra={
            "example": {
                "status": "running",
                "version": "1.0.0",
                "description": "FastMCP服务器正常运行",
                "tools_count": 1,
            }
        },
    )


@mcp.tool
def get_system_info() -> Dict[str, Any]:
    """
    获取系统信息工具

    获取当前FastMCP服务器的基础系统信息，包括运行状态和版本信息。
    这是一个测试工具，用于验证MCP服务器功能正常。

    Returns:
        Dict[str, Any]: 系统信息字典，包含状态、版本等信息
    """
    # 1. 收集系统基础信息
    # 获取工具数量（通过访问工具管理器）
    try:
        if hasattr(mcp, "_tool_manager") and hasattr(mcp._tool_manager, "tools"):
            tools_count = len(mcp._tool_manager.tools)
        else:
            tools_count = 1
    except (AttributeError, TypeError):
        # 如果无法获取工具计数，使用默认值1（当前工具）
        tools_count = 1

    system_info = SystemInfoModel(
        status="running",
        version="1.0.0",
        description="FastMCP 2.11.3+ 并行开发系统",
        tools_count=tools_count,
    )

    # 2. 验证数据模型
    validated_info = system_info.model_dump()

    # 3. 记录日志
    logger.info(f"系统信息查询: {tools_count} 个工具已注册")

    # 4. 返回验证后的数据
    return validated_info


@mcp.tool
def initialize_parallel_dev_system() -> Dict[str, Any]:
    """
    初始化并行开发系统

    初始化MCP资源管理器和生命周期集成，确保系统各组件正常协作。

    Returns:
        Dict[str, Any]: 初始化结果
    """
    try:
        # 1. 初始化资源管理器
        from .session.mcp_resources import initialize_mcp_resources
        resource_init_result = initialize_mcp_resources()

        # 2. 初始化生命周期集成
        lifecycle_integration = get_lifecycle_integration()

        # 3. 返回成功结果
        logger.info("并行开发系统初始化成功")
        return {
            "success": True,
            "message": "并行开发系统初始化成功",
            "resource_manager_initialized": resource_init_result,
            "lifecycle_integration_active": True,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        # 4. 异常处理
        logger.error(f"并行开发系统初始化失败: {e}")
        return {
            "success": False,
            "message": f"初始化失败: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }


@mcp.tool
def get_parallel_dev_status() -> Dict[str, Any]:
    """
    获取并行开发系统状态

    获取tmux工具、session工具和资源管理器的当前状态信息。

    Returns:
        Dict[str, Any]: 系统状态信息
    """
    try:
        # 1. 获取资源管理器状态
        from .session.resource_manager import get_resource_manager
        resource_manager = get_resource_manager()

        # 2. 统计注册的工具数量
        tools_count = 0
        if hasattr(mcp, "_tool_manager") and hasattr(mcp._tool_manager, "tools"):
            tools_count = len(mcp._tool_manager.tools)
        elif hasattr(mcp, "_tools"):
            tools_count = len(mcp._tools)

        # 3. 返回状态信息
        status_info = {
            "system_status": "running",
            "tools_registered": tools_count,
            "resource_manager_active": resource_manager is not None,
            "master_projects_count": len(resource_manager.masters) if resource_manager else 0,
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0"
        }

        logger.info(f"并行开发系统状态查询: {tools_count} 个工具已注册")
        return status_info

    except Exception as e:
        # 4. 异常处理
        logger.error(f"获取系统状态失败: {e}")
        return {
            "system_status": "error",
            "error_message": str(e),
            "timestamp": datetime.now().isoformat()
        }


def setup_logging() -> None:
    """
    配置日志系统

    设置日志格式和级别，确保系统运行状态可追踪。
    """
    # 1. 设置日志级别
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # 2. 设置FastMCP相关日志
    fastmcp_logger = logging.getLogger("fastmcp")
    fastmcp_logger.setLevel(logging.INFO)


def main() -> None:
    """
    程序主入口点

    作为包的main()函数，支持通过'uv run python -m src.parallel_dev_mcp.server'启动。
    默认使用STDIO模式运行MCP服务器。
    """
    # 1. 初始化日志系统
    setup_logging()
    logger.info("FastMCP 并行开发服务器启动中...")

    # 2. 检查注册的工具
    try:
        if hasattr(mcp, "_tool_manager") and hasattr(mcp._tool_manager, "tools"):
            tools_count = len(mcp._tool_manager.tools)
        else:
            tools_count = 1
    except (AttributeError, TypeError):
        tools_count = 1
    logger.info(f"已注册 {tools_count} 个MCP工具")

    # 3. 启动MCP服务器 (STDIO模式)
    try:
        logger.info("服务器启动成功，使用STDIO模式")
        mcp.run()
    except Exception as e:
        # 4. 异常处理
        logger.error(f"服务器启动失败: {e}")
        raise


def run_http_server(host: str = "127.0.0.1", port: int = 8000) -> None:
    """
    启动HTTP模式服务器

    Args:
        host: 监听主机地址
        port: 监听端口号
    """
    # 1. 初始化日志
    setup_logging()
    logger.info(f"FastMCP HTTP服务器启动: {host}:{port}")

    # 2. 启动HTTP服务器
    try:
        mcp.run(transport="http", host=host, port=port)
    except Exception as e:
        # 3. 异常处理
        logger.error(f"HTTP服务器启动失败: {e}")
        raise


if __name__ == "__main__":
    main()
