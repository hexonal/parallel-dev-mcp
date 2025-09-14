"""
MCP Tools Export Module - 统一导出优化后的三层MCP工具架构
用于统一导入所有MCP工具函数，支持 CLAUDE.md 中的使用模式。
"""

# 🔧 Tmux Layer (2 tools) - 基础会话编排和Claude启动
from ..parallel_dev_mcp.tmux.orchestrator import tmux_session_orchestrator, launch_claude_in_session

# 📋 Session Layer (7 tools) - 精细会话管理
from ..parallel_dev_mcp.session.session_manager import (
    create_development_session,
    register_existing_session,
    terminate_session,
    query_session_status,
    list_all_managed_sessions
)

from ..parallel_dev_mcp.session.message_system import (
    send_message_to_session,
    get_session_messages,
    mark_message_read
)

from ..parallel_dev_mcp.session.relationship_manager import (
    register_session_relationship,
    query_child_sessions
)

# 📊 Monitoring Layer (1 tool) - 基础健康监控
from ..parallel_dev_mcp.monitoring.health_monitor import check_system_health

# 🛠️ 内部工具 (1 tool) - 配置管理
from ..parallel_dev_mcp._internal.config_tools import get_environment_config

# 导出所有工具名称列表
__all__ = [
    # Tmux Layer
    'tmux_session_orchestrator',
    'launch_claude_in_session',

    # Session Layer
    'create_development_session',
    'register_existing_session',
    'terminate_session',
    'query_session_status',
    'list_all_managed_sessions',
    'send_message_to_session',
    'get_session_messages',
    'mark_message_read',
    'register_session_relationship',
    'query_child_sessions',

    # Monitoring Layer
    'check_system_health',

    # Internal Tools
    'get_environment_config'
]

# 版本信息
__version__ = "1.0.0"
__description__ = "优化的三层MCP工具架构 - 10个核心工具，专注essential功能"