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
        """生成Claude配置文件内容 - 支持FastMCP 2.11.3+"""
        return {
            "mcpServers": {
                "parallel-dev-mcp": {
                    "command": "uv", 
                    "args": ["run", "parallel-dev-mcp"],
                    "cwd": str(self.project_dir),
                    "env": {
                        "PROJECT_ID": self.project_id,
                        "PYTHONPATH": str(self.project_dir)
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
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w') as f:
            json.dump(content, f, indent=2)


def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='生成并行开发MCP项目配置')
    parser.add_argument('--project-id', required=True, help='项目ID')
    parser.add_argument('--tasks', nargs='+', required=True, help='任务列表')
    parser.add_argument('--output-dir', default='./configs', help='输出目录 (默认: ./configs)')
    
    args = parser.parse_args()
    
    # 设置路径
    output_dir = Path(args.output_dir)
    project_dir = Path.cwd()
    
    # 创建配置生成器
    generator = ConfigGenerator(args.project_id, project_dir, output_dir)
    
    print(f"🚀 开始生成项目 {args.project_id} 的配置文件...")
    print(f"📁 输出目录: {output_dir}")
    print(f"📋 任务列表: {args.tasks}")
    
    # 生成配置文件
    try:
        # Claude MCP服务器配置
        claude_config = generator.generate_claude_config()
        generator.write_config_file(output_dir / "claude-config.json", claude_config)
        
        # 主会话hooks
        master_hooks = generator.generate_master_hooks()
        generator.write_config_file(output_dir / "master_hooks.json", master_hooks)
        
        # 子会话hooks
        for task in args.tasks:
            child_hooks = generator.generate_child_hooks(task)
            generator.write_config_file(output_dir / f"child_{task}_hooks.json", child_hooks)
        
        # 项目元数据
        metadata = generator.generate_project_metadata(args.tasks)
        generator.write_config_file(output_dir / "project_metadata.json", metadata)
        
        # 启动命令
        commands = generator.generate_claude_start_commands(args.tasks)
        generator.write_config_file(output_dir / "start_commands.json", commands)
        
        print("\n✅ 配置文件生成完成！")
        print("\n📋 生成的文件:")
        for config_file in output_dir.glob("*.json"):
            print(f"  - {config_file.name}")
        
        print(f"\n🚀 下一步:")
        print(f"1. 使用 FastMCP 环境初始化项目:")
        print(f"   uv run python -c \"from parallel_dev_mcp import tmux_session_orchestrator; tmux_session_orchestrator('init', '{args.project_id}', {args.tasks})\"")
        print(f"2. 启动会话:")
        print(f"   uv run python -c \"from parallel_dev_mcp import tmux_session_orchestrator; tmux_session_orchestrator('start', '{args.project_id}', {args.tasks})\"")
        print(f"3. 启动FastMCP服务器:")
        print(f"   uv run parallel-dev-mcp")
        print(f"4. 配置Claude Code:")
        print(f"   将生成的 claude-config.json 内容添加到 Claude Code 的 MCP 服务器配置中")
        
    except Exception as e:
        print(f"❌ 生成配置失败: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())