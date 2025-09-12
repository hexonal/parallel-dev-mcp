"""
Orchestrator Layer - 项目编排层

从coordinator的高级能力完美融合而来，提供项目级编排功能。
适合需要完整项目管理的高级场景。
"""

from .project_orchestrator import (
    orchestrate_project_workflow,
    manage_project_lifecycle,
    coordinate_parallel_tasks
)

__all__ = [
    # 项目编排
    "orchestrate_project_workflow",
    "manage_project_lifecycle", 
    "coordinate_parallel_tasks"
]