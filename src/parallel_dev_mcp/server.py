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
# 注意：tmux_tools 已删除（YAGNI清理，功能已被统一工具替代）

# 导入session工具 - 自动注册到mcp实例
from .session import session_tools

# 导入session资源 - 自动注册到mcp实例
from .session import mcp_resources

# 注意：prompts模块未实现，如需要可后续添加
# from .prompts import prompt_tools

# 注意：message_tools 已被统一工具 message(...) 替代

# 导入Web服务工具 - 自动注册到mcp实例
from .web import web_tools

# 导入Web服务生命周期管理
from .web.lifecycle_manager import initialize_web_lifecycle

# ====== 新统一工具层 (符合CLAUDE.md规范和YAGNI原则) ======
# 导入统一工具模块 - 提供类型安全的精简MCP工具集
# - session: 统一会话管理 (create/list/terminate)
# - message: 统一消息发送 (立即/延时发送)
# 所有返回值使用Pydantic Models，严禁 Dict[str, Any]
from .unified import session, message

# ====== 保留的必要模块 ======
# 导入Master职责管理 - 自动注册到mcp实例
from .session import master_responsibilities

# 导入主会话信息资源 - 自动注册到mcp实例
from .session import master_session_resource

# 注意：以下文件已删除（YAGNI清理）
# - template_tools.py (无实际用途)
# - log_tools.py (无实际用途)
# - delayed_message_sender.py (已被新 message 工具替代)
# - message_queue_manager.py (已被新 message 工具替代)
# - prompts/prompt_tools.py (无MCP工具，仅内部函数)

# 导入限流管理器 (内部能力，不暴露MCP工具)
from .session.rate_limit_manager import get_rate_limit_manager

# 导入tmux环境验证
from .session.tmux_validator import validate_tmux_environment

# 导入session lifecycle集成
from .session.lifecycle_integration import get_lifecycle_integration

# 导入共享的FastMCP实例
from .mcp_instance import mcp

# ====== 已删除的旧工具（功能已被统一工具替代） ======
# - child_tools.py: child_session_tool → 使用 session(action='create/terminate')
# - message_tools.py: send_delayed_message_tool → 使用 message(...)
# - session_tools.py: create_session → 使用 session(action='create')

# 注意：通过导入上述模块，所有 @mcp.tool 和 @mcp.resource 装饰的函数
# 会自动注册到这个mcp实例中。最终核心架构 (8个核心工具)：
#
# 📱 用户直接操作层 (8个MCP工具) - 只暴露用户必需的核心操作接口
# ├── tmux基础 (4个): list_tmux_sessions, kill_tmux_session, send_keys_to_tmux_session, get_tmux_session_info
# ├── session会话 (2个): create_session, update_child_resource
# ├── child管理 (1个): child_session_tool
# └── message消息 (1个): send_delayed_message_tool
#
# 🔧 内部能力层 (MCP核心自动流转，不暴露工具)
# ├── Master责任管理: 会话ID自动管理、Child监控、Git资源持久化 (_master_session_id_internal等)
# ├── 资源生命周期: 会话终止时自动清理、Master状态自动更新 (_remove_child_resource_internal等)
# ├── 限流检测: RateLimitManager 单例管理器 (通过 get_rate_limit_manager() 访问)
# ├── 日志系统: StructuredLogger 内部模块 (通过 _structured_log_internal() 等函数使用)
# ├── 模板管理: 内部模板处理 (通过 _template_manager_internal() 等函数使用)
# ├── Web服务: 内部Flask服务 (通过 _flask_web_server_internal() 自动流转)
# ├── 定时消息: 内部定时系统 (通过 _scheduled_message_internal() 自动流转)
# ├── 监控诊断: 内部诊断函数 (通过 _system_health_check_internal() 等函数使用)
# └── 系统信息: 内部信息收集 (通过 _get_system_info_internal() 内部使用)
#
# 📊 数据访问层 (8个MCP资源)
# ├── resource://parallel-dev-mcp/masters (Master项目集合)
# ├── resource://parallel-dev-mcp/master/{id} (单个Master项目详情)
# ├── resource://parallel-dev-mcp/children (Child任务集合)
# ├── resource://parallel-dev-mcp/child/{pid}/{tid} (单个Child任务详情)
# ├── resource://parallel-dev-mcp/statistics (系统统计信息)
# ├── resource://master-sessions (主会话信息集合)
# ├── resource://master-session-detail/{id} (主会话详细信息)
# └── resource://prompt-history (Prompt历史记录)
#
# 设计理念：\"只暴露用户必需的核心操作接口，内部能力完全隐藏\"
#
# ==================== 新架构 (符合CLAUDE.md规范 + YAGNI原则) ====================
#
# 📱 统一工具层 (2个MCP工具) - 类型安全、精简、符合YAGNI
# ├── session(action, task_id?, project_id?) - 统一会话管理
# │   └── 操作: create | list | terminate
# │   └── 返回: SessionResult (Pydantic Model)
# └── message(session_name, content, delay_seconds?) - 统一消息发送
#     └── 功能: 立即发送 | 延时发送 (0-300秒)
#     └── 返回: MessageResult (Pydantic Model)
#
# 🔒 严格规范:
# - 所有返回值必须是 Pydantic Models (严禁 Dict[str, Any])
# - 所有函数不得超过 50 行
# - 使用步骤编号注释 (# 1., # 2., etc.)
# - 遵循 YAGNI 原则：只实现必需功能
#
# 迁移计划：
# 1. ✅ 创建新统一工具（已完成）
# 2. 🔄 测试新工具功能（进行中）
# 3. ⏳ 标记旧工具为 @deprecated（待完成）
# 4. ⏳ 清理 YAGNI 违规文件（待完成）

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
        json_schema_extra={
            "example": {
                "status": "running",
                "version": "1.0.0",
                "description": "FastMCP服务器正常运行",
                "tools_count": 1,
            }
        }
    )


def _get_system_info_internal() -> Dict[str, Any]:
    """
    获取系统信息内部函数

    内部使用，不暴露为MCP工具。
    获取当前FastMCP服务器的基础系统信息，包括运行状态和版本信息。

    Returns:
        Dict[str, Any]: 系统信息字典，包含状态、版本等信息
    """
    # 1. 收集系统基础信息
    # 获取工具数量（通过访问工具管理器）
    try:
        if hasattr(mcp, "_tool_manager") and hasattr(mcp._tool_manager, "_tools"):
            tools_count = len(mcp._tool_manager._tools)
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


def _initialize_parallel_dev_system_internal() -> Dict[str, Any]:
    """
    内部系统初始化函数

    系统启动时自动调用，不暴露为MCP工具。
    初始化MCP资源管理器和生命周期集成，确保系统各组件正常协作。

    Returns:
        Dict[str, Any]: 初始化结果
    """
    try:
        # 1. 验证tmux环境（PRD要求）
        tmux_validation = validate_tmux_environment()
        if not tmux_validation.get("success"):
            logger.warning(f"Tmux环境验证失败: {tmux_validation.get('error')}")
            # 注意：这里不强制退出，因为MCP服务可能在非tmux环境中测试

        # 2. 初始化资源管理器
        from .session.mcp_resources import initialize_mcp_resources
        resource_init_result = initialize_mcp_resources()

        # 3. 初始化生命周期集成
        lifecycle_integration = get_lifecycle_integration()

        # 4. 初始化Web服务生命周期管理
        web_lifecycle_result = initialize_web_lifecycle()

        # 5. 初始化Master职责
        from .session.master_responsibilities import initialize_all_master_responsibilities
        master_responsibilities_result = initialize_all_master_responsibilities()

        # 6. 返回成功结果
        logger.info("并行开发系统初始化成功")
        return {
            "success": True,
            "message": "并行开发系统初始化成功",
            "tmux_environment": tmux_validation,
            "resource_manager_initialized": resource_init_result,
            "lifecycle_integration_active": True,
            "web_lifecycle_initialized": web_lifecycle_result,
            "master_responsibilities_initialized": master_responsibilities_result,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        # 7. 异常处理
        logger.error(f"并行开发系统初始化失败: {e}")
        return {
            "success": False,
            "message": f"初始化失败: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }


def _get_parallel_dev_status_internal() -> Dict[str, Any]:
    """
    内部系统状态查询函数

    内部使用，不暴露为MCP工具。
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
        if hasattr(mcp, "_tool_manager") and hasattr(mcp._tool_manager, "_tools"):
            tools_count = len(mcp._tool_manager._tools)
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
        if hasattr(mcp, "_tool_manager") and hasattr(mcp._tool_manager, "_tools"):
            tools_count = len(mcp._tool_manager._tools)
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
