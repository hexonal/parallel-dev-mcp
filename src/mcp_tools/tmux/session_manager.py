"""
Session Manager - Clean session lifecycle management

Orchestrates session operations using specialized components.
Each method has a single responsibility.
"""

import json
import time
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

from .tmux_operations import TmuxOperations
from .config_generator import ConfigGenerator


class TmuxSessionManager:
    """清洁的会话管理器 - 单一职责原则"""
    
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.master_session = f"master_project_{project_id}"
        self.child_sessions = {}
        
        # 目录设置
        self.project_dir = Path("projects") / project_id
        self.config_dir = self.project_dir / "config"
        
        # 组件注入
        self.tmux = TmuxOperations()
        self.config_gen = ConfigGenerator(project_id, self.project_dir, self.config_dir)
    
    def init_project(self, tasks: List[str]) -> Dict[str, Any]:
        """初始化项目配置 - 拆分为小函数"""
        try:
            self._ensure_directories_exist()
            config_files = self._create_all_config_files(tasks)
            metadata_file = self._create_project_metadata(tasks)
            
            return self._build_init_success_response(tasks, config_files, metadata_file)
            
        except Exception as e:
            return {"error": f"Initialization failed: {str(e)}"}
    
    def start_all_sessions(self, tasks: List[str]) -> Dict[str, Any]:
        """启动所有会话 - 拆分为小函数"""
        if not self.tmux.is_available():
            return {"error": "tmux is not available or not installed"}
        
        try:
            created_sessions = []
            errors = []
            
            self._create_master_session(created_sessions, errors)
            self._create_child_sessions(tasks, created_sessions, errors)
            
            time.sleep(2)  # 等待会话初始化
            
            session_status = self._verify_sessions_health(created_sessions)
            claude_commands = self.config_gen.generate_claude_start_commands(tasks)
            
            return self._build_start_response(created_sessions, errors, session_status, claude_commands)
            
        except Exception as e:
            self._cleanup_failed_sessions(created_sessions)
            return {"error": f"Failed to start sessions: {str(e)}", "cleaned_up_sessions": created_sessions}
    
    def get_project_status(self) -> Dict[str, Any]:
        """获取项目状态 - 简化逻辑"""
        try:
            all_sessions = self.tmux.list_sessions()
            project_sessions = self._filter_project_sessions(all_sessions)
            health_status = self._check_sessions_health(project_sessions)
            message_stats = self._get_message_queue_stats()
            
            return self._build_status_response(project_sessions, health_status, message_stats)
            
        except Exception as e:
            return {"error": f"Failed to get project status: {str(e)}"}
    
    def send_inter_session_message(self, from_session: str, to_session: str, message: str) -> Dict[str, Any]:
        """会话间消息发送 - 专注核心逻辑"""
        try:
            message_id = f"msg_{int(time.time() * 1000)}"
            timestamp = str(datetime.now())
            
            # 双重发送机制
            mcp_result = self._try_send_via_mcp(from_session, to_session, message, message_id)
            file_result = self._send_via_file_system(from_session, to_session, message, message_id, timestamp)
            
            return self._build_message_response(message_id, from_session, to_session, timestamp, message, mcp_result, file_result)
            
        except Exception as e:
            return {"error": f"Failed to send message: {str(e)}"}
    
    def get_attach_instructions(self, session_type: str = "master") -> Dict[str, Any]:
        """获取会话连接说明 - 简化分支"""
        if session_type == "master":
            return self._get_master_attach_info()
        elif session_type == "list":
            return self._get_all_child_sessions_info()
        else:
            return {"error": f"Unknown session_type: {session_type}. Use 'master' or 'list'"}
    
    def cleanup_project(self) -> Dict[str, Any]:
        """清理项目 - 专注核心清理逻辑"""
        try:
            killed_sessions = []
            errors = []
            
            project_sessions = self._get_project_session_names()
            
            for session_name in project_sessions:
                if self.tmux.kill_session(session_name):
                    killed_sessions.append(session_name)
                else:
                    errors.append(f"Failed to kill session: {session_name}")
            
            self._cleanup_message_directory()
            
            return self._build_cleanup_response(killed_sessions, errors)
            
        except Exception as e:
            return {"error": f"Cleanup failed: {str(e)}"}
    
    def list_all_sessions(self) -> Dict[str, Any]:
        """列出所有会话 - 简化分类逻辑"""
        try:
            all_sessions = self.tmux.list_sessions()
            project_sessions, other_sessions = self._categorize_sessions(all_sessions)
            
            return {
                "project_id": self.project_id,
                "project_sessions": project_sessions,
                "project_session_count": len(project_sessions),
                "other_sessions": other_sessions,
                "total_sessions": len(all_sessions)
            }
            
        except Exception as e:
            return {"error": f"Failed to list sessions: {str(e)}"}
    
    # === 私有辅助方法 - 每个方法<20行 ===
    
    def _ensure_directories_exist(self):
        """确保目录存在"""
        self.project_dir.mkdir(parents=True, exist_ok=True)
        self.config_dir.mkdir(exist_ok=True)
    
    def _create_all_config_files(self, tasks: List[str]) -> List[str]:
        """创建所有配置文件"""
        config_files = []
        
        # Claude配置
        claude_config = self.config_gen.generate_claude_config()
        claude_file = self.config_dir / "claude-config.json"
        self.config_gen.write_config_file(claude_file, claude_config)
        config_files.append(str(claude_file))
        
        # 主会话hooks
        master_hooks = self.config_gen.generate_master_hooks()
        master_file = self.config_dir / "master_hooks.json"
        self.config_gen.write_config_file(master_file, master_hooks)
        config_files.append(str(master_file))
        
        # 子会话hooks
        for task in tasks:
            child_hooks = self.config_gen.generate_child_hooks(task)
            child_file = self.config_dir / f"child_{task}_hooks.json"
            self.config_gen.write_config_file(child_file, child_hooks)
            config_files.append(str(child_file))
        
        return config_files
    
    def _create_project_metadata(self, tasks: List[str]) -> str:
        """创建项目元数据"""
        metadata = self.config_gen.generate_project_metadata(tasks)
        metadata_file = self.project_dir / "project_metadata.json"
        self.config_gen.write_config_file(metadata_file, metadata)
        
        # 创建消息目录
        message_dir = self.project_dir / "messages"
        message_dir.mkdir(exist_ok=True)
        
        return str(metadata_file)
    
    def _build_init_success_response(self, tasks, config_files, metadata_file) -> Dict[str, Any]:
        """构建初始化成功响应"""
        return {
            "success": True,
            "status": "initialized", 
            "project_id": self.project_id,
            "project_dir": str(self.project_dir),
            "tasks_configured": tasks,
            "files_created": {
                "config_files": config_files,
                "metadata": metadata_file
            },
            "next_step": f"tmux_session_orchestrator('start', '{self.project_id}', {tasks})"
        }
    
    def _create_master_session(self, created_sessions: List[str], errors: List[str]):
        """创建主会话"""
        master_env = {
            'PROJECT_ID': self.project_id,
            'SESSION_ROLE': 'master',
            'HOOKS_CONFIG_PATH': str(self.config_dir / "master_hooks.json"),
            'MCP_SERVER_URL': 'http://localhost:8765'
        }
        
        if self.tmux.create_session(self.master_session, master_env):
            created_sessions.append(self.master_session)
        else:
            errors.append(f"Failed to create master session: {self.master_session}")
    
    def _create_child_sessions(self, tasks: List[str], created_sessions: List[str], errors: List[str]):
        """创建子会话"""
        for task in tasks:
            child_session = f"child_{self.project_id}_task_{task}"
            child_env = {
                'PROJECT_ID': self.project_id,
                'TASK_ID': task,
                'SESSION_ROLE': 'child',
                'HOOKS_CONFIG_PATH': str(self.config_dir / f"child_{task}_hooks.json"),
                'MCP_SERVER_URL': 'http://localhost:8765'
            }
            
            if self.tmux.create_session(child_session, child_env):
                created_sessions.append(child_session)
                self.child_sessions[task] = child_session
            else:
                errors.append(f"Failed to create child session: {child_session}")
    
    def _verify_sessions_health(self, session_names: List[str]) -> Dict[str, Any]:
        """验证会话健康状态"""
        health_status = {}
        for session_name in session_names:
            health_status[session_name] = self.tmux.check_session_health(session_name)
        return health_status
    
    def _build_start_response(self, created_sessions, errors, session_status, claude_commands) -> Dict[str, Any]:
        """构建启动响应"""
        result = {
            "success": not errors,
            "status": "started" if not errors else "partially_started",
            "project_id": self.project_id,
            "sessions_created": created_sessions,
            "master_session": self.master_session,
            "child_sessions": self.child_sessions,
            "session_health": session_status,
            "claude_start_commands": claude_commands
        }
        
        if errors:
            result["errors"] = errors
            result["cleanup_needed"] = True
        
        return result
    
    def _cleanup_failed_sessions(self, created_sessions: List[str]):
        """清理失败的会话"""
        for session in created_sessions:
            self.tmux.kill_session(session)
    
    def _filter_project_sessions(self, all_sessions: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """过滤项目相关会话"""
        project_sessions = {'master': [], 'children': []}
        
        for session in all_sessions:
            session_name = session['name']
            if session_name.startswith(f"master_project_{self.project_id}"):
                project_sessions['master'].append(session)
            elif session_name.startswith(f"child_{self.project_id}_task_"):
                project_sessions['children'].append(session)
        
        return project_sessions
    
    def _check_sessions_health(self, project_sessions: Dict[str, List]) -> Dict[str, Any]:
        """检查会话健康状态"""
        health_status = {}
        all_sessions = project_sessions['master'] + project_sessions['children']
        
        for session in all_sessions:
            session_name = session['name']
            health_status[session_name] = self.tmux.check_session_health(session_name)
        
        return health_status
    
    def _get_message_queue_stats(self) -> Dict[str, Any]:
        """获取消息队列统计"""
        try:
            message_dir = self.project_dir / "messages"
            if not message_dir.exists():
                return {"total_files": 0, "total_messages": 0}
            
            stats = {"total_files": 0, "total_messages": 0, "unread_messages": 0}
            
            for message_file in message_dir.glob("*.json"):
                stats["total_files"] += 1
                try:
                    with open(message_file, 'r') as f:
                        messages = json.load(f)
                        stats["total_messages"] += len(messages)
                except Exception:
                    continue
            
            return stats
        except Exception:
            return {"error": "Failed to get message stats"}
    
    def _build_status_response(self, project_sessions, health_status, message_stats) -> Dict[str, Any]:
        """构建状态响应"""
        all_sessions = project_sessions['master'] + project_sessions['children']
        healthy_sessions = sum(1 for session in all_sessions 
                             if health_status.get(session['name'], {}).get('healthy', False))
        
        return {
            "success": True,
            "project_id": self.project_id,
            "timestamp": str(datetime.now()),
            "total_sessions": len(all_sessions),
            "healthy_sessions": healthy_sessions,
            "health_ratio": healthy_sessions / len(all_sessions) if all_sessions else 0,
            "master_session": project_sessions['master'],
            "child_sessions": project_sessions['children'],
            "health_details": health_status,
            "message_queue_stats": message_stats,
            "all_healthy": healthy_sessions == len(all_sessions),
            "attach_commands": self._get_all_attach_commands()
        }
    
    def _try_send_via_mcp(self, from_session: str, to_session: str, message: str, message_id: str) -> Dict[str, Any]:
        """尝试通过MCP发送消息"""
        return {
            "method": "mcp_server",
            "status": "attempted",
            "note": "MCP server integration not implemented yet"
        }
    
    def _send_via_file_system(self, from_session: str, to_session: str, message: str, message_id: str, timestamp: str) -> Dict[str, Any]:
        """通过文件系统发送消息"""
        try:
            message_dir = self.project_dir / "messages"
            message_file = message_dir / f"{to_session}_messages.json"
            
            # 读取现有消息
            messages = []
            if message_file.exists():
                with open(message_file, 'r') as f:
                    messages = json.load(f)
            
            # 添加新消息
            messages.append({
                "id": message_id,
                "from": from_session,
                "to": to_session,
                "message": message,
                "timestamp": timestamp,
                "read": False
            })
            
            # 写入文件
            with open(message_file, 'w') as f:
                json.dump(messages, f, indent=2)
            
            return {
                "method": "file_system",
                "status": "success",
                "message_file": str(message_file),
                "total_messages": len(messages)
            }
        except Exception as e:
            return {"method": "file_system", "status": "failed", "error": str(e)}
    
    def _build_message_response(self, message_id, from_session, to_session, timestamp, message, mcp_result, file_result) -> Dict[str, Any]:
        """构建消息响应"""
        return {
            "status": "sent",
            "message_id": message_id,
            "from_session": from_session,
            "to_session": to_session,
            "timestamp": timestamp,
            "delivery_methods": {
                "mcp_server": mcp_result,
                "file_system": file_result
            },
            "message_preview": message[:100] + "..." if len(message) > 100 else message
        }
    
    def _get_master_attach_info(self) -> Dict[str, Any]:
        """获取主会话连接信息"""
        return {
            "session_type": "master",
            "command": self.tmux.get_attach_command(self.master_session),
            "session_name": self.master_session,
            "description": "连接到项目主协调会话",
            "role": "项目协调和监控"
        }
    
    def _get_all_child_sessions_info(self) -> Dict[str, Any]:
        """获取所有子会话信息"""
        all_sessions = self.tmux.list_sessions()
        child_sessions = []
        
        for session in all_sessions:
            session_name = session['name']
            if session_name.startswith(f"child_{self.project_id}_task_"):
                task_id = session_name.split('_')[-1]
                child_sessions.append({
                    "command": self.tmux.get_attach_command(session_name),
                    "session_name": session_name,
                    "task_id": task_id,
                    "attached": session.get('attached', False)
                })
        
        return {
            "session_type": "children",
            "available_child_sessions": child_sessions,
            "description": "所有可用的子任务会话"
        }
    
    def _get_project_session_names(self) -> List[str]:
        """获取项目相关会话名称"""
        all_sessions = self.tmux.list_sessions()
        project_session_names = []
        
        for session in all_sessions:
            session_name = session['name']
            if (session_name.startswith(f"master_project_{self.project_id}") or 
                session_name.startswith(f"child_{self.project_id}_task_")):
                project_session_names.append(session_name)
        
        return project_session_names
    
    def _cleanup_message_directory(self):
        """清理消息目录"""
        message_dir = self.project_dir / "messages"
        if message_dir.exists():
            import shutil
            shutil.rmtree(message_dir)
            message_dir.mkdir(exist_ok=True)
    
    def _build_cleanup_response(self, killed_sessions, errors) -> Dict[str, Any]:
        """构建清理响应"""
        result = {
            "success": not errors,
            "status": "cleaned" if not errors else "partially_cleaned",
            "project_id": self.project_id,
            "sessions_killed": killed_sessions,
            "total_killed": len(killed_sessions),
            "project_dir": str(self.project_dir)
        }
        
        if errors:
            result["errors"] = errors
        
        return result
    
    def _categorize_sessions(self, all_sessions: List[Dict[str, Any]]) -> tuple:
        """分类会话"""
        project_sessions = []
        other_sessions = []
        
        for session in all_sessions:
            session_name = session['name']
            if (session_name.startswith(f"master_project_{self.project_id}") or 
                session_name.startswith(f"child_{self.project_id}_task_")):
                
                # 识别会话类型
                if session_name.startswith("master_project_"):
                    session_type = "master"
                elif "_task_" in session_name:
                    session_type = "child"
                    task_id = session_name.split('_task_')[-1]
                    session['task_id'] = task_id
                else:
                    session_type = "unknown"
                
                session['type'] = session_type
                project_sessions.append(session)
            else:
                other_sessions.append(session)
        
        return project_sessions, other_sessions
    
    def _get_all_attach_commands(self) -> Dict[str, str]:
        """获取所有会话连接命令"""
        commands = {self.master_session: self.tmux.get_attach_command(self.master_session)}
        
        for task, session_name in self.child_sessions.items():
            commands[session_name] = self.tmux.get_attach_command(session_name)
        
        return commands