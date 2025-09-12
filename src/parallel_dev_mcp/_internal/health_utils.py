"""
Health Utils - 健康检查工具函数

从mcp_server/coordinator/status_monitor.py完美迁移而来的健康检查函数。
专注于会话健康分数计算，支持监控层使用。
"""

from datetime import datetime
from typing import Dict, Any


def calculate_session_health_score(session_dict: Dict[str, Any]) -> float:
    """
    计算会话健康分数
    
    从coordinator/status_monitor.py完美迁移而来的算法。
    基于活动时间、消息数量等因素综合评估。
    
    Args:
        session_dict: 会话信息字典
        
    Returns:
        健康分数 (0.0 - 1.0)
    """
    score = 1.0
    
    # 检查活动时间
    try:
        last_activity = datetime.fromisoformat(session_dict.get("last_activity", ""))
        hours_since_activity = (datetime.now() - last_activity).total_seconds() / 3600
        if hours_since_activity > 24:
            score -= 0.3
        elif hours_since_activity > 6:
            score -= 0.1
    except:
        score -= 0.2
    
    # 检查消息数量
    message_count = session_dict.get("message_count", 0)
    if message_count == 0:
        score -= 0.1
    
    return max(0.0, score)


def assess_system_health_level(score: float) -> str:
    """
    根据分数评估健康级别
    
    Args:
        score: 健康分数 (0.0 - 1.0)
        
    Returns:
        健康级别字符串
    """
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


def calculate_average_health_score(sessions: Dict[str, Any]) -> float:
    """
    计算平均健康分数
    
    Args:
        sessions: 会话信息字典
        
    Returns:
        平均健康分数
    """
    if not sessions:
        return 1.0
    
    total_score = 0.0
    count = 0
    
    for session_info in sessions.values():
        if hasattr(session_info, 'to_dict'):
            session_dict = session_info.to_dict()
        else:
            session_dict = session_info
            
        score = calculate_session_health_score(session_dict)
        total_score += score
        count += 1
    
    return total_score / count if count > 0 else 1.0


def generate_health_summary(sessions: Dict[str, Any]) -> Dict[str, Any]:
    """
    生成健康摘要报告
    
    Args:
        sessions: 会话信息字典
        
    Returns:
        健康摘要字典
    """
    if not sessions:
        return {
            "total_sessions": 0,
            "healthy_sessions": 0,
            "warning_sessions": 0, 
            "critical_sessions": 0,
            "average_score": 1.0,
            "health_ratio": 1.0
        }
    
    scores = []
    healthy_count = 0
    warning_count = 0
    critical_count = 0
    
    for session_info in sessions.values():
        if hasattr(session_info, 'to_dict'):
            session_dict = session_info.to_dict()
        else:
            session_dict = session_info
            
        score = calculate_session_health_score(session_dict)
        scores.append(score)
        
        if score >= 0.8:
            healthy_count += 1
        elif score >= 0.5:
            warning_count += 1
        else:
            critical_count += 1
    
    return {
        "total_sessions": len(sessions),
        "healthy_sessions": healthy_count,
        "warning_sessions": warning_count,
        "critical_sessions": critical_count,
        "average_score": sum(scores) / len(scores),
        "health_ratio": healthy_count / len(sessions)
    }