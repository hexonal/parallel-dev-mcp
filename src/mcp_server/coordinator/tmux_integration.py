"""
Tmux Integration - Clean integration with tmux orchestrator

Focused on bridging MCP coordinator with tmux operations.
No business logic mixing.
"""

import json
import logging
from typing import Dict, Any, List

# Import the refactored tmux module
try:
    from ...mcp_tools.tmux import tmux_session_orchestrator
    TMUX_ORCHESTRATOR_AVAILABLE = True
except ImportError:
    TMUX_ORCHESTRATOR_AVAILABLE = False
    tmux_session_orchestrator = None

from .session_registry import SessionRegistry


class TmuxIntegration:
    """Tmux集成层 - 纯集成逻辑"""
    
    def __init__(self, registry: SessionRegistry, logger: logging.Logger):
        self.registry = registry
        self.logger = logger
    
    def is_available(self) -> bool:
        """检查tmux编排器是否可用"""
        return TMUX_ORCHESTRATOR_AVAILABLE
    
    def init_project(self, project_id: str, tasks: str) -> Dict[str, Any]:
        """初始化tmux项目"""
        if not self.is_available():
            return {"success": False, "error": "Tmux orchestrator not available"}
        
        try:
            task_list = self._parse_tasks(tasks)
            if not task_list:
                return {"success": False, "error": "At least one task is required"}
            
            result = tmux_session_orchestrator("init", project_id, task_list)
            
            if "error" in result:
                self.logger.error(f"Tmux项目初始化失败: {result['error']}")
                return {"success": False, "error": result["error"], "project_id": project_id}
            
            self.logger.info(f"Tmux项目初始化成功: {project_id}, 任务: {task_list}")
            
            return {
                "success": True,
                "project_id": project_id,
                "tasks_configured": task_list,
                "files_created": result.get("files_created", {}),
                "next_step": "使用 tmux_project_start 启动所有会话",
                "details": result
            }
            
        except Exception as e:
            error_msg = f"初始化tmux项目失败: {str(e)}"
            self.logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    def start_project(self, project_id: str, tasks: str = None) -> Dict[str, Any]:
        """启动tmux项目的所有会话"""
        if not self.is_available():
            return {"success": False, "error": "Tmux orchestrator not available"}
        
        try:
            task_list = self._parse_tasks(tasks) if tasks else self._get_tasks_from_metadata(project_id)
            if not task_list:
                return {"success": False, "error": "No tasks found for project"}
            
            result = tmux_session_orchestrator("start", project_id, task_list)
            
            if "error" in result:
                self.logger.error(f"Tmux会话启动失败: {result['error']}")
                return {"success": False, "error": result["error"], "project_id": project_id}
            
            # 自动注册会话关系到MCP服务器
            self._register_tmux_sessions(result, project_id, task_list)
            
            self.logger.info(f"Tmux项目启动成功: {project_id}, 会话数: {len(result.get('sessions_created', []))}")
            
            return {
                "success": True,
                "project_id": project_id,
                "master_session": result.get("master_session"),
                "child_sessions": result.get("child_sessions", {}),
                "sessions_created": result.get("sessions_created", []),
                "connect_commands": result.get("claude_start_commands", {}),
                "details": result
            }
            
        except Exception as e:
            error_msg = f"启动tmux项目失败: {str(e)}"
            self.logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    def get_project_status(self, project_id: str) -> Dict[str, Any]:
        """获取tmux项目的完整状态"""
        if not self.is_available():
            return {"success": False, "error": "Tmux orchestrator not available"}
        
        try:
            # 获取tmux状态
            tmux_result = tmux_session_orchestrator("status", project_id)
            
            if "error" in tmux_result:
                return {"success": False, "error": tmux_result["error"], "project_id": project_id}
            
            # 获取MCP状态
            master_session = f"master_project_{project_id}"
            mcp_children = self.registry.get_child_sessions(master_session)
            
            # 合并状态信息
            combined_status = self._combine_status_info(tmux_result, master_session, mcp_children, project_id)
            
            self.logger.info(f"获取项目状态: {project_id}, 健康状态: {combined_status['overall_status']}")
            
            return combined_status
            
        except Exception as e:
            error_msg = f"获取项目状态失败: {str(e)}"
            self.logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    def cleanup_project(self, project_id: str) -> Dict[str, Any]:
        """清理tmux项目环境"""
        if not self.is_available():
            return {"success": False, "error": "Tmux orchestrator not available"}
        
        try:
            cleanup_results = {"project_id": project_id, "steps_completed": [], "steps_failed": []}
            
            # 清理tmux会话
            tmux_result = tmux_session_orchestrator("cleanup", project_id)
            if "error" in tmux_result:
                cleanup_results["steps_failed"].append("tmux_cleanup")
                cleanup_results["tmux_error"] = tmux_result["error"]
            else:
                cleanup_results["steps_completed"].append("tmux_cleanup")
                cleanup_results["tmux_sessions_killed"] = tmux_result.get("sessions_killed", [])
            
            # 清理MCP状态 (简化处理)
            try:
                master_session = f"master_project_{project_id}"
                child_sessions = self.registry.get_child_sessions(master_session)
                
                # 记录清理信息 (实际状态会在会话终止时自动清理)
                cleanup_results["steps_completed"].append("mcp_cleanup")
                cleanup_results["mcp_sessions_cleaned"] = [master_session] + child_sessions
                cleanup_results["mcp_note"] = "会话状态将在tmux会话终止时自动清理"
                
            except Exception as e:
                cleanup_results["steps_failed"].append("mcp_cleanup")
                cleanup_results["mcp_error"] = str(e)
            
            success = len(cleanup_results["steps_failed"]) == 0
            
            self.logger.info(f"项目清理完成: {project_id}, 成功: {success}")
            
            return {
                "success": success,
                "project_id": project_id,
                "cleanup_summary": cleanup_results,
                "status": "完全清理" if success else "部分清理"
            }
            
        except Exception as e:
            error_msg = f"清理项目失败: {str(e)}"
            self.logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    def get_session_attach_info(self, project_id: str, session_type: str = "master") -> Dict[str, Any]:
        """获取tmux会话连接信息"""
        if not self.is_available():
            return {"success": False, "error": "Tmux orchestrator not available"}
        
        try:
            result = tmux_session_orchestrator("attach", project_id, session_type=session_type)
            
            if "error" in result:
                return {"success": False, "error": result["error"], "project_id": project_id}
            
            return {"success": True, "project_id": project_id, "attach_info": result}
            
        except Exception as e:
            error_msg = f"获取连接信息失败: {str(e)}"
            self.logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    # === 私有辅助方法 ===
    
    def _parse_tasks(self, tasks: str) -> List[str]:
        """解析任务列表"""
        if not tasks:
            return []
        return [task.strip() for task in tasks.split(",") if task.strip()]
    
    def _get_tasks_from_metadata(self, project_id: str) -> List[str]:
        """从项目元数据获取任务列表"""
        try:
            from pathlib import Path
            metadata_file = Path("projects") / project_id / "project_metadata.json"
            
            if metadata_file.exists():
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                    return metadata.get("tasks", [])
        except Exception:
            pass
        return []
    
    def _register_tmux_sessions(self, result: Dict[str, Any], project_id: str, task_list: List[str]):
        """注册tmux会话到MCP注册中心"""
        master_session = result.get("master_session")
        child_sessions = result.get("child_sessions", {})
        
        # 注册主会话
        if master_session:
            self.registry.register_session(master_session, "master", project_id)
        
        # 注册子会话并建立关系
        for task_id, child_session in child_sessions.items():
            self.registry.register_session(child_session, "child", project_id, task_id)
            if master_session:
                self.registry.register_relationship(master_session, child_session)
                self.logger.info(f"注册会话关系: {child_session} -> {master_session} (任务: {task_id})")
    
    def _combine_status_info(self, tmux_result: Dict[str, Any], master_session: str, 
                           mcp_children: List[str], project_id: str) -> Dict[str, Any]:
        """合并tmux和MCP状态信息"""
        # 基础状态
        combined_status = {
            "success": True,
            "project_id": project_id,
            "tmux_status": tmux_result,
            "mcp_status": {
                "master_session": master_session,
                "registered_children": mcp_children,
                "mcp_child_count": len(mcp_children)
            }
        }
        
        # 分析健康状态
        tmux_healthy = tmux_result.get("all_healthy", False)
        mcp_consistent = len(mcp_children) == len(tmux_result.get("child_sessions", {}))
        
        if tmux_healthy and mcp_consistent:
            combined_status["overall_status"] = "healthy"
            combined_status["health_report"] = "✅ 所有组件状态正常"
        else:
            issues = []
            if not tmux_healthy:
                issues.append("tmux会话异常")
            if not mcp_consistent:
                issues.append("MCP注册不一致")
            
            combined_status["health_report"] = f"⚠️ 发现问题: {', '.join(issues)}"
            combined_status["overall_status"] = "degraded"
        
        return combined_status