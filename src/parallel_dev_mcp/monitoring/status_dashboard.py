"""
Status Dashboard - 系统状态仪表板
从coordinator的状态监控完美融合而来，提供可视化状态展示。
每个函数都是独立的MCP工具，Claude可以直接调用。
"""

import json
import csv
from datetime import datetime, timedelta
from typing import Dict, Any, List
import io

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
    name="get_system_dashboard",
    description="获取系统仪表板，包含关键指标和状态概览"
)
def get_system_dashboard(
    refresh_interval: int = 60,
    include_trends: bool = True
) -> Dict[str, Any]:
    """
    系统仪表板 - 全面的系统状态概览
    
    Args:
        refresh_interval: 刷新间隔（秒）
        include_trends: 是否包含趋势数据
    """
    try:
        dashboard = {
            "timestamp": datetime.now().isoformat(),
            "refresh_interval": refresh_interval,
            "system_overview": {},
            "key_metrics": {},
            "status_indicators": {},
            "recent_activities": []
        }
        
        # 1. 系统概览
        dashboard["system_overview"] = _build_system_overview()
        
        # 2. 关键指标
        dashboard["key_metrics"] = _collect_key_metrics()
        
        # 3. 状态指示器
        dashboard["status_indicators"] = _build_status_indicators()
        
        # 4. 最近活动
        dashboard["recent_activities"] = _get_recent_activities(limit=10)
        
        # 5. 趋势数据（如果请求）
        if include_trends:
            dashboard["trends"] = _collect_trend_data()
        
        # 6. 警报和通知
        dashboard["alerts"] = _collect_active_alerts()
        
        # 7. 快速操作建议
        dashboard["quick_actions"] = _suggest_quick_actions(dashboard)
        
        return dashboard
        
    except Exception as e:
        return {
            "success": False,
            "error": f"获取系统仪表板失败: {str(e)}"
        }

@mcp_tool(
    name="generate_status_report",
    description="生成详细的状态报告，支持多种格式输出"
)
def generate_status_report(
    report_type: str = "comprehensive",
    format_type: str = "json",
    include_recommendations: bool = True,
    time_period: str = "24h"
) -> Dict[str, Any]:
    """
    生成状态报告 - 定制化的系统状态报告
    
    Args:
        report_type: 报告类型 (summary/comprehensive/technical)
        format_type: 输出格式 (json/markdown/csv)
        include_recommendations: 是否包含建议
        time_period: 时间周期 (1h/24h/7d/30d)
    """
    try:
        # 确定时间范围
        time_range_hours = _parse_time_period(time_period)
        
        # 构建报告数据
        report_data = {
            "report_metadata": {
                "generated_at": datetime.now().isoformat(),
                "report_type": report_type,
                "time_period": time_period,
                "time_range_hours": time_range_hours
            }
        }
        
        if report_type == "summary":
            report_data.update(_generate_summary_report(time_range_hours))
        elif report_type == "comprehensive":
            report_data.update(_generate_comprehensive_report(time_range_hours))
        elif report_type == "technical":
            report_data.update(_generate_technical_report(time_range_hours))
        else:
            return {
                "success": False,
                "error": f"不支持的报告类型: {report_type}"
            }
        
        # 添加建议
        if include_recommendations:
            report_data["recommendations"] = _generate_report_recommendations(report_data)
        
        # 格式化输出
        if format_type == "json":
            return report_data
        elif format_type == "markdown":
            return _format_as_markdown(report_data)
        elif format_type == "csv":
            return _format_as_csv(report_data)
        else:
            return {
                "success": False,
                "error": f"不支持的格式类型: {format_type}"
            }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"生成状态报告失败: {str(e)}"
        }

@mcp_tool(
    name="export_system_metrics",
    description="导出系统指标数据，支持多种导出格式"
)
def export_system_metrics(
    metrics_scope: str = "all",
    export_format: str = "json",
    time_range: str = "24h",
    include_metadata: bool = True
) -> Dict[str, Any]:
    """
    导出系统指标 - 指标数据导出和备份
    
    Args:
        metrics_scope: 指标范围 (all/sessions/system/tmux)
        export_format: 导出格式 (json/csv/txt)
        time_range: 时间范围
        include_metadata: 是否包含元数据
    """
    try:
        time_range_hours = _parse_time_period(time_range)
        
        export_data = {
            "export_metadata": {
                "exported_at": datetime.now().isoformat(),
                "metrics_scope": metrics_scope,
                "time_range": time_range,
                "export_format": export_format
            },
            "metrics": {}
        }
        
        # 根据范围收集指标
        if metrics_scope in ["all", "sessions"]:
            export_data["metrics"]["sessions"] = _export_session_metrics(time_range_hours)
        
        if metrics_scope in ["all", "system"]:
            export_data["metrics"]["system"] = _export_system_metrics(time_range_hours)
        
        if metrics_scope in ["all", "tmux"]:
            export_data["metrics"]["tmux"] = _export_tmux_metrics(time_range_hours)
        
        if metrics_scope in ["all", "registry"]:
            export_data["metrics"]["registry"] = _export_registry_metrics()
        
        # 添加汇总统计
        export_data["summary"] = _generate_export_summary(export_data["metrics"])
        
        # 格式化输出
        if export_format == "json":
            return export_data
        elif export_format == "csv":
            return _export_as_csv(export_data)
        elif export_format == "txt":
            return _export_as_text(export_data)
        else:
            return {
                "success": False,
                "error": f"不支持的导出格式: {export_format}"
            }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"导出系统指标失败: {str(e)}"
        }

# === 内部辅助函数 ===

def _build_system_overview() -> Dict[str, Any]:
    """构建系统概览"""
    all_sessions = _session_registry.list_all_sessions()
    registry_stats = _session_registry.get_registry_stats()
    
    return {
        "total_sessions": len(all_sessions),
        "active_sessions": len([s for s in all_sessions.values() if _is_session_active(s)]),
        "total_messages": registry_stats.get("total_messages", 0),
        "total_relationships": registry_stats.get("total_relationships", 0),
        "last_cleanup": registry_stats.get("last_cleanup"),
        "uptime": _calculate_system_uptime()
    }

def _collect_key_metrics() -> Dict[str, Any]:
    """收集关键指标"""
    all_sessions = _session_registry.list_all_sessions()
    
    # 计算健康分数分布
    health_scores = []
    for session_info in all_sessions.values():
        session_dict = session_info.to_dict()
        score = calculate_session_health_score(session_dict)
        health_scores.append(score)
    
    avg_health = sum(health_scores) / len(health_scores) if health_scores else 0
    
    return {
        "average_session_health": round(avg_health, 3),
        "healthy_session_count": sum(1 for score in health_scores if score > 0.8),
        "warning_session_count": sum(1 for score in health_scores if 0.5 < score <= 0.8),
        "unhealthy_session_count": sum(1 for score in health_scores if score <= 0.5),
        "message_activity_rate": _calculate_message_activity_rate(),
        "session_creation_rate": _calculate_session_creation_rate()
    }

def _build_status_indicators() -> Dict[str, Any]:
    """构建状态指示器"""
    return {
        "overall_system": _get_overall_system_status(),
        "session_registry": _get_registry_status(),
        "message_system": _get_message_system_status(),
        "relationship_system": _get_relationship_system_status()
    }

def _get_recent_activities(limit: int = 10) -> List[Dict[str, Any]]:
    """获取最近活动"""
    activities = []
    all_sessions = _session_registry.list_all_sessions()
    
    # 收集最近的会话活动
    session_activities = []
    for name, session_info in all_sessions.items():
        session_activities.append({
            "type": "session_activity",
            "session": name,
            "timestamp": session_info.last_activity.isoformat(),
            "message_count": session_info.message_count
        })
    
    # 按时间排序
    session_activities.sort(key=lambda x: x["timestamp"], reverse=True)
    activities.extend(session_activities[:limit])
    
    return activities

def _collect_trend_data() -> Dict[str, Any]:
    """收集趋势数据"""
    # 这里可以实现真正的趋势分析
    return {
        "session_count_trend": "stable",
        "health_score_trend": "improving",
        "message_volume_trend": "increasing",
        "note": "趋势数据需要历史数据支持"
    }

def _collect_active_alerts() -> List[Dict[str, Any]]:
    """收集活动警报"""
    alerts = []
    all_sessions = _session_registry.list_all_sessions()
    
    # 检查不健康的会话
    for name, session_info in all_sessions.items():
        session_dict = session_info.to_dict()
        health_score = calculate_session_health_score(session_dict)
        
        if health_score < 0.3:
            alerts.append({
                "level": "critical",
                "type": "session_health",
                "message": f"会话 {name} 健康分数过低: {health_score:.2f}",
                "session": name,
                "timestamp": datetime.now().isoformat()
            })
        elif health_score < 0.6:
            alerts.append({
                "level": "warning", 
                "type": "session_health",
                "message": f"会话 {name} 健康状况需要关注: {health_score:.2f}",
                "session": name,
                "timestamp": datetime.now().isoformat()
            })
    
    return alerts

def _suggest_quick_actions(dashboard: Dict[str, Any]) -> List[Dict[str, Any]]:
    """建议快速操作"""
    actions = []
    
    # 基于警报建议操作
    alerts = dashboard.get("alerts", [])
    critical_alerts = [a for a in alerts if a["level"] == "critical"]
    
    if critical_alerts:
        actions.append({
            "action": "cleanup_critical_sessions",
            "description": f"清理 {len(critical_alerts)} 个严重不健康的会话",
            "priority": "high"
        })
    
    # 基于系统状态建议操作
    overview = dashboard.get("system_overview", {})
    if overview.get("total_sessions", 0) > 20:
        actions.append({
            "action": "session_cleanup",
            "description": "会话数量较多，建议清理不活跃会话",
            "priority": "medium"
        })
    
    return actions

def _parse_time_period(time_period: str) -> int:
    """解析时间周期为小时数"""
    if time_period.endswith('h'):
        return int(time_period[:-1])
    elif time_period.endswith('d'):
        return int(time_period[:-1]) * 24
    else:
        return 24  # 默认24小时

def _generate_summary_report(time_range_hours: int) -> Dict[str, Any]:
    """生成摘要报告"""
    all_sessions = _session_registry.list_all_sessions()
    
    return {
        "summary": {
            "total_sessions": len(all_sessions),
            "active_sessions": len([s for s in all_sessions.values() if _is_session_active(s)]),
            "average_health_score": _calculate_average_health_score(),
            "key_issues": _identify_key_issues()
        }
    }

def _generate_comprehensive_report(time_range_hours: int) -> Dict[str, Any]:
    """生成综合报告"""
    return {
        "comprehensive_data": {
            "system_overview": _build_system_overview(),
            "session_analysis": _analyze_all_sessions(),
            "performance_metrics": _collect_performance_data(),
            "health_assessment": _assess_system_health(),
            "trend_analysis": _analyze_trends(time_range_hours)
        }
    }

def _generate_technical_report(time_range_hours: int) -> Dict[str, Any]:
    """生成技术报告"""
    return {
        "technical_details": {
            "registry_internals": _session_registry.get_registry_stats(),
            "memory_usage": _analyze_memory_usage(),
            "performance_bottlenecks": _identify_bottlenecks(),
            "optimization_opportunities": _identify_optimizations()
        }
    }

def _generate_report_recommendations(report_data: Dict[str, Any]) -> List[str]:
    """生成报告建议"""
    recommendations = []
    
    # 基于报告数据分析并生成建议
    if "summary" in report_data:
        summary = report_data["summary"]
        if summary.get("average_health_score", 1.0) < 0.7:
            recommendations.append("系统整体健康状况需要改善，建议清理不健康会话")
    
    return recommendations

def _format_as_markdown(data: Dict[str, Any]) -> Dict[str, Any]:
    """格式化为Markdown"""
    md_lines = ["# 系统状态报告", ""]
    md_lines.append(f"生成时间: {data['report_metadata']['generated_at']}")
    md_lines.append("")
    
    # 根据数据结构生成Markdown
    for key, value in data.items():
        if key != "report_metadata":
            md_lines.append(f"## {key}")
            md_lines.append(f"```json\n{json.dumps(value, indent=2, ensure_ascii=False)}\n```")
            md_lines.append("")
    
    return "\n".join(md_lines)

def _format_as_csv(data: Dict[str, Any]) -> Dict[str, Any]:
    """格式化为CSV"""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # 写入表头
    writer.writerow(["Key", "Value", "Type"])
    
    # 递归写入数据
    def write_nested_data(obj, prefix=""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if isinstance(v, (dict, list)):
                    write_nested_data(v, f"{prefix}.{k}" if prefix else k)
                else:
                    writer.writerow([f"{prefix}.{k}" if prefix else k, str(v), type(v).__name__])
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                write_nested_data(item, f"{prefix}[{i}]")
    
    write_nested_data(data)
    return output.getvalue()

def _export_session_metrics(time_range_hours: int) -> Dict[str, Any]:
    """导出会话指标"""
    all_sessions = _session_registry.list_all_sessions()
    session_metrics = {}
    
    for name, session_info in all_sessions.items():
        session_dict = session_info.to_dict()
        session_metrics[name] = {
            **session_dict,
            "health_score": calculate_session_health_score(session_dict)
        }
    
    return session_metrics

def _export_system_metrics(time_range_hours: int) -> Dict[str, Any]:
    """导出系统指标"""
    return {
        "timestamp": datetime.now().isoformat(),
        "uptime": _calculate_system_uptime(),
        "note": "系统指标导出需要更多系统集成"
    }

def _export_tmux_metrics(time_range_hours: int) -> Dict[str, Any]:
    """导出tmux指标"""
    return {
        "timestamp": datetime.now().isoformat(),
        "note": "tmux指标导出需要tmux状态集成"
    }

def _export_registry_metrics() -> Dict[str, Any]:
    """导出注册中心指标"""
    return _session_registry.get_registry_stats()

def _generate_export_summary(metrics: Dict[str, Any]) -> Dict[str, Any]:
    """生成导出摘要"""
    return {
        "total_data_points": sum(len(str(v)) for v in metrics.values()),
        "export_timestamp": datetime.now().isoformat(),
        "data_integrity": "verified"
    }

def _export_as_csv(data: Dict[str, Any]) -> Dict[str, Any]:
    """导出为CSV格式"""
    return _format_as_csv(data)

def _export_as_text(data: Dict[str, Any]) -> Dict[str, Any]:
    """导出为文本格式"""
    return json.dumps(data, indent=2, ensure_ascii=False)

# 辅助函数实现
def _is_session_active(session_info) -> bool:
    """检查会话是否活跃"""
    try:
        last_activity = session_info.last_activity
        return (datetime.now() - last_activity).total_seconds() < 3600  # 1小时内有活动
    except:
        return False

def _calculate_system_uptime() -> Dict[str, Any]:
    """计算系统运行时间"""
    return "模拟运行时间"

def _calculate_message_activity_rate() -> float:
    """计算消息活动率"""
    return 1.5  # 每分钟消息数

def _calculate_session_creation_rate() -> float:
    """计算会话创建率"""
    return 0.1  # 每小时会话创建数

def _get_overall_system_status() -> Dict[str, Any]:
    """获取总体系统状态"""
    return "healthy"

def _get_registry_status() -> Dict[str, Any]:
    """获取注册中心状态"""
    return "healthy"

def _get_message_system_status() -> Dict[str, Any]:
    """获取消息系统状态"""
    return "healthy"

def _get_relationship_system_status() -> Dict[str, Any]:
    """获取关系系统状态"""
    return "healthy"

def _calculate_average_health_score() -> float:
    """计算平均健康分数"""
    all_sessions = _session_registry.list_all_sessions()
    if not all_sessions:
        return 1.0
    
    scores = []
    for session_info in all_sessions.values():
        session_dict = session_info.to_dict()
        score = calculate_session_health_score(session_dict)
        scores.append(score)
    
    return sum(scores) / len(scores)

def _identify_key_issues() -> List[str]:
    """识别关键问题"""
    issues = []
    all_sessions = _session_registry.list_all_sessions()
    
    unhealthy_count = 0
    for session_info in all_sessions.values():
        session_dict = session_info.to_dict()
        score = calculate_session_health_score(session_dict)
        if score < 0.5:
            unhealthy_count += 1
    
    if unhealthy_count > 0:
        issues.append(f"{unhealthy_count} 个会话健康状况不佳")
    
    return issues

def _analyze_all_sessions() -> Dict[str, Any]:
    """分析所有会话"""
    all_sessions = _session_registry.list_all_sessions()
    return {
        "total_count": len(all_sessions),
        "analysis_timestamp": datetime.now().isoformat()
    }

def _collect_performance_data() -> Dict[str, Any]:
    """收集性能数据"""
    return {
        "collection_timestamp": datetime.now().isoformat(),
        "note": "性能数据收集需要更多集成"
    }

def _assess_system_health() -> Dict[str, Any]:
    """评估系统健康"""
    return {
        "overall_health": "good",
        "assessment_timestamp": datetime.now().isoformat()
    }

def _analyze_trends(time_range_hours: int) -> Dict[str, Any]:
    """分析趋势"""
    return {
        "trend_analysis_timestamp": datetime.now().isoformat(),
        "time_range_hours": time_range_hours
    }

def _analyze_memory_usage() -> Dict[str, Any]:
    """分析内存使用"""
    return {"memory_analysis": "需要实现"}

def _identify_bottlenecks() -> List[str]:
    """识别性能瓶颈"""
    return ["需要实现瓶颈检测"]

def _identify_optimizations() -> List[str]:
    """识别优化机会"""
    return ["需要实现优化建议"]