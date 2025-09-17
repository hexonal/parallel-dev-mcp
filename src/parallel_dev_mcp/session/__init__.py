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
    "get_lifecycle_integration"
]