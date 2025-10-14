# -*- coding: utf-8 -*-
"""
会话管理模块

@description 提供Master和Child会话的管理、资源存储和生命周期集成功能
"""

# 数据模型
from .models import (
    MasterResourceModel,
    ChildResourceModel,
    RepoInfo,
    ChildStatus,
    MasterStatus
)

# 资源管理器
from .resource_manager import (
    ResourceManager,
    ResourceConfig,
    ResourceEvent,
    ResourceEventType
)

# MCP资源集成
from .mcp_resources import (
    get_resource_manager,
    initialize_mcp_resources,
    cleanup_mcp_resources
)

# 生命周期集成
from .lifecycle_integration import (
    LifecycleIntegration,
    LifecycleConfig,
    SessionEvent,
    SessionEventType,
    get_lifecycle_integration
)

# 会话管理工具
from .session_tools import (
    update_child_resource,
    SessionCreateResult
)
# 注意：create_session 已被统一工具 session(action='create') 替代
# 注意：update_master_resource 和 remove_child_resource 是内部函数，不导出

__all__ = [
    # 数据模型
    "MasterResourceModel",
    "ChildResourceModel",
    "RepoInfo",
    "ChildStatus",
    "MasterStatus",

    # 资源管理器
    "ResourceManager",
    "ResourceConfig",
    "ResourceEvent",
    "ResourceEventType",

    # MCP资源集成
    "get_resource_manager",
    "initialize_mcp_resources",
    "cleanup_mcp_resources",

    # 生命周期集成
    "LifecycleIntegration",
    "LifecycleConfig",
    "SessionEvent",
    "SessionEventType",
    "get_lifecycle_integration",

    # 会话管理工具
    "update_child_resource",
    "SessionCreateResult"
    # 注意：create_session 已被统一工具 session(action='create') 替代
]