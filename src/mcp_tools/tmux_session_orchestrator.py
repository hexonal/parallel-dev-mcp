#!/usr/bin/env python3
"""
Tmux会话编排器 - 纯MCP实现
完全替代所有Shell脚本，保持tmux的所有优势
"""

import subprocess
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# MCP装饰器 - 适配实际MCP框架
try:
    from fastmcp import mcp_tool
except ImportError:
    # 开发阶段模拟
    def mcp_tool(name: str = None, description: str = None):
        def decorator(func):
            func._mcp_tool_name = name or func.__name__
            func._mcp_tool_description = description
            return func
        return decorator


@mcp_tool("tmux_session_orchestrator")
def tmux_session_orchestrator(
    action: str,  # init|start|status|message|attach|cleanup|list
    project_id: str,
    tasks: Optional[List[str]] = None,
    from_session: Optional[str] = None,
    to_session: Optional[str] = None,
    message: Optional[str] = None,
    session_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    基于tmux的纯MCP会话编排器
    
    替代功能：
    - setup_claude_code.sh -> init action
    - start_master_*.sh -> start action (master sessions)
    - start_child_*.sh -> start action (child sessions) 
    - status_*.sh -> status action
    - cleanup_*.sh -> cleanup action
    - 会话间通信 -> message action
    
    Args:
        action: 操作类型
        project_id: 项目ID
        tasks: 任务列表 (用于init和start)
        from_session: 发送消息的源会话
        to_session: 接收消息的目标会话
        message: 消息内容
        session_type: 会话类型 (用于attach)
    """
    
    try:
        manager = TmuxSessionManager(project_id)
        
        if action == "init":
            return manager.init_project(tasks or [])
        elif action == "start":
            return manager.start_all_sessions(tasks or [])
        elif action == "status":
            return manager.get_project_status()
        elif action == "message":
            if not all([from_session, to_session, message]):
                return {"error": "message action requires from_session, to_session, and message"}
            return manager.send_inter_session_message(from_session, to_session, message)
        elif action == "attach":
            return manager.get_attach_instructions(session_type or "master")
        elif action == "cleanup":
            return manager.cleanup_project()
        elif action == "list":
            return manager.list_all_sessions()
        else:
            return {"error": f"Unknown action: {action}", "available_actions": [
                "init", "start", "status", "message", "attach", "cleanup", "list"
            ]}
            
    except Exception as e:
        return {
            "error": f"Failed to execute action '{action}': {str(e)}",
            "project_id": project_id,
            "action": action
        }


class TmuxSessionManager:
    """基于tmux的会话管理器 - 纯Python实现"""
    
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.project_dir = Path(f"./projects/{project_id}")
        self.config_dir = self.project_dir / "config"
        self.master_session = f"master_project_{project_id}"
        self.child_sessions = {}
        
        # 确保项目目录存在
        self.project_dir.mkdir(parents=True, exist_ok=True)
        self.config_dir.mkdir(parents=True, exist_ok=True)
    
    def init_project(self, tasks: List[str]) -> Dict[str, Any]:
        """
        初始化项目配置
        替代: setup_claude_code.sh
        """
        
        try:
            # 1. 生成Claude配置文件
            claude_config = self._generate_claude_config()
            claude_config_file = self.config_dir / "claude-config.json"
            with open(claude_config_file, 'w') as f:
                json.dump(claude_config, f, indent=2)
            
            # 2. 生成hooks配置文件
            hooks_configs = self._generate_hooks_configs(tasks)
            hooks_files = []
            
            # 主会话hooks
            master_hooks_file = self.config_dir / "master_hooks.json"
            with open(master_hooks_file, 'w') as f:
                json.dump(hooks_configs['master'], f, indent=2)
            hooks_files.append(str(master_hooks_file))
            
            # 子会话hooks
            for task in tasks:
                child_hooks_file = self.config_dir / f"child_{task}_hooks.json"
                with open(child_hooks_file, 'w') as f:
                    json.dump(hooks_configs['children'][task], f, indent=2)
                hooks_files.append(str(child_hooks_file))
            
            # 3. 生成项目元数据
            metadata = {
                "project_id": self.project_id,
                "tasks": tasks,
                "created_at": str(datetime.now()),
                "master_session": self.master_session,
                "child_sessions": {task: f"child_{self.project_id}_task_{task}" for task in tasks}
            }
            
            metadata_file = self.project_dir / "project_metadata.json"
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            # 4. 创建消息目录
            message_dir = self.project_dir / "messages"
            message_dir.mkdir(exist_ok=True)
            
            return {
                "success": True,
                "status": "initialized", 
                "project_id": self.project_id,
                "project_dir": str(self.project_dir),
                "tasks_configured": tasks,
                "files_created": {
                    "claude_config": str(claude_config_file),
                    "hooks_files": hooks_files,
                    "metadata": str(metadata_file)
                },
                "next_step": f"tmux_session_orchestrator('start', '{self.project_id}', {tasks})"
            }
            
        except Exception as e:
            return {"error": f"Initialization failed: {str(e)}"}
    
    def start_all_sessions(self, tasks: List[str]) -> Dict[str, Any]:
        """
        启动所有会话
        替代: start_master_*.sh 和 start_child_*.sh
        """
        
        created_sessions = []
        errors = []
        
        try:
            # 检查tmux是否可用
            if not self._check_tmux_available():
                return {"error": "tmux is not available or not installed"}
            
            # 1. 创建主会话
            master_env = {
                'PROJECT_ID': self.project_id,
                'SESSION_ROLE': 'master',
                'HOOKS_CONFIG_PATH': str(self.config_dir / "master_hooks.json"),
                'MCP_SERVER_URL': 'http://localhost:8765'
            }
            
            if self._create_tmux_session(self.master_session, master_env):
                created_sessions.append(self.master_session)
            else:
                errors.append(f"Failed to create master session: {self.master_session}")
            
            # 2. 创建所有子会话
            for task in tasks:
                child_session = f"child_{self.project_id}_task_{task}"
                child_env = {
                    'PROJECT_ID': self.project_id,
                    'TASK_ID': task,
                    'SESSION_ROLE': 'child',
                    'HOOKS_CONFIG_PATH': str(self.config_dir / f"child_{task}_hooks.json"),
                    'MCP_SERVER_URL': 'http://localhost:8765'
                }
                
                if self._create_tmux_session(child_session, child_env):
                    created_sessions.append(child_session)
                    self.child_sessions[task] = child_session
                else:
                    errors.append(f"Failed to create child session: {child_session}")
            
            # 3. 等待会话初始化
            time.sleep(2)
            
            # 4. 在每个会话中启动Claude (可选，用户也可手动启动)
            claude_start_commands = self._generate_claude_start_commands()
            
            # 5. 验证会话状态
            session_status = self._verify_sessions_health(created_sessions)
            
            result = {
                "success": not errors,
                "status": "started" if not errors else "partially_started",
                "project_id": self.project_id,
                "sessions_created": created_sessions,
                "master_session": self.master_session,
                "child_sessions": self.child_sessions,
                "session_health": session_status,
                "claude_start_commands": claude_start_commands
            }
            
            if errors:
                result["errors"] = errors
                result["cleanup_needed"] = True
            
            return result
            
        except Exception as e:
            # 清理已创建的会话
            for session in created_sessions:
                self._kill_tmux_session(session)
            
            return {
                "error": f"Failed to start sessions: {str(e)}",
                "cleaned_up_sessions": created_sessions
            }
    
    def get_project_status(self) -> Dict[str, Any]:
        """
        获取项目状态
        替代: status_*.sh
        """
        
        try:
            # 1. 获取所有tmux会话
            all_tmux_sessions = self._list_tmux_sessions()
            
            # 2. 筛选项目相关会话
            project_sessions = {
                'master': None,
                'children': {}
            }
            
            for session_info in all_tmux_sessions:
                session_name = session_info['name']
                
                if session_name == self.master_session:
                    project_sessions['master'] = session_info
                elif session_name.startswith(f"child_{self.project_id}_task_"):
                    task_id = session_name.replace(f"child_{self.project_id}_task_", "")
                    project_sessions['children'][task_id] = session_info
            
            # 3. 检查会话健康状态
            health_status = {}
            total_sessions = 0
            healthy_sessions = 0
            
            if project_sessions['master']:
                health_status['master'] = self._check_session_health(self.master_session)
                total_sessions += 1
                if health_status['master']['healthy']:
                    healthy_sessions += 1
            
            for task_id, session_info in project_sessions['children'].items():
                session_name = f"child_{self.project_id}_task_{task_id}"
                health_status[f'child_{task_id}'] = self._check_session_health(session_name)
                total_sessions += 1
                if health_status[f'child_{task_id}']['healthy']:
                    healthy_sessions += 1
            
            # 4. 检查消息队列状态
            message_stats = self._get_message_queue_stats()
            
            return {
                "success": True,
                "project_id": self.project_id,
                "timestamp": str(datetime.now()),
                "total_sessions": total_sessions,
                "healthy_sessions": healthy_sessions,
                "health_ratio": healthy_sessions / total_sessions if total_sessions > 0 else 0,
                "master_session": project_sessions['master'],
                "child_sessions": project_sessions['children'],
                "health_details": health_status,
                "message_queue_stats": message_stats,
                "all_healthy": healthy_sessions == total_sessions,
                "attach_commands": self._get_attach_commands()
            }
            
        except Exception as e:
            return {"error": f"Failed to get project status: {str(e)}"}
    
    def send_inter_session_message(self, from_session: str, to_session: str, message: str) -> Dict[str, Any]:
        """
        会话间消息发送
        支持通过MCP服务器和文件系统的混合方式
        """
        
        try:
            message_id = f"msg_{int(time.time() * 1000)}_{hash(message) % 1000000}"
            timestamp = str(datetime.now())
            
            # 通过文件系统发送消息
            file_result = self._send_via_file_system(from_session, to_session, message, message_id, timestamp)
            
            return {
                "status": "sent",
                "message_id": message_id,
                "from_session": from_session,
                "to_session": to_session,
                "timestamp": timestamp,
                "delivery_method": file_result,
                "message_preview": message[:100] + "..." if len(message) > 100 else message
            }
            
        except Exception as e:
            return {"error": f"Failed to send message: {str(e)}"}
    
    def get_attach_instructions(self, session_type: str = "master") -> Dict[str, Any]:
        """获取会话连接说明"""
        
        if session_type == "master":
            return {
                "session_type": "master",
                "command": f"tmux attach-session -t {self.master_session}",
                "session_name": self.master_session,
                "description": "连接到项目主协调会话",
                "role": "项目协调和监控"
            }
        elif session_type == "list":
            # 获取所有可用的子会话
            all_sessions = self._list_tmux_sessions()
            child_sessions = {}
            
            for session in all_sessions:
                if session['name'].startswith(f"child_{self.project_id}_task_"):
                    task_id = session['name'].replace(f"child_{self.project_id}_task_", "")
                    child_sessions[task_id] = {
                        "command": f"tmux attach-session -t {session['name']}",
                        "session_name": session['name'],
                        "task_id": task_id,
                        "attached": session.get('attached', False)
                    }
            
            return {
                "session_type": "children",
                "available_child_sessions": child_sessions,
                "description": "所有可用的子任务会话"
            }
        else:
            return {"error": f"Unknown session_type: {session_type}. Use 'master' or 'list'"}
    
    def cleanup_project(self) -> Dict[str, Any]:
        """
        清理项目
        替代: cleanup_*.sh
        """
        
        try:
            killed_sessions = []
            errors = []
            
            # 1. 获取所有相关会话
            all_sessions = self._list_tmux_sessions()
            project_session_names = []
            
            for session in all_sessions:
                session_name = session['name']
                if (session_name.startswith(f"master_project_{self.project_id}") or 
                    session_name.startswith(f"child_{self.project_id}_task_")):
                    project_session_names.append(session_name)
            
            # 2. 终止所有相关会话
            for session_name in project_session_names:
                if self._kill_tmux_session(session_name):
                    killed_sessions.append(session_name)
                else:
                    errors.append(f"Failed to kill session: {session_name}")
            
            # 3. 清理消息文件 (可选)
            message_dir = self.project_dir / "messages"
            if message_dir.exists():
                import shutil
                shutil.rmtree(message_dir)
                message_dir.mkdir(exist_ok=True)
            
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
            
        except Exception as e:
            return {"error": f"Cleanup failed: {str(e)}"}
    
    def list_all_sessions(self) -> Dict[str, Any]:
        """列出所有tmux会话，标识项目相关的会话"""
        
        try:
            all_sessions = self._list_tmux_sessions()
            
            project_sessions = []
            other_sessions = []
            
            for session in all_sessions:
                session_name = session['name']
                if (session_name.startswith(f"master_project_{self.project_id}") or 
                    session_name.startswith(f"child_{self.project_id}_task_")):
                    
                    # 添加项目相关信息
                    session['project_id'] = self.project_id
                    if session_name == self.master_session:
                        session['session_role'] = 'master'
                    else:
                        session['session_role'] = 'child'
                        session['task_id'] = session_name.replace(f"child_{self.project_id}_task_", "")
                    
                    project_sessions.append(session)
                else:
                    other_sessions.append(session)
            
            return {
                "project_id": self.project_id,
                "project_sessions": project_sessions,
                "project_session_count": len(project_sessions),
                "other_sessions": other_sessions,
                "total_sessions": len(all_sessions)
            }
            
        except Exception as e:
            return {"error": f"Failed to list sessions: {str(e)}"}
    
    # === 内部辅助方法 ===
    
    def _check_tmux_available(self) -> bool:
        """检查tmux是否可用"""
        try:
            result = subprocess.run(['tmux', '-V'], capture_output=True, text=True)
            return result.returncode == 0
        except FileNotFoundError:
            return False
    
    def _create_tmux_session(self, session_name: str, env_vars: Dict[str, str]) -> bool:
        """创建tmux会话"""
        try:
            cmd = ['tmux', 'new-session', '-d', '-s', session_name]
            
            # 添加环境变量
            for key, value in env_vars.items():
                cmd.extend(['-e', f'{key}={value}'])
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode == 0
            
        except Exception:
            return False
    
    def _list_tmux_sessions(self) -> List[Dict[str, Any]]:
        """列出所有tmux会话"""
        try:
            result = subprocess.run(
                ['tmux', 'list-sessions', '-F', 
                 '#{session_name}:#{session_created}:#{session_attached}:#{session_windows}'],
                capture_output=True, text=True
            )
            
            if result.returncode != 0:
                return []
            
            sessions = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    parts = line.split(':')
                    if len(parts) >= 4:
                        sessions.append({
                            'name': parts[0],
                            'created': parts[1],
                            'attached': parts[2] == '1',
                            'windows': int(parts[3])
                        })
            
            return sessions
            
        except Exception:
            return []
    
    def _kill_tmux_session(self, session_name: str) -> bool:
        """终止指定tmux会话"""
        try:
            result = subprocess.run(
                ['tmux', 'kill-session', '-t', session_name],
                capture_output=True, text=True
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def _generate_claude_config(self) -> Dict[str, Any]:
        """生成Claude配置文件"""
        return {
            "mcpServers": {
                "tmux-orchestrator": {
                    "command": "python", 
                    "args": ["-m", "src.mcp_tools.tmux_session_orchestrator"],
                    "env": {
                        "PROJECT_ID": self.project_id
                    }
                }
            }
        }
    
    def _generate_hooks_configs(self, tasks: List[str]) -> Dict[str, Any]:
        """生成hooks配置文件"""
        
        # 基础hooks模板
        base_hooks = {
            "user-prompt-submit-hook": {
                "command": ["python", "-c", "import sys; print(f'Hook executed for: {sys.argv[1] if len(sys.argv) > 1 else \"unknown\"}')", "{{prompt}}"],
                "description": "Basic prompt submit hook"
            }
        }
        
        # 主会话hooks
        master_hooks = base_hooks.copy()
        master_hooks.update({
            "session-start-hook": {
                "command": ["python", "-c", f"print('Master session started for project: {self.project_id}')"],
                "description": "Master session startup hook"
            }
        })
        
        # 子会话hooks
        children_hooks = {}
        for task in tasks:
            child_hooks = base_hooks.copy()
            child_hooks.update({
                "session-start-hook": {
                    "command": ["python", "-c", f"print('Child session started for task: {task}')"],
                    "description": f"Child session startup hook for {task}"
                }
            })
            children_hooks[task] = child_hooks
        
        return {
            "master": master_hooks,
            "children": children_hooks
        }
    
    def _generate_claude_start_commands(self) -> Dict[str, str]:
        """生成Claude启动命令"""
        return {
            "master": f"claude --hooks-config {self.config_dir}/master_hooks.json",
            "children": {
                task: f"claude --hooks-config {self.config_dir}/child_{task}_hooks.json"
                for task in self.child_sessions.keys()
            }
        }
    
    def _verify_sessions_health(self, session_names: List[str]) -> Dict[str, Any]:
        """验证会话健康状态"""
        health_status = {}
        
        for session_name in session_names:
            health_status[session_name] = self._check_session_health(session_name)
        
        return health_status
    
    def _check_session_health(self, session_name: str) -> Dict[str, Any]:
        """检查单个会话健康状态"""
        try:
            # 检查会话是否存在
            result = subprocess.run(
                ['tmux', 'has-session', '-t', session_name],
                capture_output=True, text=True
            )
            
            if result.returncode != 0:
                return {"healthy": False, "reason": "Session not found"}
            
            # 检查会话窗口数量
            result = subprocess.run(
                ['tmux', 'display-message', '-t', session_name, '-p', '#{session_windows}'],
                capture_output=True, text=True
            )
            
            if result.returncode == 0:
                windows = int(result.stdout.strip())
                return {
                    "healthy": True,
                    "windows": windows,
                    "session_name": session_name
                }
            else:
                return {"healthy": False, "reason": "Cannot get session info"}
                
        except Exception as e:
            return {"healthy": False, "reason": str(e)}
    
    
    def _send_via_file_system(self, from_session: str, to_session: str, message: str, message_id: str, timestamp: str) -> Dict[str, Any]:
        """通过文件系统发送消息"""
        try:
            message_dir = self.project_dir / "messages"
            message_file = message_dir / f"messages_{to_session}.json"
            
            # 读取现有消息
            messages = []
            if message_file.exists():
                with open(message_file, 'r') as f:
                    messages = json.load(f)
            
            # 添加新消息
            new_message = {
                "id": message_id,
                "from": from_session,
                "to": to_session, 
                "message": message,
                "timestamp": timestamp,
                "read": False
            }
            
            messages.append(new_message)
            
            # 限制消息数量，避免文件过大
            if len(messages) > 100:
                messages = messages[-50:]  # 保留最新50条
            
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
            return {
                "method": "file_system",
                "status": "failed",
                "error": str(e)
            }
    
    def _get_message_queue_stats(self) -> Dict[str, Any]:
        """获取消息队列统计信息"""
        try:
            message_dir = self.project_dir / "messages"
            if not message_dir.exists():
                return {"total_files": 0, "total_messages": 0}
            
            stats = {
                "total_files": 0,
                "total_messages": 0,
                "unread_messages": 0,
                "sessions_with_messages": []
            }
            
            for message_file in message_dir.glob("messages_*.json"):
                stats["total_files"] += 1
                
                try:
                    with open(message_file, 'r') as f:
                        messages = json.load(f)
                        stats["total_messages"] += len(messages)
                        unread = sum(1 for msg in messages if not msg.get("read", False))
                        stats["unread_messages"] += unread
                        
                        if messages:
                            session_name = message_file.stem.replace("messages_", "")
                            stats["sessions_with_messages"].append({
                                "session": session_name,
                                "total": len(messages),
                                "unread": unread
                            })
                except Exception:
                    continue
            
            return stats
            
        except Exception:
            return {"error": "Failed to get message stats"}
    
    def _get_attach_commands(self) -> Dict[str, str]:
        """获取所有会话的连接命令"""
        commands = {}
        
        # 主会话
        commands["master"] = f"tmux attach-session -t {self.master_session}"
        
        # 子会话
        for task, session_name in self.child_sessions.items():
            commands[f"child_{task}"] = f"tmux attach-session -t {session_name}"
        
        return commands


# 用于独立测试的主函数
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python tmux_session_orchestrator.py <action> <project_id> [tasks...]")
        sys.exit(1)
    
    action = sys.argv[1]
    project_id = sys.argv[2]
    tasks = sys.argv[3:] if len(sys.argv) > 3 else []
    
    result = tmux_session_orchestrator(action, project_id, tasks)
    print(json.dumps(result, indent=2))