"""
MCP Tools - 完美融合架构

这是从mcp_server完美融合而来的分层MCP工具系统。
所有原server的能力都被保留并重新组织为更优雅的分层架构。

分层架构说明:
- tmux层: 纯MCP的tmux会话编排，零shell脚本依赖
- session层: 细粒度的会话管理，每个函数都是独立MCP工具  
- monitoring层: 系统监控和诊断，从coordinator完美融合而来
- orchestrator层: 项目级编排，最高级别的自动化能力

使用指南:
- 基础用户: 使用tmux层的orchestrator工具
- 高级用户: 使用session层的细粒度工具
- 系统管理员: 使用monitoring层的监控工具
- 项目经理: 使用orchestrator层的项目管理工具
"""

# === Tmux Layer - 纯MCP会话编排 ===
from .tmux.orchestrator import tmux_session_orchestrator

# === Session Layer - 细粒度会话管理 ===
from .session.session_manager import (
    create_development_session,
    terminate_session, 
    query_session_status,
    list_all_managed_sessions
)

from .session.message_system import (
    send_message_to_session,
    get_session_messages,
    mark_message_read,
    broadcast_message
)

from .session.relationship_manager import (
    register_session_relationship,
    query_child_sessions,
    get_session_hierarchy,
    find_session_path
)

# === Monitoring Layer - 系统监控和诊断 ===
from .monitoring.health_monitor import (
    check_system_health,
    diagnose_session_issues,
    get_performance_metrics
)

from .monitoring.status_dashboard import (
    get_system_dashboard,
    generate_status_report,
    export_system_metrics
)

# === Orchestrator Layer - 项目级编排 ===
from .orchestrator.project_orchestrator import (
    orchestrate_project_workflow,
    manage_project_lifecycle,
    coordinate_parallel_tasks
)

# === 分层导出 ===
__all__ = [
    # === TMUX LAYER ===
    # 基础会话编排 - 适合所有用户
    "tmux_session_orchestrator",
    
    # === SESSION LAYER === 
    # 会话管理 - 细粒度控制
    "create_development_session",
    "terminate_session",
    "query_session_status", 
    "list_all_managed_sessions",
    
    # 消息系统 - 会话间通信
    "send_message_to_session",
    "get_session_messages",
    "mark_message_read",
    "broadcast_message",
    
    # 关系管理 - 会话层级结构
    "register_session_relationship",
    "query_child_sessions",
    "get_session_hierarchy",
    "find_session_path",
    
    # === MONITORING LAYER ===
    # 健康监控 - 系统诊断
    "check_system_health",
    "diagnose_session_issues", 
    "get_performance_metrics",
    
    # 状态仪表板 - 可视化监控
    "get_system_dashboard",
    "generate_status_report",
    "export_system_metrics",
    
    # === ORCHESTRATOR LAYER ===
    # 项目编排 - 最高级别自动化
    "orchestrate_project_workflow",
    "manage_project_lifecycle",
    "coordinate_parallel_tasks"
]

# === 能力层级指南 ===
"""
🔧 TMUX LAYER (基础层)
   适用于: 所有用户
   能力: 纯MCP的tmux会话编排，替代所有shell脚本
   推荐: 日常开发工作的首选

📋 SESSION LAYER (细粒度层) 
   适用于: 需要精确控制的高级用户
   能力: 单个会话的精细管理和会话间通信
   推荐: 复杂项目的会话协调

📊 MONITORING LAYER (监控层)
   适用于: 系统管理员和运维人员
   能力: 系统健康监控、问题诊断、性能分析
   推荐: 生产环境监控和问题排查

🎯 ORCHESTRATOR LAYER (编排层)
   适用于: 项目经理和高级开发者
   能力: 完整项目生命周期管理和复杂工作流编排
   推荐: 大型项目的自动化管理

注意: 上层工具会自动调用下层工具，形成完整的能力融合体系。
"""