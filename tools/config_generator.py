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
    
    def generate_smart_hooks(self) -> Dict[str, Any]:
        """生成智能会话识别hooks配置 - 统一处理主会话和子会话"""
        hooks_script_path = str(self.project_dir / "examples/hooks/smart_session_detector.py")
        
        return {
            "user-prompt-submit-hook": {
                "command": [
                    "python", hooks_script_path, "user-prompt", "{{prompt}}"
                ],
                "description": "智能会话提示处理Hook - 自动识别会话类型"
            },
            "session-start-hook": {
                "command": [
                    "python", hooks_script_path, "session-start"
                ],
                "description": "智能会话启动Hook - 自动注册和协调"
            },
            "stop-hook": {
                "command": [
                    "python", hooks_script_path, "stop"
                ],
                "description": "智能任务进度Hook - 自动进度汇报"
            },
            "session-end-hook": {
                "command": [
                    "python", hooks_script_path, "session-end"
                ],
                "description": "智能会话结束Hook - 自动完成通知"
            }
        }
    
    
    def generate_project_metadata(self, tasks: List[str]) -> Dict[str, Any]:
        """生成项目元数据"""
        return {
            "project_id": self.project_id,
            "tasks": tasks,
            "created_at": str(datetime.now()),
            "master_session": f"parallel_{self.project_id}_task_master",
            "child_sessions": {
                task: f"parallel_{self.project_id}_task_child_{task}" 
                for task in tasks
            }
        }
    
    def generate_claude_start_commands(self, tasks: List[str]) -> Dict[str, Any]:
        """生成Claude启动命令 - 使用智能hooks"""
        smart_hooks_config = f"{self.config_dir}/smart_hooks.json"
        
        commands = {
            "smart_hooks_config": smart_hooks_config,
            "master": f"claude --hooks-config {smart_hooks_config}",
            "children": {}
        }
        
        # 所有会话都使用同一个智能hooks配置
        for task in tasks:
            commands["children"][task] = f"claude --hooks-config {smart_hooks_config}"
        
        return commands
    
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
        
        # 智能hooks配置 - 统一处理所有会话类型
        smart_hooks = generator.generate_smart_hooks()
        generator.write_config_file(output_dir / "smart_hooks.json", smart_hooks)
        
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
        print(f"5. 使用智能hooks (所有会话使用同一配置):")
        print(f"   所有tmux会话都使用 smart_hooks.json 进行自动会话识别和通信")
        
    except Exception as e:
        print(f"❌ 生成配置失败: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())