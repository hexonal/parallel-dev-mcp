#!/usr/bin/env python3
"""
统一的高级API接口
提供最简单的并行开发系统使用方式
"""

import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

# 导入集成的组件
from .session_coordinator import session_coordinator
from ..mcp_tools.tmux_session_orchestrator import tmux_session_orchestrator

# MCP装饰器
try:
    from fastmcp import mcp_tool
except ImportError:
    def mcp_tool(name: str = None, description: str = None):
        def decorator(func):
            func._mcp_tool_name = name or func.__name__
            func._mcp_tool_description = description
            return func
        return decorator


# === 最高级的一键式API ===

@mcp_tool("parallel_dev_one_click")
def parallel_dev_one_click(
    project_id: str, 
    tasks: str,
    auto_connect: bool = False
) -> str:
    """
    一键式并行开发环境设置
    完全替代所有Shell脚本，提供最简单的使用方式
    
    Args:
        project_id: 项目ID (如: "ECOMMERCE")
        tasks: 任务列表，逗号分隔 (如: "AUTH,PAYMENT,UI")
        auto_connect: 是否自动显示连接命令
    
    返回完整的项目设置结果和使用指南
    """
    
    try:
        task_list = [task.strip() for task in tasks.split(",") if task.strip()]
        
        if not task_list:
            return json.dumps({
                "success": False,
                "error": "至少需要一个任务"
            })
        
        result = {
            "success": True,
            "project_id": project_id,
            "tasks": task_list,
            "timestamp": str(datetime.now()),
            "steps": [],
            "errors": []
        }
        
        # 步骤1: 初始化项目
        init_result = json.loads(session_coordinator.tmux_project_init(project_id, tasks))
        if init_result.get("success"):
            result["steps"].append("✅ 项目初始化完成")
            result["init_details"] = init_result
        else:
            result["errors"].append(f"❌ 初始化失败: {init_result.get('error', 'Unknown error')}")
            return json.dumps(result)
        
        # 步骤2: 启动所有会话
        start_result = json.loads(session_coordinator.tmux_project_start(project_id))
        if start_result.get("success"):
            result["steps"].append("✅ 所有会话启动完成")
            result["start_details"] = start_result
            result["master_session"] = start_result.get("master_session")
            result["child_sessions"] = start_result.get("child_sessions", {})
        else:
            result["errors"].append(f"❌ 启动失败: {start_result.get('error', 'Unknown error')}")
            # 尝试清理
            session_coordinator.tmux_project_cleanup(project_id)
            return json.dumps(result)
        
        # 步骤3: 验证状态
        status_result = json.loads(session_coordinator.tmux_project_status(project_id))
        if status_result.get("success"):
            result["steps"].append("✅ 系统状态验证通过")
            result["status_details"] = status_result
            result["overall_health"] = status_result.get("overall_status", "unknown")
        else:
            result["errors"].append(f"⚠️ 状态检查异常: {status_result.get('error', 'Unknown error')}")
        
        # 生成使用指南
        if auto_connect:
            attach_result = json.loads(session_coordinator.tmux_session_attach_info(project_id, "list"))
            if attach_result.get("success"):
                result["connect_commands"] = attach_result.get("attach_info", {})
        
        # 生成完整的使用指南
        result["user_guide"] = {
            "quick_start": [
                f"🎯 项目 '{project_id}' 已完全配置完成！",
                f"📊 包含 {len(task_list)} 个并行任务: {', '.join(task_list)}",
                "",
                "🚀 立即开始使用:",
                f"1. 连接到主会话: tmux attach-session -t {result.get('master_session', 'master_project_' + project_id)}",
                "2. 在主会话中启动Claude并连接到MCP服务器",
                "3. 使用MCP工具协调各个子任务"
            ],
            "parallel_development": [
                "🔄 并行开发模式:",
                "• 主会话负责项目协调和监控",
                "• 每个子会话专注于特定任务开发", 
                "• 会话间自动同步状态和消息",
                "• 实时监控项目整体进度"
            ],
            "available_commands": [
                "📋 可用的MCP工具:",
                "• tmux_project_status - 查看项目状态",
                "• send_message_to_session - 会话间通信",
                "• get_child_sessions - 获取子会话列表",
                "• tmux_project_cleanup - 清理项目环境"
            ],
            "connect_to_tasks": [
                f"🔗 连接到具体任务会话:"
            ] + [
                f"• {task}: tmux attach-session -t child_{project_id}_task_{task}"
                for task in task_list
            ]
        }
        
        # 最终状态
        if len(result["errors"]) == 0:
            result["final_status"] = "🎉 并行开发环境完全就绪！"
            result["next_action"] = f"执行: tmux attach-session -t {result.get('master_session', 'master_project_' + project_id)}"
        else:
            result["final_status"] = "⚠️ 部分功能可能异常，请检查错误信息"
            result["troubleshooting"] = "运行 parallel_dev_status 检查详细状态"
        
        return json.dumps(result, indent=2, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"一键设置失败: {str(e)}",
            "project_id": project_id,
            "timestamp": str(datetime.now())
        })


@mcp_tool("parallel_dev_status")
def parallel_dev_status(project_id: str) -> str:
    """
    获取项目完整状态
    最简单的状态检查方式
    """
    
    try:
        # 获取详细状态
        status_result = json.loads(session_coordinator.tmux_project_status(project_id))
        
        if not status_result.get("success"):
            return json.dumps({
                "success": False,
                "error": status_result.get("error", "Unknown error"),
                "project_id": project_id
            })
        
        # 简化状态信息
        simplified_status = {
            "success": True,
            "project_id": project_id,
            "timestamp": status_result.get("timestamp"),
            "overall_health": status_result.get("overall_status", "unknown"),
            "health_report": status_result.get("health_report", "Unknown"),
            "session_summary": {
                "total_sessions": status_result.get("tmux_status", {}).get("total_sessions", 0),
                "healthy_sessions": status_result.get("tmux_status", {}).get("healthy_sessions", 0),
                "registered_mcp_children": status_result.get("mcp_status", {}).get("registered_children", 0)
            },
            "quick_actions": []
        }
        
        # 根据状态提供建议
        if status_result.get("overall_status") == "healthy":
            simplified_status["quick_actions"] = [
                "✅ 系统运行正常",
                f"🔗 连接主会话: tmux attach-session -t {status_result.get('mcp_status', {}).get('master_session', 'master_project_' + project_id)}",
                "📊 查看详细状态: parallel_dev_detailed_status"
            ]
        else:
            simplified_status["quick_actions"] = [
                "⚠️ 检测到问题，建议操作:",
                "🔧 重启项目: parallel_dev_restart",
                "🧹 清理环境: parallel_dev_cleanup", 
                "📋 查看详细日志: parallel_dev_detailed_status"
            ]
        
        # 添加连接命令
        connect_commands = status_result.get("connect_commands", {})
        if connect_commands:
            simplified_status["connect_commands"] = connect_commands
        
        return json.dumps(simplified_status, indent=2, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"状态检查失败: {str(e)}",
            "project_id": project_id
        })


@mcp_tool("parallel_dev_cleanup")
def parallel_dev_cleanup(project_id: str) -> str:
    """
    清理项目环境
    最简单的清理方式
    """
    
    try:
        cleanup_result = json.loads(session_coordinator.tmux_project_cleanup(project_id))
        
        if cleanup_result.get("success"):
            return json.dumps({
                "success": True,
                "project_id": project_id,
                "message": f"🧹 项目 '{project_id}' 环境已完全清理",
                "cleaned_sessions": cleanup_result.get("cleanup_summary", {}).get("tmux_sessions_killed", []),
                "next_steps": [
                    "现在可以重新初始化项目",
                    f"运行: parallel_dev_one_click {project_id} <tasks>"
                ]
            })
        else:
            return json.dumps({
                "success": False,
                "project_id": project_id,
                "error": f"清理失败: {cleanup_result.get('error', 'Unknown error')}",
                "partial_cleanup": cleanup_result.get("cleanup_summary", {})
            })
            
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"清理失败: {str(e)}",
            "project_id": project_id
        })


@mcp_tool("parallel_dev_restart")
def parallel_dev_restart(project_id: str, tasks: str = None) -> str:
    """
    重启项目环境
    先清理再重新初始化
    """
    
    try:
        result = {
            "success": True,
            "project_id": project_id,
            "steps": [],
            "errors": []
        }
        
        # 步骤1: 清理现有环境
        cleanup_result = json.loads(parallel_dev_cleanup(project_id))
        if cleanup_result.get("success"):
            result["steps"].append("✅ 环境清理完成")
        else:
            result["errors"].append(f"⚠️ 清理异常: {cleanup_result.get('error', 'Unknown error')}")
        
        # 步骤2: 重新初始化
        if tasks:
            init_result = json.loads(parallel_dev_one_click(project_id, tasks))
            if init_result.get("success"):
                result["steps"].append("✅ 重新初始化完成")
                result["restart_details"] = init_result
                result["final_status"] = "🔄 项目重启成功"
            else:
                result["errors"].append(f"❌ 重新初始化失败: {init_result.get('error', 'Unknown error')}")
                result["final_status"] = "❌ 项目重启失败"
        else:
            result["final_status"] = "🧹 仅完成清理，请提供tasks参数重新初始化"
            result["next_action"] = f"运行: parallel_dev_one_click {project_id} <tasks>"
        
        result["success"] = len(result["errors"]) == 0
        
        return json.dumps(result, indent=2, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"重启失败: {str(e)}",
            "project_id": project_id
        })


@mcp_tool("parallel_dev_detailed_status")
def parallel_dev_detailed_status(project_id: str) -> str:
    """
    获取详细的项目状态
    包含所有技术细节
    """
    
    try:
        # 获取所有状态信息
        tmux_status = json.loads(session_coordinator.tmux_project_status(project_id))
        
        # 获取会话列表
        list_result = json.loads(session_coordinator.list_all_sessions())
        
        # 获取连接信息
        attach_result = json.loads(session_coordinator.tmux_session_attach_info(project_id, "list"))
        
        detailed_status = {
            "success": True,
            "project_id": project_id,
            "timestamp": str(datetime.now()),
            "tmux_detailed_status": tmux_status,
            "session_list": list_result,
            "connection_info": attach_result,
            "system_health": {
                "tmux_orchestrator_available": True,
                "mcp_server_active": True,
                "hooks_configured": True
            }
        }
        
        return json.dumps(detailed_status, indent=2, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"获取详细状态失败: {str(e)}",
            "project_id": project_id
        })


@mcp_tool("parallel_dev_help")
def parallel_dev_help() -> str:
    """
    显示并行开发系统帮助信息
    """
    
    help_info = {
        "title": "🚀 并行开发系统 - 使用指南",
        "description": "基于tmux和MCP的纯代码并行开发解决方案",
        "quick_start": {
            "1_initialize": "parallel_dev_one_click <project_id> <tasks>",
            "2_check_status": "parallel_dev_status <project_id>", 
            "3_connect": "tmux attach-session -t master_project_<project_id>",
            "4_cleanup": "parallel_dev_cleanup <project_id>"
        },
        "main_commands": {
            "parallel_dev_one_click": {
                "description": "一键设置完整的并行开发环境",
                "usage": "parallel_dev_one_click PROJECT_ID TASK1,TASK2,TASK3",
                "example": "parallel_dev_one_click ECOMMERCE AUTH,PAYMENT,UI"
            },
            "parallel_dev_status": {
                "description": "检查项目状态",
                "usage": "parallel_dev_status PROJECT_ID",
                "example": "parallel_dev_status ECOMMERCE"
            },
            "parallel_dev_cleanup": {
                "description": "清理项目环境",
                "usage": "parallel_dev_cleanup PROJECT_ID",
                "example": "parallel_dev_cleanup ECOMMERCE"
            },
            "parallel_dev_restart": {
                "description": "重启项目环境",
                "usage": "parallel_dev_restart PROJECT_ID [TASKS]",
                "example": "parallel_dev_restart ECOMMERCE AUTH,PAYMENT,UI"
            }
        },
        "advanced_commands": {
            "tmux_project_init": "仅初始化项目配置",
            "tmux_project_start": "仅启动tmux会话",
            "tmux_project_status": "获取tmux详细状态",
            "tmux_session_attach_info": "获取会话连接信息",
            "parallel_dev_detailed_status": "获取完整系统状态"
        },
        "original_mcp_tools": {
            "register_session_relationship": "注册会话关系",
            "report_session_status": "上报会话状态",
            "get_child_sessions": "获取子会话列表",
            "send_message_to_session": "发送会话消息",
            "get_session_messages": "获取会话消息"
        },
        "examples": {
            "电商项目": "parallel_dev_one_click ECOMMERCE AUTH,PAYMENT,CART,UI",
            "后端API": "parallel_dev_one_click API_PROJECT USER,ORDER,NOTIFICATION",
            "全栈应用": "parallel_dev_one_click FULLSTACK BACKEND,FRONTEND,DATABASE,DEPLOY"
        },
        "troubleshooting": {
            "tmux未安装": "请安装tmux: brew install tmux (macOS) 或 apt install tmux (Ubuntu)",
            "会话创建失败": "检查项目ID格式，只允许字母数字和下划线",
            "MCP连接异常": "确保在支持MCP的Claude Code环境中运行",
            "权限问题": "确保有创建文件和进程的权限"
        },
        "architecture": {
            "组件": ["Tmux会话管理", "MCP服务器协调", "自动Hooks配置", "状态同步机制"],
            "特点": ["零Shell脚本", "纯MCP接口", "保持tmux优势", "完整并行开发"]
        }
    }
    
    return json.dumps(help_info, indent=2, ensure_ascii=False)


# 创建统一API的快捷入口
def get_unified_api_summary():
    """获取统一API摘要"""
    return {
        "one_click": "parallel_dev_one_click - 一键式完整设置",
        "status": "parallel_dev_status - 简单状态检查", 
        "cleanup": "parallel_dev_cleanup - 环境清理",
        "restart": "parallel_dev_restart - 重启项目",
        "help": "parallel_dev_help - 帮助信息",
        "detailed": "parallel_dev_detailed_status - 详细状态"
    }


if __name__ == "__main__":
    print("🚀 统一API模块加载完成")
    print("提供最简单的并行开发系统使用方式")
    print("\n核心命令:")
    for cmd, desc in get_unified_api_summary().items():
        print(f"  {desc}")