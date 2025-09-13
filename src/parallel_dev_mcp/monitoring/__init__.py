"""
Monitoring Layer - 基础系统监控层

优化后的简化版本，专注基础健康检查功能。
移除了过度设计的诊断、性能指标、报告生成等复杂功能。
"""

from .health_monitor import (
    check_system_health
)

__all__ = [
    # 基础健康监控
    "check_system_health"
]