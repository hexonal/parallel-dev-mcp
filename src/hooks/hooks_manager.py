#!/usr/bin/env python3
"""Claude Hooks配置管理器

负责生成、安装和管理Claude Code的hooks配置，实现与MCP服务器的集成。
"""

import json
import os
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List
import subprocess


class HooksManager:
    """Claude Hooks配置管理器"""
    
    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root or os.getcwd())
        self.hooks_dir = self.project_root / "src" / "hooks"
        self.templates_dir = self.hooks_dir
        
    def generate_child_session_hooks(
        self,
        session_name: str,
        master_session_id: str,
        task_id: str,
        project_id: str,
        output_path: str = None
    ) -> str:
        """生成子会话专用的hooks配置
        
        Args:
            session_name: 子会话名称
            master_session_id: 主会话ID
            task_id: 任务ID
            project_id: 项目ID
            output_path: 输出文件路径
            
        Returns:
            生成的hooks配置文件路径
        """
        # 加载模板
        template_path = self.templates_dir / "child_session_hooks.json"
        with open(template_path, 'r', encoding='utf-8') as f:
            hooks_config = json.load(f)
        
        # 定制化配置
        hooks_config["session_info"] = {
            "session_name": session_name,
            "master_session_id": master_session_id,
            "task_id": task_id,
            "project_id": project_id,
            "generated_at": subprocess.check_output(['date', '-Iseconds']).decode().strip()
        }
        
        # 更新环境变量引用为实际值
        env_replacements = {
            "${MASTER_SESSION_ID}": master_session_id,
            "${TASK_ID}": task_id,
            "${PROJECT_ID}": project_id,
            "${SESSION_NAME}": session_name
        }
        
        # 递归替换配置中的变量
        hooks_config = self._replace_variables(hooks_config, env_replacements)
        
        # 生成输出路径
        if not output_path:
            output_path = f"config/hooks/{session_name}_hooks.json"
        
        output_file = self.project_root / output_path
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 写入配置文件
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(hooks_config, f, indent=2, ensure_ascii=False)
        
        print(f"子会话hooks配置已生成: {output_file}")
        return str(output_file)
    
    def generate_master_session_hooks(
        self,
        session_name: str,
        project_id: str,
        output_path: str = None
    ) -> str:
        """生成主会话专用的hooks配置
        
        Args:
            session_name: 主会话名称
            project_id: 项目ID
            output_path: 输出文件路径
            
        Returns:
            生成的hooks配置文件路径
        """
        # 加载模板
        template_path = self.templates_dir / "master_session_hooks.json"
        with open(template_path, 'r', encoding='utf-8') as f:
            hooks_config = json.load(f)
        
        # 定制化配置
        hooks_config["session_info"] = {
            "session_name": session_name,
            "project_id": project_id,
            "generated_at": subprocess.check_output(['date', '-Iseconds']).decode().strip()
        }
        
        # 环境变量替换
        env_replacements = {
            "${PROJECT_ID}": project_id,
            "${MASTER_SESSION_NAME}": session_name
        }
        
        hooks_config = self._replace_variables(hooks_config, env_replacements)
        
        # 生成输出路径
        if not output_path:
            output_path = f"config/hooks/{session_name}_hooks.json"
        
        output_file = self.project_root / output_path
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 写入配置文件
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(hooks_config, f, indent=2, ensure_ascii=False)
        
        print(f"主会话hooks配置已生成: {output_file}")
        return str(output_file)
    
    def install_hooks_config(self, hooks_config_path: str, claude_config_dir: str = None) -> bool:
        """安装hooks配置到Claude Code配置目录
        
        Args:
            hooks_config_path: hooks配置文件路径
            claude_config_dir: Claude配置目录路径
            
        Returns:
            安装是否成功
        """
        try:
            # 默认Claude配置目录
            if not claude_config_dir:
                claude_config_dir = os.path.expanduser("~/.claude")
            
            claude_config_path = Path(claude_config_dir)
            claude_config_path.mkdir(parents=True, exist_ok=True)
            
            # 复制hooks配置
            hooks_file = claude_config_path / "hooks.json"
            shutil.copy2(hooks_config_path, hooks_file)
            
            print(f"Hooks配置已安装到: {hooks_file}")
            return True
            
        except Exception as e:
            print(f"安装hooks配置失败: {e}")
            return False
    
    def create_session_with_hooks(
        self,
        session_type: str,
        session_name: str,
        master_session_id: str = None,
        task_id: str = None,
        project_id: str = "DEFAULT_PROJECT"
    ) -> str:
        """创建带有hooks配置的tmux会话
        
        Args:
            session_type: 会话类型 (master/child)
            session_name: 会话名称
            master_session_id: 主会话ID (子会话需要)
            task_id: 任务ID (子会话需要)
            project_id: 项目ID
            
        Returns:
            创建的会话名称
        """
        try:
            # 生成hooks配置
            if session_type == "master":
                hooks_config_path = self.generate_master_session_hooks(
                    session_name, project_id
                )
            elif session_type == "child":
                if not master_session_id or not task_id:
                    raise ValueError("子会话需要指定master_session_id和task_id")
                
                hooks_config_path = self.generate_child_session_hooks(
                    session_name, master_session_id, task_id, project_id
                )
            else:
                raise ValueError(f"不支持的会话类型: {session_type}")
            
            # 设置环境变量
            env_vars = {
                "SESSION_ROLE": session_type,
                "PROJECT_ID": project_id,
                "HOOKS_CONFIG_PATH": hooks_config_path
            }
            
            if session_type == "child":
                env_vars.update({
                    "MASTER_SESSION_ID": master_session_id,
                    "TASK_ID": task_id,
                    "WORKTREE_PATH": f"../worktrees/task-{task_id}"
                })
            
            # 构建tmux命令
            tmux_cmd = ["tmux", "new-session", "-d", "-s", session_name]
            
            # 添加环境变量
            for key, value in env_vars.items():
                tmux_cmd.extend(["-e", f"{key}={value}"])
            
            # 启动Claude Code
            tmux_cmd.append("claude")
            
            # 执行命令
            result = subprocess.run(tmux_cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"会话已创建: {session_name} ({session_type})")
                
                # 安装hooks配置到会话专用目录
                session_config_dir = f"config/sessions/{session_name}"
                self.install_hooks_config(hooks_config_path, session_config_dir)
                
                return session_name
            else:
                raise subprocess.CalledProcessError(
                    result.returncode, tmux_cmd, result.stderr
                )
                
        except Exception as e:
            print(f"创建会话失败: {e}")
            return None
    
    def _replace_variables(self, obj: Any, replacements: Dict[str, str]) -> Any:
        """递归替换配置对象中的变量"""
        if isinstance(obj, dict):
            return {
                key: self._replace_variables(value, replacements)
                for key, value in obj.items()
            }
        elif isinstance(obj, list):
            return [
                self._replace_variables(item, replacements)
                for item in obj
            ]
        elif isinstance(obj, str):
            result = obj
            for var, value in replacements.items():
                result = result.replace(var, value)
            return result
        else:
            return obj
    
    def list_active_sessions(self) -> List[Dict[str, Any]]:
        """列出所有活跃的会话及其配置"""
        try:
            result = subprocess.run(
                ["tmux", "list-sessions", "-F", "#{session_name}"],
                capture_output=True, text=True
            )
            
            if result.returncode != 0:
                return []
            
            sessions = []
            for session_name in result.stdout.strip().split('\n'):
                if not session_name:
                    continue
                
                # 尝试获取会话环境变量
                env_result = subprocess.run([
                    "tmux", "show-environment", "-t", session_name
                ], capture_output=True, text=True)
                
                session_info = {"session_name": session_name}
                
                if env_result.returncode == 0:
                    for line in env_result.stdout.strip().split('\n'):
                        if '=' in line and not line.startswith('-'):
                            key, value = line.split('=', 1)
                            if key in ['SESSION_ROLE', 'PROJECT_ID', 'TASK_ID', 'MASTER_SESSION_ID']:
                                session_info[key.lower()] = value
                
                sessions.append(session_info)
            
            return sessions
            
        except Exception as e:
            print(f"获取会话列表失败: {e}")
            return []
    
    def cleanup_hooks_configs(self, keep_recent: int = 5):
        """清理旧的hooks配置文件"""
        config_dir = self.project_root / "config" / "hooks"
        
        if not config_dir.exists():
            return
        
        # 获取所有hooks配置文件，按修改时间排序
        config_files = sorted(
            config_dir.glob("*_hooks.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        
        # 保留最近的配置文件，删除其他的
        for old_config in config_files[keep_recent:]:
            try:
                old_config.unlink()
                print(f"已删除旧配置: {old_config}")
            except Exception as e:
                print(f"删除配置失败 {old_config}: {e}")


def main():
    """命令行工具主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Claude Hooks配置管理工具")
    
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # 生成配置命令
    gen_parser = subparsers.add_parser("generate", help="生成hooks配置")
    gen_parser.add_argument("session_type", choices=["master", "child"], help="会话类型")
    gen_parser.add_argument("session_name", help="会话名称")
    gen_parser.add_argument("--project-id", default="DEFAULT_PROJECT", help="项目ID")
    gen_parser.add_argument("--master-session-id", help="主会话ID (子会话需要)")
    gen_parser.add_argument("--task-id", help="任务ID (子会话需要)")
    gen_parser.add_argument("--output", help="输出文件路径")
    
    # 创建会话命令
    create_parser = subparsers.add_parser("create-session", help="创建带hooks的会话")
    create_parser.add_argument("session_type", choices=["master", "child"], help="会话类型")
    create_parser.add_argument("session_name", help="会话名称")
    create_parser.add_argument("--project-id", default="DEFAULT_PROJECT", help="项目ID")
    create_parser.add_argument("--master-session-id", help="主会话ID (子会话需要)")
    create_parser.add_argument("--task-id", help="任务ID (子会话需要)")
    
    # 列出会话命令
    subparsers.add_parser("list-sessions", help="列出活跃会话")
    
    # 清理配置命令
    clean_parser = subparsers.add_parser("cleanup", help="清理旧配置文件")
    clean_parser.add_argument("--keep", type=int, default=5, help="保留最近N个配置文件")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    hooks_manager = HooksManager()
    
    if args.command == "generate":
        if args.session_type == "master":
            hooks_manager.generate_master_session_hooks(
                args.session_name, args.project_id, args.output
            )
        else:  # child
            if not args.master_session_id or not args.task_id:
                print("错误: 子会话需要指定 --master-session-id 和 --task-id")
                return
            
            hooks_manager.generate_child_session_hooks(
                args.session_name, args.master_session_id,
                args.task_id, args.project_id, args.output
            )
    
    elif args.command == "create-session":
        hooks_manager.create_session_with_hooks(
            args.session_type, args.session_name,
            args.master_session_id, args.task_id, args.project_id
        )
    
    elif args.command == "list-sessions":
        sessions = hooks_manager.list_active_sessions()
        print(f"活跃会话 ({len(sessions)}个):")
        for session in sessions:
            session_type = session.get('session_role', 'unknown')
            project_id = session.get('project_id', 'unknown')
            print(f"  - {session['session_name']} ({session_type}, {project_id})")
    
    elif args.command == "cleanup":
        hooks_manager.cleanup_hooks_configs(args.keep)


if __name__ == "__main__":
    main()