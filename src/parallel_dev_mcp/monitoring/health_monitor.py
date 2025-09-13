"""
Health Monitor - 基础系统健康监控
优化后的简化版本，专注基础健康检查功能。
移除了过度设计的诊断、性能指标等复杂功能。
"""

import json
import subprocess
from datetime import datetime, timedelta
from typing import Dict, Any, List
import psutil
import os

# 复用已重构的组件
from .._internal.global_registry import get_global_registry
from .._internal.health_utils import calculate_session_health_score

# MCP工具装饰器
def mcp_tool(name: str = None, description: str = None):
    """MCP工具装饰器"""
    def decorator(func):
        func.mcp_tool_name = name or func.__name__
        func.mcp_tool_description = description or func.__doc__
        return func
    return decorator

# 全局共享会话注册中心
_session_registry = get_global_registry()

@mcp_tool(
    name="check_system_health",
    description="全面的系统健康检查，包括会话状态、系统资源、tmux状态"
)
def check_system_health(
    include_detailed_metrics: bool = False,
    check_tmux_integrity: bool = True
) -> Dict[str, Any]:
    """
    系统健康检查 - 全面的系统状态评估
    
    Args:
        include_detailed_metrics: 是否包含详细的系统指标
        check_tmux_integrity: 是否检查tmux完整性
    """
    try:
        health_report = {
            "timestamp": datetime.now().isoformat(),
            "overall_status": "unknown",
            "health_score": 0.0,
            "components": {}
        }
        
        # 1. 检查会话健康状况
        session_health = _check_sessions_health()
        health_report["components"]["sessions"] = session_health
        
        # 2. 检查系统资源
        system_health = _check_system_resources(include_detailed_metrics)
        health_report["components"]["system_resources"] = system_health
        
        # 3. 检查tmux状态
        if check_tmux_integrity:
            tmux_health = _check_tmux_integrity()
            health_report["components"]["tmux"] = tmux_health
        
        # 4. 检查MCP组件状态
        mcp_health = _check_mcp_components()
        health_report["components"]["mcp_components"] = mcp_health
        
        # 5. 计算总体健康分数
        health_report["health_score"] = _calculate_overall_health_score(health_report["components"])
        health_report["overall_status"] = _determine_health_status(health_report["health_score"])
        
        # 6. 生成建议
        health_report["recommendations"] = _generate_health_recommendations(health_report)
        
        return health_report
        
    except Exception as e:
        return {
            "success": False,
            "error": f"系统健康检查失败: {str(e)}"
        }

# 过度设计的工具已移除：
# - diagnose_session_issues: 过度复杂的会话诊断分析
# - get_performance_metrics: 过度复杂的性能指标收集
# 保留 check_system_health 作为唯一的基础监控工具

# === 内部辅助函数 ===

def _check_sessions_health() -> Dict[str, Any]:
    """检查所有会话的健康状况"""
    all_sessions = _session_registry.list_all_sessions()
    
    healthy_count = 0
    total_sessions = len(all_sessions)
    session_details = {}
    
    for name, session_info in all_sessions.items():
        session_dict = session_info.to_dict()
        health_score = calculate_session_health_score(session_dict)
        
        session_details[name] = {
            "health_score": health_score,
            "status": "healthy" if health_score > 0.8 else "warning" if health_score > 0.5 else "unhealthy",
            "last_activity": session_dict.get("last_activity"),
            "message_count": session_dict.get("message_count", 0)
        }
        
        if health_score > 0.8:
            healthy_count += 1
    
    return {
        "status": "healthy" if healthy_count == total_sessions else "degraded",
        "total_sessions": total_sessions,
        "healthy_sessions": healthy_count,
        "health_ratio": healthy_count / total_sessions if total_sessions > 0 else 1.0,
        "session_details": session_details
    }

def _check_system_resources(include_detailed: bool = False) -> Dict[str, Any]:
    """检查系统资源使用情况"""
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        resource_status = {
            "status": "healthy",
            "cpu_usage": cpu_percent,
            "memory_usage": memory.percent,
            "disk_usage": disk.percent,
            "warnings": []
        }
        
        # 检查资源警告
        if cpu_percent > 80:
            resource_status["warnings"].append(f"CPU使用率过高: {cpu_percent}%")
            resource_status["status"] = "warning"
        
        if memory.percent > 85:
            resource_status["warnings"].append(f"内存使用率过高: {memory.percent}%")
            resource_status["status"] = "warning"
        
        if disk.percent > 90:
            resource_status["warnings"].append(f"磁盘使用率过高: {disk.percent}%")
            resource_status["status"] = "warning"
        
        if include_detailed:
            resource_status["detailed_info"] = {
                "cpu_count": psutil.cpu_count(),
                "memory_total_gb": round(memory.total / (1024**3), 2),
                "memory_available_gb": round(memory.available / (1024**3), 2),
                "disk_total_gb": round(disk.total / (1024**3), 2),
                "disk_free_gb": round(disk.free / (1024**3), 2)
            }
        
        return resource_status
        
    except Exception as e:
        return {
            "status": "error",
            "error": f"无法获取系统资源信息: {str(e)}"
        }

def _check_tmux_integrity() -> Dict[str, Any]:
    """检查tmux完整性"""
    try:
        # 检查tmux是否运行
        result = subprocess.run(['tmux', 'list-sessions'], 
                              capture_output=True, text=True)
        
        tmux_status = {
            "status": "healthy",
            "tmux_available": result.returncode == 0,
            "issues": []
        }
        
        if result.returncode != 0:
            tmux_status["status"] = "error"
            tmux_status["issues"].append("tmux服务不可用")
            return tmux_status
        
        # 获取tmux会话列表
        tmux_sessions = result.stdout.strip().split('\n') if result.stdout.strip() else []
        registered_sessions = set(_session_registry.list_all_sessions().keys())
        
        # 检查会话一致性
        tmux_session_names = set()
        for line in tmux_sessions:
            if ':' in line:
                session_name = line.split(':')[0]
                tmux_session_names.add(session_name)
        
        # 查找不一致的会话
        orphaned_tmux = tmux_session_names - registered_sessions
        missing_tmux = registered_sessions - tmux_session_names
        
        if orphaned_tmux:
            tmux_status["issues"].append(f"存在未注册的tmux会话: {list(orphaned_tmux)}")
            tmux_status["status"] = "warning"
        
        if missing_tmux:
            tmux_status["issues"].append(f"已注册但tmux中不存在的会话: {list(missing_tmux)}")
            tmux_status["status"] = "warning"
        
        tmux_status.update({
            "tmux_session_count": len(tmux_session_names),
            "registered_session_count": len(registered_sessions),
            "consistency_ratio": len(registered_sessions & tmux_session_names) / max(len(registered_sessions), 1)
        })
        
        return tmux_status
        
    except Exception as e:
        return {
            "status": "error",
            "error": f"tmux完整性检查失败: {str(e)}"
        }

def _check_mcp_components() -> Dict[str, Any]:
    """检查MCP组件状态"""
    components = {
        "status": "healthy",
        "components": {
            "session_registry": {"status": "healthy", "active_sessions": len(_session_registry.active_sessions)},
            "message_system": {"status": "healthy", "total_messages": sum(len(msgs) for msgs in _session_registry.session_messages.values())},
            "relationship_system": {"status": "healthy", "total_relationships": len(_session_registry.session_relationships)}
        }
    }
    
    return components

def _calculate_overall_health_score(components: Dict[str, Any]) -> float:
    """计算总体健康分数"""
    scores = []
    
    # 会话健康分数
    if "sessions" in components and "health_ratio" in components["sessions"]:
        scores.append(components["sessions"]["health_ratio"])
    
    # 系统资源分数
    if "system_resources" in components:
        sys_score = 1.0
        if components["system_resources"]["status"] == "warning":
            sys_score = 0.6
        elif components["system_resources"]["status"] == "error":
            sys_score = 0.0
        scores.append(sys_score)
    
    # tmux分数
    if "tmux" in components:
        tmux_score = components["tmux"].get("consistency_ratio", 1.0)
        if components["tmux"]["status"] == "error":
            tmux_score = 0.0
        scores.append(tmux_score)
    
    return sum(scores) / len(scores) if scores else 0.0

def _determine_health_status(score: float) -> Dict[str, Any]:
    """根据分数确定健康状态"""
    if score >= 0.9:
        return "excellent"
    elif score >= 0.7:
        return "good"
    elif score >= 0.5:
        return "fair"
    elif score >= 0.3:
        return "poor"
    else:
        return "critical"

def _generate_health_recommendations(health_report: Dict[str, Any]) -> List[str]:
    """生成健康建议"""
    recommendations = []
    
    # 基于组件状态生成建议
    components = health_report.get("components", {})
    
    if "system_resources" in components:
        sys_res = components["system_resources"]
        for warning in sys_res.get("warnings", []):
            if "CPU" in warning:
                recommendations.append("考虑关闭不必要的进程以降低CPU使用率")
            elif "内存" in warning:
                recommendations.append("考虑清理内存或增加swap空间")
            elif "磁盘" in warning:
                recommendations.append("清理磁盘空间或扩展存储")
    
    if "tmux" in components and components["tmux"]["status"] != "healthy":
        recommendations.append("检查tmux会话一致性，清理孤儿会话")
    
    if "sessions" in components:
        health_ratio = components["sessions"].get("health_ratio", 1.0)
        if health_ratio < 0.8:
            recommendations.append("检查并清理不健康的会话")
    
    return recommendations

# 过度设计的辅助函数已移除：
# - _diagnose_single_session: 单会话诊断
# - _generate_diagnosis_recommendations: 诊断建议生成
# - _assess_diagnosis_severity: 诊断严重程度评估
# - _collect_system_performance_metrics: 系统性能指标收集
# - _collect_session_performance_metrics: 会话性能指标收集
# - _collect_tmux_performance_metrics: tmux性能指标收集
# - _collect_historical_metrics: 历史指标收集
# - _generate_performance_summary: 性能摘要生成
#
# 保留的辅助函数只服务于check_system_health基础功能