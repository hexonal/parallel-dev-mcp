"""
Session Manager - 融合server能力的会话管理工具

从coordinator完美融合而来，提供细粒度会话管理。
每个函数都是独立的MCP工具，Claude可以直接调用。
"""

import json
import logging
import os
import subprocess
from datetime import datetime
from typing import Dict, Any

# 复用已重构的注册中心组件
from ..tmux.session_manager import TmuxSessionManager
from .._internal.session_registry import SessionRegistry

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
    name="create_development_session",
    description="创建开发会话，支持tmux集成和环境配置"
)
def create_development_session(
    project_id: str, 
    session_type: str = "master",
    task_id: str = None,
    working_directory: str = None
) -> Dict[str, Any]:
    """
    创建开发会话 - 细粒度会话控制
    
    Args:
        project_id: 项目ID
        session_type: 会话类型 (master/child)
        task_id: 任务ID (子会话必需)
        working_directory: 工作目录
    """
    try:
        # 参数验证
        if session_type not in ["master", "child"]:
            return {
                "success": False,
                "error": f"无效的会话类型: {session_type}。必须是 'master' 或 'child'"
            }
        
        if session_type == "child" and not task_id:
            return {
                "success": False,
                "error": "子会话必须指定task_id"
            }
        
        # 生成会话名称
        if session_type == "master":
            session_name = f"parallel_{project_id}_task_master"
        else:
            session_name = f"parallel_{project_id}_task_child_{task_id}"
        
        # 检查会话是否已存在
        if session_name in _session_registry.active_sessions:
            return {
                "success": False,
                "error": f"会话已存在: {session_name}"
            }
        
        # 创建tmux会话 
        tmux_result = _create_tmux_session(session_name, working_directory, session_type, project_id, task_id)
        if not tmux_result["success"]:
            return tmux_result
        
        # 注册到MCP系统
        _session_registry.register_session(session_name, session_type, project_id, task_id)
        
        # 建立父子关系
        if session_type == "child":
            master_session = f"parallel_{project_id}_task_master"
            _session_registry.register_relationship(master_session, session_name)
        
        result = {
            "success": True,
            "session_name": session_name,
            "session_type": session_type,
            "project_id": project_id,
            "task_id": task_id,
            "tmux_info": tmux_result,
            "connect_command": f"tmux attach-session -t {session_name}"
        }
        
        return result
        
    except Exception as e:
        return {"success": False, "error": f"创建开发会话失败: {str(e)}"}

@mcp_tool(
    name="terminate_session",
    description="终止会话，清理tmux会话和MCP状态"
)
def terminate_session(session_name: str) -> Dict[str, Any]:
    """
    终止会话 - 完整清理会话状态
    
    Args:
        session_name: 要终止的会话名称
    """
    try:
        # 清理MCP状态
        mcp_cleanup = _cleanup_mcp_session(session_name)
        
        # 终止tmux会话
        tmux_cleanup = _kill_tmux_session(session_name)
        
        result = {
            "success": True,
            "session_name": session_name,
            "mcp_cleanup": mcp_cleanup,
            "tmux_cleanup": tmux_cleanup
        }
        
        return result
        
    except Exception as e:
        return {"success": False, "error": f"终止会话失败: {str(e)}"}

@mcp_tool(
    name="query_session_status", 
    description="查询指定会话或所有会话的详细状态"
)
def query_session_status(session_name: str = None) -> Dict[str, Any]:
    """
    查询会话状态 - 详细状态信息
    
    Args:
        session_name: 会话名称，为空时返回所有会话状态
    """
    try:
        if session_name:
            # 单个会话状态
            session_info = _session_registry.get_session_info(session_name)
            if not session_info:
                return {"success": False, "error": f"会话不存在: {session_name}"}
            
            session_dict = session_info.to_dict()
            session_dict["health_score"] = _calculate_session_health_score(session_dict)
            session_dict["tmux_info"] = _get_tmux_session_info(session_name)
            
            return {"success": True, "session": session_dict}, indent=2)
        else:
            # 所有会话状态
            all_sessions = _session_registry.list_all_sessions()
            session_statuses = {}
            
            for name, info in all_sessions.items():
                session_dict = info.to_dict()
                session_dict["health_score"] = _calculate_session_health_score(session_dict)
                session_dict["tmux_info"] = _get_tmux_session_info(name)
                session_statuses[name] = session_dict
            
            return {
                "success": True,
                "total_sessions": len(session_statuses),
                "sessions": session_statuses,
                "summary": _generate_session_summary(session_statuses)
            }, indent=2)
            
    except Exception as e:
        return {"success": False, "error": f"查询会话状态失败: {str(e)}"}

@mcp_tool(
    name="list_all_managed_sessions",
    description="列出所有MCP管理的会话，包含tmux状态对比"
)
def list_all_managed_sessions() -> Dict[str, Any]:
    """
    列出所有管理的会话 - 完整会话清单
    """
    try:
        all_sessions = _session_registry.list_all_sessions()
        tmux_sessions = _get_all_tmux_sessions()
        
        return {
            "success": True,
            "mcp_managed_sessions": {name: info.to_dict() for name, info in all_sessions.items()},
            "tmux_sessions": tmux_sessions,
            "total_mcp_sessions": len(all_sessions),
            "total_tmux_sessions": len(tmux_sessions),
            "query_time": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {"success": False, "error": f"列出会话失败: {str(e)}"}

# === 内部辅助函数 ===

def _create_tmux_session(session_name: str, working_directory: str, 
                        session_type: str, project_id: str, task_id: str) -> Dict[str, Any]:
    """创建tmux会话"""
    try:
        working_directory = working_directory or os.getcwd()
        
        # 基本环境变量
        env_vars = {
            'PROJECT_ID': project_id,
            'SESSION_ROLE': session_type
        }
        
        if task_id:
            env_vars['TASK_ID'] = task_id
        
        # 创建tmux会话
        cmd = ['tmux', 'new-session', '-d', '-s', session_name, '-c', working_directory]
        
        # 添加环境变量
        for key, value in env_vars.items():
            cmd.extend(['-e', f'{key}={value}'])
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            return {
                "success": True,
                "session_name": session_name,
                "working_directory": working_directory,
                "environment": env_vars
            }
        else:
            return {
                "success": False,
                "error": f"tmux session creation failed: {result.stderr}"
            }
            
    except Exception as e:
        return {"success": False, "error": f"tmux session creation error: {str(e)}"}

def _kill_tmux_session(session_name: str) -> Dict[str, Any]:
    """终止tmux会话"""
    try:
        result = subprocess.run(['tmux', 'kill-session', '-t', session_name], 
                              capture_output=True, text=True)
        
        return {
            "success": result.returncode == 0,
            "session_name": session_name,
            "output": result.stdout if result.returncode == 0 else result.stderr
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}

def _cleanup_mcp_session(session_name: str) -> Dict[str, Any]:
    """清理MCP会话状态"""
    try:
        # 移除会话注册
        removed = _session_registry.remove_session(session_name)
        
        return {
            "success": removed,
            "session_name": session_name,
            "removed_from_registry": removed
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}

def _get_all_tmux_sessions() -> list:
    """获取所有tmux会话名称"""
    try:
        result = subprocess.run(['tmux', 'list-sessions', '-F', '#{session_name}'], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            return result.stdout.strip().split('\n') if result.stdout.strip() else []
        else:
            return []
            
    except Exception:
        return []

def _get_tmux_session_info(session_name: str) -> Dict[str, Any]:
    """获取tmux会话信息"""
    try:
        result = subprocess.run(
            ['tmux', 'display-message', '-t', session_name, '-p', '#{session_windows}:#{session_attached}'],
            capture_output=True, text=True
        )
        
        if result.returncode == 0:
            parts = result.stdout.strip().split(':')
            return {
                "exists": True,
                "windows": int(parts[0]) if parts[0] else 0,
                "attached": parts[1] == '1' if len(parts) > 1 else False
            }
        else:
            return {"exists": False}
            
    except Exception:
        return {"exists": False, "error": "Check failed"}

def _calculate_session_health_score(session_dict: Dict[str, Any]) -> float:
    """计算会话健康分数"""
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

def _generate_session_summary(session_statuses: Dict[str, Dict]) -> Dict[str, Any]:
    """生成会话摘要"""
    if not session_statuses:
        return {"healthy_count": 0, "total_count": 0, "avg_health_score": 0.0}
    
    health_scores = [s["health_score"] for s in session_statuses.values()]
    healthy_count = sum(1 for score in health_scores if score > 0.8)
    
    return {
        "healthy_count": healthy_count,
        "total_count": len(session_statuses),
        "avg_health_score": sum(health_scores) / len(health_scores),
        "health_ratio": healthy_count / len(session_statuses)
    }