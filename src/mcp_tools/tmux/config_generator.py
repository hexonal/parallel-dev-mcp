"""
Configuration Generator - Clean configuration file creation

Focused solely on generating Claude, hooks, and metadata configurations.
Pure functions with no side effects.
"""

import json
from typing import Dict, Any, List
from pathlib import Path
from datetime import datetime


class ConfigGenerator:
    """纯配置生成器，无副作用"""
    
    def __init__(self, project_id: str, project_dir: Path, config_dir: Path):
        self.project_id = project_id
        self.project_dir = project_dir
        self.config_dir = config_dir
    
    def generate_claude_config(self) -> Dict[str, Any]:
        """生成Claude配置文件内容"""
        return {
            "mcpServers": {
                "session-coordinator": {
                    "command": "python",
                    "args": ["-m", "src.mcp_server.session_coordinator"],
                    "env": {
                        "PROJECT_ID": self.project_id,
                        "PROJECT_DIR": str(self.project_dir)
                    }
                },
                "tmux-orchestrator": {
                    "command": "python", 
                    "args": ["-m", "src.mcp_tools.tmux_session_orchestrator"],
                    "env": {
                        "PROJECT_ID": self.project_id
                    }
                }
            }
        }
    
    def generate_master_hooks(self) -> Dict[str, Any]:
        """生成主会话hooks配置"""
        return {
            "user-prompt-submit-hook": {
                "command": [
                    "python", 
                    "-c", 
                    f"import sys, json, os; project_id = os.environ.get('PROJECT_ID', 'unknown'); print(f'🎯 Master会话 [{{project_id}}]: 处理提示 - {{len(sys.argv[1]) if len(sys.argv) > 1 else 0}}字符')",
                    "{{prompt}}"
                ],
                "description": "主会话提示处理Hook - 项目协调和监控"
            },
            "session-start-hook": {
                "command": [
                    "python",
                    "-c",
                    f"import os; project_id = os.environ.get('PROJECT_ID', 'unknown'); print(f'🚀 Master会话启动: 项目 {{project_id}} - 负责协调所有子任务')"
                ],
                "description": "主会话启动Hook"
            },
            "task-completion-hook": {
                "command": [
                    "python",
                    "-c", 
                    f"import os; project_id = os.environ.get('PROJECT_ID', 'unknown'); print(f'✅ Master会话 [{{project_id}}]: 任务完成通知已接收')"
                ],
                "description": "任务完成通知Hook"
            },
            "mcp-connection-hook": {
                "command": [
                    "python",
                    "-c",
                    f"import os; project_id = os.environ.get('PROJECT_ID', 'unknown'); print(f'🔗 Master会话 [{{project_id}}]: MCP连接已建立，开始协调工作')"
                ],
                "description": "MCP连接建立Hook"
            }
        }
    
    def generate_child_hooks(self, task: str) -> Dict[str, Any]:
        """生成子会话hooks配置"""
        return {
            "user-prompt-submit-hook": {
                "command": [
                    "python",
                    "-c", 
                    f"import sys, json, os; project_id = os.environ.get('PROJECT_ID', 'unknown'); task_id = os.environ.get('TASK_ID', 'unknown'); print(f'⚡ Child会话 [{{project_id}}:{{task_id}}]: 处理提示 - {{len(sys.argv[1]) if len(sys.argv) > 1 else 0}}字符')",
                    "{{prompt}}"
                ],
                "description": "子会话提示处理Hook - 具体任务执行"
            },
            "session-start-hook": {
                "command": [
                    "python",
                    "-c",
                    f"import os; project_id = os.environ.get('PROJECT_ID', 'unknown'); task_id = os.environ.get('TASK_ID', 'unknown'); print(f'🔧 Child会话启动: 项目 {{project_id}} - 任务 {{task_id}}')"
                ],
                "description": "子会话启动Hook"
            },
            "progress-report-hook": {
                "command": [
                    "python",
                    "-c",
                    f"import os; project_id = os.environ.get('PROJECT_ID', 'unknown'); task_id = os.environ.get('TASK_ID', 'unknown'); print(f'📊 Child会话 [{{project_id}}:{{task_id}}]: 进度报告已发送到主会话')"
                ],
                "description": "进度报告Hook"
            },
            "task-completion-hook": {
                "command": [
                    "python", 
                    "-c",
                    f"import os; project_id = os.environ.get('PROJECT_ID', 'unknown'); task_id = os.environ.get('TASK_ID', 'unknown'); print(f'🎉 Child会话 [{{project_id}}:{{task_id}}]: 任务完成！通知主会话')"
                ],
                "description": "任务完成Hook"
            },
            "mcp-connection-hook": {
                "command": [
                    "python",
                    "-c", 
                    f"import os; project_id = os.environ.get('PROJECT_ID', 'unknown'); task_id = os.environ.get('TASK_ID', 'unknown'); print(f'🔗 Child会话 [{{project_id}}:{{task_id}}]: MCP连接已建立，准备接收指令')"
                ],
                "description": "MCP连接建立Hook"
            }
        }
    
    def generate_project_metadata(self, tasks: List[str]) -> Dict[str, Any]:
        """生成项目元数据"""
        return {
            "project_id": self.project_id,
            "tasks": tasks,
            "created_at": str(datetime.now()),
            "master_session": f"master_project_{self.project_id}",
            "child_sessions": {
                task: f"child_{self.project_id}_task_{task}" 
                for task in tasks
            }
        }
    
    def generate_claude_start_commands(self, tasks: List[str]) -> Dict[str, Any]:
        """生成Claude启动命令"""
        return {
            "master": f"claude --hooks-config {self.config_dir}/master_hooks.json",
            "children": {
                task: f"claude --hooks-config {self.config_dir}/child_{task}_hooks.json"
                for task in tasks
            }
        }
    
    def write_config_file(self, file_path: Path, content: Dict[str, Any]) -> None:
        """写入配置文件"""
        with open(file_path, 'w') as f:
            json.dump(content, f, indent=2)