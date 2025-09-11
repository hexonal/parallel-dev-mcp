"""会话协调系统的工具函数

提供会话命名解析、状态验证和其他辅助功能。
"""

import re
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, Tuple
from .session_models import SessionRole, SessionStatusEnum, SessionRelationship


def parse_session_name(session_name: str) -> Optional[Dict[str, str]]:
    """从会话名称解析会话信息
    
    支持的命名格式:
    - 主会话: master_project_<project_id>
    - 子会话: child_<project_id>_task_<task_id>
    
    Args:
        session_name: 会话名称
        
    Returns:
        解析结果字典，包含role, project_id等信息，解析失败返回None
    """
    # 主会话模式: master_project_PROJECT123
    master_pattern = r'^master_project_([a-zA-Z0-9_]+)$'
    master_match = re.match(master_pattern, session_name)
    if master_match:
        return {
            "role": SessionRole.MASTER.value,
            "project_id": master_match.group(1),
            "session_name": session_name
        }
    
    # 子会话模式: child_PROJECT123_task_AUTH001
    child_pattern = r'^child_([a-zA-Z0-9_]+)_task_([a-zA-Z0-9_]+)$'
    child_match = re.match(child_pattern, session_name)
    if child_match:
        project_id = child_match.group(1)
        task_id = child_match.group(2)
        return {
            "role": SessionRole.CHILD.value,
            "project_id": project_id,
            "task_id": task_id,
            "parent_session": f"master_project_{project_id}",
            "session_name": session_name
        }
    
    return None


def validate_session_name(session_name: str) -> Tuple[bool, str]:
    """验证会话名称格式
    
    Args:
        session_name: 待验证的会话名称
        
    Returns:
        (是否有效, 错误消息)
    """
    if not session_name:
        return False, "会话名称不能为空"
    
    if len(session_name) > 100:
        return False, "会话名称长度不能超过100字符"
    
    # 检查是否符合支持的格式
    parsed = parse_session_name(session_name)
    if not parsed:
        return False, "会话名称格式不正确，应为 'master_project_<id>' 或 'child_<project_id>_task_<task_id>'"
    
    return True, ""


def generate_session_name(role: SessionRole, project_id: str, task_id: Optional[str] = None) -> str:
    """生成标准格式的会话名称
    
    Args:
        role: 会话角色
        project_id: 项目ID
        task_id: 任务ID (仅子会话需要)
        
    Returns:
        生成的会话名称
    """
    if role == SessionRole.MASTER:
        return f"master_project_{project_id}"
    elif role == SessionRole.CHILD:
        if not task_id:
            raise ValueError("子会话必须指定task_id")
        return f"child_{project_id}_task_{task_id}"
    else:
        raise ValueError(f"不支持的会话角色: {role}")


def generate_message_id() -> str:
    """生成唯一的消息ID"""
    return f"msg_{uuid.uuid4().hex[:12]}_{int(datetime.now().timestamp())}"


def validate_status_transition(current_status: SessionStatusEnum, 
                             new_status: SessionStatusEnum) -> Tuple[bool, str]:
    """验证状态转换是否合法
    
    Args:
        current_status: 当前状态
        new_status: 新状态
        
    Returns:
        (是否合法, 错误消息)
    """
    # 定义合法的状态转换路径
    valid_transitions = {
        SessionStatusEnum.UNKNOWN: [
            SessionStatusEnum.STARTING, SessionStatusEnum.STARTED, 
            SessionStatusEnum.WORKING, SessionStatusEnum.TERMINATED
        ],
        SessionStatusEnum.STARTING: [
            SessionStatusEnum.STARTED, SessionStatusEnum.ERROR, 
            SessionStatusEnum.TERMINATED
        ],
        SessionStatusEnum.STARTED: [
            SessionStatusEnum.WORKING, SessionStatusEnum.COMPLETED,
            SessionStatusEnum.BLOCKED, SessionStatusEnum.ERROR,
            SessionStatusEnum.TERMINATED
        ],
        SessionStatusEnum.WORKING: [
            SessionStatusEnum.WORKING, SessionStatusEnum.COMPLETED,
            SessionStatusEnum.BLOCKED, SessionStatusEnum.ERROR,
            SessionStatusEnum.TERMINATED
        ],
        SessionStatusEnum.BLOCKED: [
            SessionStatusEnum.WORKING, SessionStatusEnum.COMPLETED,
            SessionStatusEnum.ERROR, SessionStatusEnum.TERMINATED
        ],
        SessionStatusEnum.ERROR: [
            SessionStatusEnum.STARTING, SessionStatusEnum.WORKING,
            SessionStatusEnum.TERMINATED
        ],
        SessionStatusEnum.COMPLETED: [
            SessionStatusEnum.WORKING, SessionStatusEnum.TERMINATED
        ],
        SessionStatusEnum.TERMINATED: []  # 终止状态不可转换
    }
    
    allowed_transitions = valid_transitions.get(current_status, [])
    if new_status not in allowed_transitions:
        return False, f"不允许从 {current_status.value} 转换到 {new_status.value}"
    
    return True, ""


def calculate_session_health_score(session_status: Dict[str, Any]) -> float:
    """计算会话健康度评分 (0.0 - 1.0)
    
    Args:
        session_status: 会话状态字典
        
    Returns:
        健康度评分
    """
    score = 1.0
    
    # 基于状态的评分
    status = session_status.get('status', 'UNKNOWN')
    status_scores = {
        'WORKING': 1.0,
        'STARTED': 0.8,
        'COMPLETED': 1.0,
        'BLOCKED': 0.3,
        'ERROR': 0.1,
        'TERMINATED': 0.0,
        'UNKNOWN': 0.5
    }
    score *= status_scores.get(status, 0.5)
    
    # 基于最后更新时间的评分
    last_update = session_status.get('last_update')
    if last_update:
        try:
            last_update_time = datetime.fromisoformat(last_update.replace('Z', '+00:00'))
            time_since_update = datetime.now() - last_update_time.replace(tzinfo=None)
            minutes_since_update = time_since_update.total_seconds() / 60
            
            # 超过10分钟没有更新，评分开始降低
            if minutes_since_update > 10:
                time_penalty = min(0.8, minutes_since_update / 60)  # 最多扣0.8分
                score *= (1 - time_penalty)
        except (ValueError, AttributeError):
            score *= 0.8  # 时间格式错误
    
    return max(0.0, min(1.0, score))