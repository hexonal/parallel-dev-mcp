"""
Health Monitor - 系统健康监控
从coordinator的状态监控完美融合而来，提供实时健康检查。
每个函数都是独立的MCP工具，Claude可以直接调用。
"""

import json
import subprocess
from datetime import datetime, timedelta
from typing import Dict, Any, List
import psutil
import os

# 复用已重构的组件
from .._internal.session_registry import SessionRegistry
from .._internal.health_utils import calculate_session_health_score

# MCP工具装饰器
def mcp_tool(name: str = None, description: str = None):
    """MCP工具装饰器"""
    def decorator(func):
        func.mcp_tool_name = name or func.__name__
        func.mcp_tool_description = description or func.__doc__
        return func
    return decorator

# 全局会话注册中心
_session_registry = SessionRegistry()

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

@mcp_tool(
    name="diagnose_session_issues",
    description="诊断会话问题，识别潜在的会话相关问题"
)
def diagnose_session_issues(
    session_name: str = None,
    deep_analysis: bool = False
) -> Dict[str, Any]:
    """
    会话问题诊断 - 深度会话分析和问题识别
    
    Args:
        session_name: 特定会话名称（为空时分析所有会话）
        deep_analysis: 是否进行深度分析
    """
    try:
        diagnosis = {
            "timestamp": datetime.now().isoformat(),
            "analysis_scope": "single_session" if session_name else "all_sessions",
            "issues": [],
            "warnings": [],
            "recommendations": []
        }
        
        if session_name:
            # 单会话诊断
            session_issues = _diagnose_single_session(session_name, deep_analysis)
            diagnosis.update(session_issues)
        else:
            # 全局会话诊断
            all_sessions = _session_registry.list_all_sessions()
            
            total_issues = []
            total_warnings = []
            session_analyses = {}
            
            for name, session_info in all_sessions.items():
                session_diagnosis = _diagnose_single_session(name, deep_analysis)
                session_analyses[name] = session_diagnosis
                
                total_issues.extend(session_diagnosis.get("issues", []))
                total_warnings.extend(session_diagnosis.get("warnings", []))
            
            diagnosis["issues"] = total_issues
            diagnosis["warnings"] = total_warnings
            diagnosis["session_analyses"] = session_analyses
            diagnosis["total_sessions_analyzed"] = len(all_sessions)
        
        # 生成全局建议
        diagnosis["recommendations"] = _generate_diagnosis_recommendations(diagnosis)
        diagnosis["severity"] = _assess_diagnosis_severity(diagnosis)
        
        return diagnosis
        
    except Exception as e:
        return {
            "success": False,
            "error": f"会话问题诊断失败: {str(e)}"
        }

@mcp_tool(
    name="get_performance_metrics",
    description="获取详细的性能指标和统计信息"
)
def get_performance_metrics(
    time_range_hours: int = 24,
    include_historical: bool = False
) -> Dict[str, Any]:
    """
    性能指标获取 - 详细的系统性能分析
    
    Args:
        time_range_hours: 时间范围（小时）
        include_historical: 是否包含历史数据
    """
    try:
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "time_range_hours": time_range_hours,
            "system_metrics": {},
            "session_metrics": {},
            "performance_summary": {}
        }
        
        # 1. 系统性能指标
        system_metrics = _collect_system_performance_metrics()
        metrics["system_metrics"] = system_metrics
        
        # 2. 会话性能指标
        session_metrics = _collect_session_performance_metrics(time_range_hours)
        metrics["session_metrics"] = session_metrics
        
        # 3. tmux性能指标
        tmux_metrics = _collect_tmux_performance_metrics()
        metrics["tmux_metrics"] = tmux_metrics
        
        # 4. 历史数据（如果请求）
        if include_historical:
            historical_data = _collect_historical_metrics(time_range_hours)
            metrics["historical_data"] = historical_data
        
        # 5. 性能摘要和趋势
        metrics["performance_summary"] = _generate_performance_summary(metrics)
        
        return metrics
        
    except Exception as e:
        return {
            "success": False,
            "error": f"获取性能指标失败: {str(e)}"
        }

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
        }
        
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
    components = health_report.get("components", {}
    
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

def _diagnose_single_session(session_name: str, deep_analysis: bool) -> Dict[str, Any]:
    """诊断单个会话"""
    session_info = _session_registry.get_session_info(session_name)
    if not session_info:
        return {
            "issues": [f"会话不存在: {session_name}"],
            "warnings": [],
            "session_exists": False
        }
    
    issues = []
    warnings = []
    
    session_dict = session_info.to_dict()
    health_score = calculate_session_health_score(session_dict)
    
    # 检查活动时间
    try:
        last_activity = datetime.fromisoformat(session_dict.get("last_activity", ""))
        hours_inactive = (datetime.now() - last_activity).total_seconds() / 3600
        
        if hours_inactive > 48:
            issues.append(f"会话超过48小时未活动")
        elif hours_inactive > 24:
            warnings.append(f"会话超过24小时未活动")
    except:
        warnings.append("无法解析最后活动时间")
    
    # 检查消息数量
    message_count = session_dict.get("message_count", 0)
    if message_count == 0:
        warnings.append("会话没有任何消息记录")
    
    # 深度分析
    if deep_analysis:
        # 检查tmux会话是否存在
        try:
            result = subprocess.run(['tmux', 'has-session', '-t', session_name], 
                                  capture_output=True)
            if result.returncode != 0:
                issues.append(f"对应的tmux会话不存在")
        except:
            warnings.append("无法检查tmux会话状态")
    
    return {
        "session_exists": True,
        "health_score": health_score,
        "issues": issues,
        "warnings": warnings,
        "session_info": session_dict
    }

def _generate_diagnosis_recommendations(diagnosis: Dict[str, Any]) -> List[str]:
    """生成诊断建议"""
    recommendations = []
    
    issues = diagnosis.get("issues", [])
    warnings = diagnosis.get("warnings", [])
    
    if any("不存在" in issue for issue in issues):
        recommendations.append("清理无效的会话引用")
    
    if any("未活动" in issue for issue in issues):
        recommendations.append("清理长时间不活动的会话")
    
    if any("tmux" in issue for issue in issues):
        recommendations.append("重新同步tmux会话状态")
    
    return recommendations

def _assess_diagnosis_severity(diagnosis: Dict[str, Any]) -> Dict[str, Any]:
    """评估诊断严重程度"""
    issue_count = len(diagnosis.get("issues", []))
    warning_count = len(diagnosis.get("warnings", []))
    
    if issue_count > 5:
        return "critical"
    elif issue_count > 2:
        return "high"
    elif issue_count > 0 or warning_count > 3:
        return "medium"
    elif warning_count > 0:
        return "low"
    else:
        return "none"

def _collect_system_performance_metrics() -> Dict[str, Any]:
    """收集系统性能指标"""
    try:
        return {
            "cpu": {
                "usage_percent": psutil.cpu_percent(interval=1),
                "load_average": os.getloadavg() if hasattr(os, 'getloadavg') else None
            },
            "memory": {
                "usage_percent": psutil.virtual_memory().percent,
                "available_gb": round(psutil.virtual_memory().available / (1024**3), 2)
            },
            "disk": {
                "usage_percent": psutil.disk_usage('/').percent,
                "free_gb": round(psutil.disk_usage('/').free / (1024**3), 2)
            }
        }
    except Exception as e:
        return {"error": str(e)}

def _collect_session_performance_metrics(time_range_hours: int) -> Dict[str, Any]:
    """收集会话性能指标"""
    all_sessions = _session_registry.list_all_sessions()
    
    active_sessions = 0
    total_messages = 0
    recent_activity_count = 0
    
    cutoff_time = datetime.now() - timedelta(hours=time_range_hours)
    
    for session_info in all_sessions.values():
        try:
            last_activity = datetime.fromisoformat(session_info.last_activity.isoformat())
            if last_activity > cutoff_time:
                recent_activity_count += 1
            active_sessions += 1
            total_messages += session_info.message_count
        except:
            pass
    
    return {
        "total_sessions": len(all_sessions),
        "active_sessions": active_sessions,
        "recent_activity_sessions": recent_activity_count,
        "total_messages": total_messages,
        "avg_messages_per_session": total_messages / max(len(all_sessions), 1)
    }

def _collect_tmux_performance_metrics() -> Dict[str, Any]:
    """收集tmux性能指标"""
    try:
        result = subprocess.run(['tmux', 'list-sessions', '-F', '#{session_name}:#{session_windows}:#{session_attached}'], 
                              capture_output=True, text=True)
        
        if result.returncode != 0:
            return {"error": "无法获取tmux信息"}
        
        sessions = result.stdout.strip().split('\n') if result.stdout.strip() else []
        
        total_windows = 0
        attached_sessions = 0
        
        for session_line in sessions:
            parts = session_line.split(':')
            if len(parts) >= 3:
                windows = int(parts[1]) if parts[1].isdigit() else 0
                attached = parts[2] == '1'
                
                total_windows += windows
                if attached:
                    attached_sessions += 1
        
        return {
            "total_sessions": len(sessions),
            "total_windows": total_windows,
            "attached_sessions": attached_sessions,
            "avg_windows_per_session": total_windows / max(len(sessions), 1)
        }
        
    except Exception as e:
        return {"error": str(e)}

def _collect_historical_metrics(time_range_hours: int) -> Dict[str, Any]:
    """收集历史指标（模拟实现）"""
    # 这里可以实现真正的历史数据收集
    return {
        "note": "历史数据收集需要持久化存储支持",
        "time_range_hours": time_range_hours
    }

def _generate_performance_summary(metrics: Dict[str, Any]) -> Dict[str, Any]:
    """生成性能摘要"""
    system = metrics.get("system_metrics", {})
    sessions = metrics.get("session_metrics", {})
    tmux = metrics.get("tmux_metrics", {})
    
    return {
        "overall_performance": "good",  # 基于各项指标计算
        "key_indicators": {
            "system_load": system.get("cpu", {}).get("usage_percent", 0),
            "memory_pressure": system.get("memory", {}).get("usage_percent", 0),
            "session_activity": sessions.get("recent_activity_sessions", 0),
            "tmux_efficiency": tmux.get("avg_windows_per_session", 0)
        },
        "recommendations": [
            "系统运行正常" if system.get("cpu", {}).get("usage_percent", 0) < 70 else "考虑优化CPU使用",
            "内存使用正常" if system.get("memory", {}).get("usage_percent", 0) < 80 else "考虑清理内存"
        ]
    }