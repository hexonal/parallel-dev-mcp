"""
Simple Tmux Session Manager - 纯会话管理

专注于tmux会话管理，不涉及配置文件生成。
配置生成应该是用户工具，不是核心MCP功能。
"""

import json
import time
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

from .tmux_operations import TmuxOperations


class TmuxSessionManager:
    """简化的会话管理器 - 只管理会话，不生成配置"""
    
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.master_session = f"parallel_{project_id}_task_master"
        self.child_sessions = {}
        
        # 基础目录设置（仅用于消息存储）
        self.project_dir = Path("projects") / project_id
        
        # 组件注入
        self.tmux = TmuxOperations()
    
    def init_project(self, tasks: List[str]) -> Dict[str, Any]:
        """初始化项目 - 仅创建必要目录"""
        try:
            # 确保项目目录存在
            self.project_dir.mkdir(parents=True, exist_ok=True)
            message_dir = self.project_dir / "messages"
            message_dir.mkdir(exist_ok=True)
            
            return {
                "success": True,
                "status": "initialized",
                "project_id": self.project_id,
                "project_dir": str(self.project_dir),
                "tasks": tasks,
                "message": "项目初始化完成。请使用配置工具生成Claude配置。"
            }
            
        except Exception as e:
            return {"success": False, "error": f"初始化失败: {str(e)}"}
    
    def start_all_sessions(self, tasks: List[str]) -> Dict[str, Any]:
        """启动所有会话"""
        if not self.tmux.is_available():
            return {"error": "tmux不可用，请确保已安装tmux"}
        
        try:
            created_sessions = []
            errors = []
            
            # 创建主会话
            self._create_master_session(created_sessions, errors)
            
            # 创建子会话
            self._create_child_sessions(tasks, created_sessions, errors)
            
            # 等待会话初始化
            time.sleep(1)
            
            # 验证会话健康状态
            session_status = self._verify_sessions_health(created_sessions)
            
            return {
                "success": len(created_sessions) > 0,
                "created_sessions": created_sessions,
                "errors": errors,
                "session_health": session_status,
                "attach_commands": self._get_attach_commands(tasks)
            }
            
        except Exception as e:
            return {"error": f"启动会话失败: {str(e)}"}
    
    def get_project_status(self) -> Dict[str, Any]:
        """获取项目状态"""
        try:
            all_sessions = self.tmux.list_sessions()
            project_sessions = self._filter_project_sessions(all_sessions)
            
            healthy_sessions = 0
            session_details = {}
            
            for session in project_sessions:
                session_name = session['name']
                health_info = self._check_session_health(session_name)
                session_details[session_name] = health_info
                
                if health_info.get("healthy", False):
                    healthy_sessions += 1
            
            return {
                "success": True,
                "project_id": self.project_id,
                "timestamp": datetime.now().isoformat(),
                "total_sessions": len(project_sessions),
                "healthy_sessions": healthy_sessions,
                "health_ratio": healthy_sessions / max(len(project_sessions), 1),
                "session_details": session_details,
                "all_healthy": healthy_sessions == len(project_sessions)
            }
            
        except Exception as e:
            return {"error": f"获取状态失败: {str(e)}"}
    
    def send_inter_session_message(self, from_session: str, to_session: str, message: str) -> Dict[str, Any]:
        """会话间消息发送"""
        try:
            message_id = f"msg_{int(time.time() * 1000)}"
            timestamp = datetime.now().isoformat()
            
            # 通过文件系统发送消息
            result = self._send_via_file_system(from_session, to_session, message, message_id, timestamp)
            
            return {
                "success": result.get("status") == "success",
                "message_id": message_id,
                "from_session": from_session,
                "to_session": to_session,
                "timestamp": timestamp,
                "delivery_method": result
            }
            
        except Exception as e:
            return {"error": f"发送消息失败: {str(e)}"}
    
    def get_attach_instructions(self, session_type: str = "master") -> Dict[str, Any]:
        """获取会话连接说明"""
        try:
            if session_type == "master":
                return {
                    "session_type": "master",
                    "command": f"tmux attach-session -t {self.master_session}",
                    "session_name": self.master_session,
                    "description": "连接到项目主协调会话"
                }
            elif session_type == "list":
                return self._get_all_child_sessions_info()
            else:
                return {"error": f"未知的会话类型: {session_type}"}
        
        except Exception as e:
            return {"error": f"获取连接说明失败: {str(e)}"}
    
    def cleanup_project(self) -> Dict[str, Any]:
        """清理项目"""
        try:
            all_sessions = self.tmux.list_sessions()
            project_sessions = self._filter_project_sessions(all_sessions)
            
            killed_sessions = []
            errors = []
            
            for session in project_sessions:
                session_name = session['name']
                if self.tmux.kill_session(session_name):
                    killed_sessions.append(session_name)
                else:
                    errors.append(f"无法终止会话: {session_name}")
            
            # 清理消息目录
            message_dir = self.project_dir / "messages"
            if message_dir.exists():
                import shutil
                shutil.rmtree(message_dir)
                message_dir.mkdir(exist_ok=True)
            
            return {
                "success": len(errors) == 0,
                "project_id": self.project_id,
                "killed_sessions": killed_sessions,
                "total_killed": len(killed_sessions),
                "errors": errors
            }
            
        except Exception as e:
            return {"error": f"清理失败: {str(e)}"}
    
    def list_all_sessions(self) -> Dict[str, Any]:
        """列出所有会话"""
        try:
            all_sessions = self.tmux.list_sessions()
            project_sessions = self._filter_project_sessions(all_sessions)
            other_sessions = [s for s in all_sessions if s not in project_sessions]
            
            return {
                "project_id": self.project_id,
                "project_sessions": project_sessions,
                "project_session_count": len(project_sessions),
                "other_sessions": other_sessions,
                "total_sessions": len(all_sessions)
            }
            
        except Exception as e:
            return {"error": f"列出会话失败: {str(e)}"}
    
    # === 私有辅助方法 ===
    
    def _create_master_session(self, created_sessions: List[str], errors: List[str]):
        """创建主会话"""
        if self.tmux.create_session(self.master_session, env_vars={"PROJECT_ID": self.project_id}):
            created_sessions.append(self.master_session)
        else:
            errors.append(f"无法创建主会话: {self.master_session}")
    
    def _create_child_sessions(self, tasks: List[str], created_sessions: List[str], errors: List[str]):
        """创建子会话"""
        for task in tasks:
            child_session = f"parallel_{self.project_id}_task_child_{task}"
            env_vars = {
                "PROJECT_ID": self.project_id,
                "TASK_ID": task,
                "SESSION_ROLE": "child"
            }
            
            if self.tmux.create_session(child_session, env_vars=env_vars):
                created_sessions.append(child_session)
                self.child_sessions[task] = child_session
            else:
                errors.append(f"无法创建子会话: {child_session}")
    
    def _verify_sessions_health(self, session_names: List[str]) -> Dict[str, Any]:
        """验证会话健康状态"""
        health_status = {}
        for session_name in session_names:
            health_status[session_name] = self._check_session_health(session_name)
        return health_status
    
    def _check_session_health(self, session_name: str) -> Dict[str, Any]:
        """检查单个会话健康状态"""
        try:
            if self.tmux.session_exists(session_name):
                return {"healthy": True, "session_name": session_name}
            else:
                return {"healthy": False, "reason": "会话不存在"}
        except Exception as e:
            return {"healthy": False, "reason": str(e)}
    
    def _filter_project_sessions(self, all_sessions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """过滤项目相关会话"""
        project_sessions = []
        for session in all_sessions:
            session_name = session['name']
            if (session_name.startswith(f"parallel_{self.project_id}_task_")):
                project_sessions.append(session)
        return project_sessions
    
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
            
            # 限制消息数量
            if len(messages) > 100:
                messages = messages[-50:]
            
            # 写入文件
            with open(message_file, 'w') as f:
                json.dump(messages, f, indent=2)
            
            return {
                "status": "success",
                "message_file": str(message_file),
                "total_messages": len(messages)
            }
            
        except Exception as e:
            return {"status": "failed", "error": str(e)}
    
    def _get_attach_commands(self, tasks: List[str]) -> Dict[str, str]:
        """获取连接命令"""
        commands = {"master": f"tmux attach-session -t {self.master_session}"}
        
        for task in tasks:
            child_session = f"parallel_{self.project_id}_task_child_{task}"
            commands[f"child_{task}"] = f"tmux attach-session -t {child_session}"
        
        return commands
    
    def _get_all_child_sessions_info(self) -> Dict[str, Any]:
        """获取所有子会话信息"""
        all_sessions = self.tmux.list_sessions()
        child_sessions = []
        
        for session in all_sessions:
            session_name = session['name']
            if session_name.startswith(f"parallel_{self.project_id}_task_child_"):
                task_id = session_name.split('_')[-1]
                child_sessions.append({
                    "command": f"tmux attach-session -t {session_name}",
                    "session_name": session_name,
                    "task_id": task_id,
                    "attached": session.get('attached', False)
                })
        
        return {
            "session_type": "children",
            "available_child_sessions": child_sessions,
            "description": "所有可用的子任务会话"
        }