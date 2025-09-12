"""
Tmux Operations - Low-level tmux system interactions

Focused on pure tmux command execution and session management.
No business logic, just clean system operations.
"""

import subprocess
from typing import List, Dict, Any


class TmuxOperations:
    """纯tmux系统操作，无业务逻辑"""
    
    @staticmethod
    def is_available() -> bool:
        """检查tmux是否可用"""
        try:
            result = subprocess.run(['tmux', '-V'], capture_output=True, text=True)
            return result.returncode == 0
        except Exception:
            return False
    
    @staticmethod
    def create_session(session_name: str, env_vars: Dict[str, str]) -> bool:
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
    
    @staticmethod
    def kill_session(session_name: str) -> bool:
        """终止指定tmux会话"""
        try:
            result = subprocess.run(
                ['tmux', 'kill-session', '-t', session_name],
                capture_output=True, text=True
            )
            return result.returncode == 0
        except Exception:
            return False
    
    @staticmethod
    def list_sessions() -> List[Dict[str, Any]]:
        """列出所有tmux会话"""
        try:
            result = subprocess.run(
                ['tmux', 'list-sessions', '-F', '#{session_name}:#{session_created}:#{session_attached}:#{session_windows}'],
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
    
    @staticmethod
    def check_session_health(session_name: str) -> Dict[str, Any]:
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
    
    @staticmethod
    def get_attach_command(session_name: str) -> str:
        """获取会话连接命令"""
        return f"tmux attach-session -t {session_name}"