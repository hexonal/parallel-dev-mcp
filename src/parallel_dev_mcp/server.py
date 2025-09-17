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

# 导入资源管理器
from .resources.master_resource import (
    get_master_info_resource,
    update_master_info_resource,
)

# 初始化FastMCP实例
mcp = FastMCP("parallel-dev-mcp")

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


@mcp.resource("resource://parallel-dev-mcp/master_session_info")
def master_session_info_resource() -> Dict[str, Any]:
    """
    Master 会话信息资源

    提供当前 Master 会话的完整信息，包括会话ID、Git仓库信息、分支状态等。
    该资源包含持久化的会话数据，支持版本控制和并发访问保护。

    Returns:
        Dict[str, Any]: Master 会话信息，包含以下字段：
            - session_id: 会话唯一标识
            - repo_url: Git仓库远程URL
            - current_branch: 当前分支名称
            - default_branch: 默认分支名称
            - repository_path: 仓库根目录路径
            - is_detached_head: 是否处于detached HEAD状态
            - remotes: 所有远程仓库列表
            - created_at: 会话创建时间
            - updated_at: 最后更新时间
            - version: 资源版本号
    """
    # 1. 获取Master会话资源内容
    resource_content = get_master_info_resource()

    # 2. 记录资源访问
    logger.debug("Master会话信息资源被访问")

    # 3. 返回资源内容
    return resource_content


@mcp.tool
def update_master_session_info() -> Dict[str, Any]:
    """
    更新 Master 会话信息工具

    重新收集当前环境的 Git 信息和会话状态，更新持久化的 Master 资源数据。
    该工具会自动处理版本控制，确保数据一致性和并发安全。

    Returns:
        Dict[str, Any]: 更新操作结果，包含成功状态和更新信息
    """
    # 1. 执行资源更新
    update_success = update_master_info_resource()

    # 2. 构建结果
    result = {
        "success": update_success,
        "message": (
            "Master会话信息更新成功" if update_success else "Master会话信息更新失败"
        ),
        "timestamp": str(datetime.now()),
    }

    # 3. 记录更新操作
    if update_success:
        logger.info("Master会话信息更新成功")
    else:
        logger.error("Master会话信息更新失败")

    # 4. 返回结果
    return result


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
