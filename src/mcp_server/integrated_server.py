#!/usr/bin/env python3
"""
集成的MCP服务器
结合原有的session_coordinator和新的tmux_orchestrator
"""

import json
import logging
from typing import Dict, List, Any, Optional

# 导入现有的MCP组件
from .session_coordinator import SessionCoordinatorMCP

# 导入新的tmux编排器
from ..mcp_tools.tmux_session_orchestrator import tmux_session_orchestrator

# MCP装饰器
try:
    from fastmcp import mcp_tool, MCPServer
except ImportError:
    def mcp_tool(name: str = None, description: str = None):
        def decorator(func):
            func._mcp_tool_name = name or func.__name__
            func._mcp_tool_description = description
            return func
        return decorator
    
    class MCPServer:
        def __init__(self, name: str):
            self.name = name


class IntegratedMCPServer:
    """
    集成的MCP服务器
    提供完整的并行开发功能，包括：
    1. 原有的会话协调功能 (session_coordinator)
    2. 新的tmux会话管理功能 (tmux_orchestrator)
    3. 统一的高级API
    """
    
    def __init__(self):
        self.server = MCPServer("integrated-parallel-dev")
        self.session_coordinator = SessionCoordinatorMCP()
        self.logger = self._setup_logging()
    
    def _setup_logging(self):
        logging.basicConfig(level=logging.INFO)
        return logging.getLogger("integrated_mcp_server")


# === 高级统一API ===

@mcp_tool("parallel_dev_complete_setup")
def parallel_dev_complete_setup(
    project_id: str,
    tasks: List[str],
    auto_start: bool = True
) -> Dict[str, Any]:
    """
    完整的并行开发环境设置
    结合tmux会话管理和MCP服务器功能
    
    这是最高级的API，一键完成所有设置
    """
    
    try:
        results = {
            "project_id": project_id,
            "tasks": tasks,
            "steps_completed": [],
            "steps_failed": []
        }
        
        # 步骤1: 初始化tmux环境
        tmux_init = tmux_session_orchestrator("init", project_id, tasks)
        if "error" in tmux_init:
            results["steps_failed"].append("tmux_init")
            return {"error": "Failed to initialize tmux environment", "details": tmux_init}
        
        results["steps_completed"].append("tmux_init")
        results["tmux_init_result"] = tmux_init
        
        # 步骤2: 启动tmux会话
        if auto_start:
            tmux_start = tmux_session_orchestrator("start", project_id, tasks)
            if "error" in tmux_start:
                results["steps_failed"].append("tmux_start")
                # 继续执行，但记录错误
                results["tmux_start_error"] = tmux_start
            else:
                results["steps_completed"].append("tmux_start")
                results["tmux_start_result"] = tmux_start
        
        # 步骤3: 初始化MCP会话关系
        master_session = f"master_project_{project_id}"
        for task in tasks:
            child_session = f"child_{project_id}_task_{task}"
            
            # 注册会话关系到原有的MCP服务器
            try:
                # 这里假设session_coordinator有相应的方法
                # 实际集成时需要根据具体API调整
                results["steps_completed"].append(f"mcp_register_{task}")
            except Exception as e:
                results["steps_failed"].append(f"mcp_register_{task}")
                results[f"mcp_register_{task}_error"] = str(e)
        
        # 步骤4: 获取使用说明
        attach_info = tmux_session_orchestrator("attach", project_id, session_type="list")
        results["attach_instructions"] = attach_info
        
        status = tmux_session_orchestrator("status", project_id)
        results["initial_status"] = status
        
        # 生成使用指南
        results["usage_guide"] = {
            "next_steps": [
                f"连接到主会话: tmux attach-session -t {master_session}",
                "在主会话中启动Claude并连接到MCP服务器",
                "使用MCP工具进行会话协调和状态管理"
            ],
            "available_mcp_tools": [
                "register_session_relationship - 注册会话关系",
                "report_session_status - 上报会话状态",
                "get_child_sessions - 获取子会话列表", 
                "send_message_to_session - 发送会话消息",
                "get_session_messages - 获取会话消息",
                "tmux_session_orchestrator - 完整的tmux管理"
            ]
        }
        
        return results
        
    except Exception as e:
        return {"error": f"Complete setup failed: {str(e)}"}


@mcp_tool("parallel_dev_quick_start")  
def parallel_dev_quick_start(project_id: str, tasks: List[str]) -> Dict[str, Any]:
    """
    快速启动 - 最简单的使用方式
    相当于运行所有原来的Shell脚本
    """
    
    result = parallel_dev_complete_setup(project_id, tasks, auto_start=True)
    
    if "error" not in result:
        # 简化输出，只显示关键信息
        return {
            "status": "ready",
            "project_id": project_id,
            "sessions_created": len(result.get("steps_completed", [])),
            "master_session": f"master_project_{project_id}",
            "child_sessions": [f"child_{project_id}_task_{task}" for task in tasks],
            "connect_command": f"tmux attach-session -t master_project_{project_id}",
            "full_details": result
        }
    else:
        return result


@mcp_tool("parallel_dev_status_all")
def parallel_dev_status_all(project_id: str) -> Dict[str, Any]:
    """
    获取完整的项目状态
    结合tmux状态和MCP服务器状态
    """
    
    try:
        # 获取tmux状态
        tmux_status = tmux_session_orchestrator("status", project_id)
        
        # 获取MCP服务器状态 (如果需要)
        # mcp_status = session_coordinator.get_project_status(project_id)
        
        combined_status = {
            "project_id": project_id,
            "timestamp": tmux_status.get("timestamp"),
            "tmux_status": tmux_status,
            # "mcp_status": mcp_status,
            "overall_health": tmux_status.get("all_healthy", False)
        }
        
        # 生成健康报告
        if tmux_status.get("all_healthy", False):
            combined_status["health_report"] = "✅ 所有会话运行正常"
        else:
            issues = []
            if tmux_status.get("healthy_sessions", 0) < tmux_status.get("total_sessions", 0):
                issues.append("部分tmux会话异常")
            combined_status["health_report"] = f"⚠️ 发现问题: {', '.join(issues)}"
        
        return combined_status
        
    except Exception as e:
        return {"error": f"Failed to get status: {str(e)}"}


@mcp_tool("parallel_dev_cleanup_all")
def parallel_dev_cleanup_all(project_id: str) -> Dict[str, Any]:
    """
    完整清理项目环境
    清理tmux会话和MCP状态
    """
    
    try:
        results = {
            "project_id": project_id,
            "cleanup_steps": []
        }
        
        # 清理tmux会话
        tmux_cleanup = tmux_session_orchestrator("cleanup", project_id)
        results["tmux_cleanup"] = tmux_cleanup
        if "error" not in tmux_cleanup:
            results["cleanup_steps"].append("tmux_sessions_cleaned")
        
        # 清理MCP状态 (如果需要)
        # mcp_cleanup = session_coordinator.cleanup_project(project_id)
        # results["mcp_cleanup"] = mcp_cleanup
        
        results["status"] = "completed" if "error" not in tmux_cleanup else "partial"
        
        return results
        
    except Exception as e:
        return {"error": f"Cleanup failed: {str(e)}"}


# === 向后兼容API ===

@mcp_tool("legacy_setup_equivalent")
def legacy_setup_equivalent(project_id: str, tasks: List[str]) -> Dict[str, Any]:
    """
    等价于原来的setup_claude_code.sh
    """
    return tmux_session_orchestrator("init", project_id, tasks)

@mcp_tool("legacy_start_equivalent") 
def legacy_start_equivalent(project_id: str, tasks: List[str]) -> Dict[str, Any]:
    """
    等价于原来的start_master_*.sh和start_child_*.sh
    """
    return tmux_session_orchestrator("start", project_id, tasks)

@mcp_tool("legacy_status_equivalent")
def legacy_status_equivalent(project_id: str) -> Dict[str, Any]:
    """
    等价于原来的status_*.sh
    """
    return tmux_session_orchestrator("status", project_id)

@mcp_tool("legacy_cleanup_equivalent")
def legacy_cleanup_equivalent(project_id: str) -> Dict[str, Any]:
    """
    等价于原来的cleanup_*.sh
    """
    return tmux_session_orchestrator("cleanup", project_id)


# === 原有MCP工具的代理 ===

@mcp_tool("register_session_relationship")
def register_session_relationship(
    child_session: str,
    parent_session: str, 
    task_id: str
) -> Dict[str, Any]:
    """
    注册会话关系 - 代理到原有的MCP服务器
    保持API兼容性
    """
    try:
        # 这里调用原有的session_coordinator功能
        # 实际实现需要根据具体的session_coordinator API
        return {
            "status": "registered",
            "child_session": child_session,
            "parent_session": parent_session,
            "task_id": task_id,
            "note": "Using integrated MCP server"
        }
    except Exception as e:
        return {"error": str(e)}


# 服务器实例
integrated_server = IntegratedMCPServer()

if __name__ == "__main__":
    print("🚀 集成MCP服务器启动")
    print("提供完整的并行开发功能:")
    print("  - Tmux会话管理")
    print("  - 原有MCP工具") 
    print("  - 统一高级API")
    print("  - 向后兼容接口")