"""
Tmux Executor - Tmux操作抽象层

统一管理所有tmux命令执行，提供清晰的接口和错误处理。
"""

import subprocess
import os
from typing import Dict, Any, List
from .response_builder import ResponseBuilder


class TmuxExecutor:
    """Tmux执行器 - 统一的tmux命令抽象层"""
    
    @staticmethod
    def session_exists(session_name: str) -> bool:
        """检查tmux会话是否存在
        
        Args:
            session_name: 会话名称
            
        Returns:
            bool: 会话是否存在
        """
        try:
            result = subprocess.run(
                ['tmux', 'has-session', '-t', session_name],
                capture_output=True, text=True
            )
            return result.returncode == 0
        except Exception:
            return False
    
    @staticmethod
    def send_command(session_name: str, command: str) -> Dict[str, Any]:
        """向tmux会话发送命令
        
        Args:
            session_name: 会话名称
            command: 要发送的命令
            
        Returns:
            Dict[str, Any]: 执行结果
        """
        try:
            cmd = ['tmux', 'send-keys', '-t', session_name, command, 'Enter']
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                return ResponseBuilder.success(command_sent=command)
            else:
                return ResponseBuilder.error(
                    f"Failed to send command to session {session_name}: {result.stderr}",
                    command=command,
                    stderr=result.stderr
                )
        except Exception as e:
            return ResponseBuilder.error(f"Exception sending command: {str(e)}")
    
    @staticmethod
    def change_directory(session_name: str, directory: str) -> Dict[str, Any]:
        """在tmux会话中切换工作目录
        
        Args:
            session_name: 会话名称  
            directory: 目标目录路径
            
        Returns:
            Dict[str, Any]: 执行结果
        """
        if not os.path.exists(directory):
            return ResponseBuilder.not_found_error("directory", directory)
        
        return TmuxExecutor.send_command(session_name, f"cd {directory}")
    
    @staticmethod
    def create_session(session_name: str, working_directory: str = None, 
                      environment: Dict[str, str] = None) -> Dict[str, Any]:
        """创建新的tmux会话
        
        Args:
            session_name: 会话名称
            working_directory: 工作目录（可选）
            environment: 环境变量（可选）
            
        Returns:
            Dict[str, Any]: 创建结果
        """
        try:
            cmd = ['tmux', 'new-session', '-d', '-s', session_name]
            
            if working_directory:
                if not os.path.exists(working_directory):
                    return ResponseBuilder.not_found_error("working directory", working_directory)
                cmd.extend(['-c', working_directory])
            
            # 添加环境变量
            if environment:
                for key, value in environment.items():
                    cmd.extend(['-e', f'{key}={value}'])
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                return ResponseBuilder.success(
                    session_name=session_name,
                    working_directory=working_directory or os.getcwd(),
                    environment=environment or {}
                )
            else:
                return ResponseBuilder.error(f"Failed to create session: {result.stderr}")
                
        except Exception as e:
            return ResponseBuilder.error(f"Exception creating session: {str(e)}")
    
    @staticmethod
    def kill_session(session_name: str) -> Dict[str, Any]:
        """终止tmux会话
        
        Args:
            session_name: 会话名称
            
        Returns:
            Dict[str, Any]: 终止结果
        """
        try:
            result = subprocess.run(
                ['tmux', 'kill-session', '-t', session_name],
                capture_output=True, text=True
            )
            
            if result.returncode == 0:
                return ResponseBuilder.success(
                    operation="kill_session",
                    session_name=session_name
                )
            else:
                return ResponseBuilder.error(f"Failed to kill session: {result.stderr}")
                
        except Exception as e:
            return ResponseBuilder.error(f"Exception killing session: {str(e)}")
    
    @staticmethod
    def list_sessions() -> Dict[str, Any]:
        """列出所有tmux会话
        
        Returns:
            Dict[str, Any]: 会话列表结果
        """
        try:
            result = subprocess.run(
                ['tmux', 'list-sessions', '-F', '#{session_name}'],
                capture_output=True, text=True
            )
            
            if result.returncode == 0:
                sessions = result.stdout.strip().split('\n') if result.stdout.strip() else []
                return ResponseBuilder.list_result(sessions, total_count=len(sessions))
            else:
                # tmux没有会话时也会返回非0，这是正常情况
                return ResponseBuilder.list_result([])
                
        except Exception as e:
            return ResponseBuilder.error(f"Exception listing sessions: {str(e)}")
    
    @staticmethod
    def get_session_info(session_name: str) -> Dict[str, Any]:
        """获取tmux会话详细信息
        
        Args:
            session_name: 会话名称
            
        Returns:
            Dict[str, Any]: 会话信息
        """
        try:
            result = subprocess.run(
                ['tmux', 'display-message', '-t', session_name, 
                 '-p', '#{session_windows}:#{session_attached}:#{session_created}'],
                capture_output=True, text=True
            )
            
            if result.returncode == 0:
                parts = result.stdout.strip().split(':')
                return ResponseBuilder.success(
                    session_name=session_name,
                    exists=True,
                    windows=int(parts[0]) if parts[0] else 0,
                    attached=parts[1] == '1' if len(parts) > 1 else False,
                    created_time=parts[2] if len(parts) > 2 else None
                )
            else:
                return ResponseBuilder.success(
                    session_name=session_name,
                    exists=False
                )
                
        except Exception as e:
            return ResponseBuilder.error(f"Exception getting session info: {str(e)}")
    
    @staticmethod
    def is_available() -> bool:
        """检查tmux是否可用
        
        Returns:
            bool: tmux是否可用
        """
        try:
            result = subprocess.run(
                ['tmux', '-V'], 
                capture_output=True, text=True
            )
            return result.returncode == 0
        except Exception:
            return False