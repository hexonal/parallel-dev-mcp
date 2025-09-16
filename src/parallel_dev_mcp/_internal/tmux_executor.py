"""
Tmux Executor - Tmux操作抽象层

统一管理所有tmux命令执行，提供清晰的接口和错误处理。
"""

import subprocess
import os
from typing import Dict, Any, List
from .response_builder import ResponseBuilder
from .tmux_send_gateway import send_to_tmux, get_tmux_gateway


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
        """向tmux会话发送命令（收口版 - 通过统一网关）

        🚨 GATEWAY: 此方法已重构为通过统一网关发送
        **重要更新**: 现在使用TmuxSendGateway进行无引号、分步骤发送
        - 不使用引号包装命令
        - 分两次send-keys：命令内容 + 回车
        - 避免特殊字符转义问题
        - 保证高内聚，统一收口

        Args:
            session_name: 会话名称
            command: 要发送的命令

        Returns:
            Dict[str, Any]: 执行结果
        """
        # 🎯 通过统一网关进行发送（唯一收口）
        result = send_to_tmux(session_name, command, "command")

        # 保持原有的返回格式兼容性
        if result.success:
            return ResponseBuilder.success(
                command_sent=command,
                method="gateway_unified_send",
                gateway_used=True,
                steps_completed=result.steps_completed
            )
        else:
            return ResponseBuilder.error(
                f"Failed to send command to session {session_name}: {result.error}",
                command=command,
                gateway_error=result.error,
                error_step=result.error_step,
                method="gateway_unified_send"
            )

    @staticmethod
    def send_raw_input(session_name: str, input_text: str) -> Dict[str, Any]:
        """发送原始输入到tmux会话（网关收口版）

        🚨 GATEWAY: 通过统一网关发送原始输入
        使用优化的网关进行原始文本输入，完全避免引号和echo问题

        Args:
            session_name: 会话名称
            input_text: 输入文本（原始内容，无需转义）

        Returns:
            Dict[str, Any]: 执行结果
        """
        # 🎯 通过统一网关发送原始输入
        result = send_to_tmux(session_name, input_text, "text")

        return {
            "success": result.success,
            "session_name": session_name,
            "input_length": len(input_text),
            "method": "gateway_raw_input",
            "error": result.error,
            "steps_completed": result.steps_completed if result.success else []
        }
    
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

        🚨 GATEWAY: 使用统一网关检查可用性

        Returns:
            bool: tmux是否可用
        """
        return get_tmux_gateway().is_tmux_available()

    @staticmethod
    def send_message_to_session(session_name: str, message: str) -> Dict[str, Any]:
        """发送消息到会话（网关收口版）

        🚨 GATEWAY: 通过统一网关发送消息

        Args:
            session_name: 会话名称
            message: 消息内容

        Returns:
            Dict[str, Any]: 发送结果
        """
        result = send_to_tmux(session_name, message, "raw")
        return {
            "success": result.success,
            "session_name": session_name,
            "message_length": len(message),
            "method": "gateway_message_send",
            "error": result.error,
            "steps_completed": result.steps_completed if result.success else []
        }

    @staticmethod
    def broadcast_to_project(project_id: str, message: str) -> Dict[str, Any]:
        """向项目所有会话广播消息（网关收口版）

        🚨 GATEWAY: 通过统一网关进行广播

        Args:
            project_id: 项目ID
            message: 广播消息

        Returns:
            Dict[str, Any]: 广播结果
        """
        # 仍使用高级API，因为需要项目会话发现逻辑
        from .tmux_message_sender import TmuxMessageSender
        return TmuxMessageSender.broadcast_to_project_sessions(project_id, message)

    @staticmethod
    def send_ctrl_key(session_name: str, ctrl_key: str) -> Dict[str, Any]:
        """发送控制键到会话（网关收口版）

        🚨 GATEWAY: 通过统一网关发送控制键

        Args:
            session_name: 会话名称
            ctrl_key: 控制键（如 'C-c', 'C-d'）

        Returns:
            Dict[str, Any]: 发送结果
        """
        result = send_to_tmux(session_name, ctrl_key, "control")
        return {
            "success": result.success,
            "session_name": session_name,
            "ctrl_key": ctrl_key,
            "method": "gateway_control_send",
            "error": result.error,
            "steps_completed": result.steps_completed if result.success else []
        }