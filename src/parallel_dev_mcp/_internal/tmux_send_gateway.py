"""
Tmux Send Gateway - 统一的tmux发送收口

🚨 CRITICAL: 这是整个项目中唯一允许执行tmux send-keys的文件！
🔐 HIGH COHESION: 所有tmux发送逻辑必须通过此文件统一收口
🎯 SINGLE RESPONSIBILITY: 专门负责tmux消息发送，保证稳定性

设计原则：
1. 唯一发送入口 - 项目中只有这个文件可以调用subprocess执行tmux send-keys
2. 高内聚低耦合 - 所有发送变体都在此文件内统一管理
3. 错误处理集中 - 统一的异常处理和日志记录
4. 接口标准化 - 提供标准化的发送接口给其他模块
"""

import subprocess
import logging
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class SendMode(Enum):
    """发送模式枚举"""
    RAW = "raw"              # 原始内容直接发送
    COMMAND = "command"      # 命令输入发送
    TEXT = "text"           # 文本输入发送
    CONTROL = "control"     # 控制键发送


@dataclass
class SendResult:
    """发送结果数据类"""
    success: bool
    session_name: str
    content: str
    mode: SendMode
    steps_completed: List[str]
    error: Optional[str] = None
    error_step: Optional[str] = None
    return_code_1: Optional[int] = None
    return_code_2: Optional[int] = None


class TmuxSendGateway:
    """
    Tmux发送网关 - 项目唯一的tmux send-keys执行点

    🚨 WARNING: 其他任何文件都不应该直接调用tmux send-keys！
    """

    # 类级别的全局配置
    _instance = None
    _debug_mode = False
    _dry_run = False

    def __new__(cls):
        """单例模式确保全局唯一性"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def enable_debug(cls, enabled: bool = True):
        """启用调试模式"""
        cls._debug_mode = enabled
        if enabled:
            logger.setLevel(logging.DEBUG)

    @classmethod
    def enable_dry_run(cls, enabled: bool = True):
        """启用干跑模式（不实际执行，仅记录）"""
        cls._dry_run = enabled

    def __init__(self):
        """初始化网关"""
        if not hasattr(self, '_initialized'):
            self._initialized = True
            logger.info("🔐 TmuxSendGateway initialized - 统一发送收口已启动")

    def send(self, session_name: str, content: str, mode: SendMode = SendMode.RAW) -> SendResult:
        """
        统一发送入口 - 所有tmux发送的唯一通道

        Args:
            session_name: 目标会话名称
            content: 要发送的内容
            mode: 发送模式

        Returns:
            SendResult: 标准化的发送结果
        """
        if self._debug_mode:
            logger.debug(f"🎯 Gateway Send: {session_name} | {mode.value} | {content[:50]}...")

        # 统一的前置检查
        if not self._validate_session(session_name):
            return SendResult(
                success=False,
                session_name=session_name,
                content=content,
                mode=mode,
                steps_completed=[],
                error=f"Session does not exist: {session_name}",
                error_step="session_validation"
            )

        # 根据模式分发到具体发送方法
        if mode == SendMode.RAW:
            return self._send_raw_content(session_name, content)
        elif mode == SendMode.COMMAND:
            return self._send_command_input(session_name, content)
        elif mode == SendMode.TEXT:
            return self._send_text_input(session_name, content)
        elif mode == SendMode.CONTROL:
            return self._send_control_key(session_name, content)
        else:
            return SendResult(
                success=False,
                session_name=session_name,
                content=content,
                mode=mode,
                steps_completed=[],
                error=f"Unknown send mode: {mode}",
                error_step="mode_validation"
            )

    def send_raw(self, session_name: str, content: str) -> SendResult:
        """发送原始内容（无引号、分步）"""
        return self.send(session_name, content, SendMode.RAW)

    def send_command(self, session_name: str, command: str) -> SendResult:
        """发送命令输入"""
        return self.send(session_name, command, SendMode.COMMAND)

    def send_text(self, session_name: str, text: str) -> SendResult:
        """发送文本输入"""
        return self.send(session_name, text, SendMode.TEXT)

    def send_control_key(self, session_name: str, key: str) -> SendResult:
        """发送控制键"""
        return self.send(session_name, key, SendMode.CONTROL)

    def broadcast_to_sessions(self, session_names: List[str], content: str,
                             mode: SendMode = SendMode.RAW) -> Dict[str, Any]:
        """
        向多个会话广播内容

        Args:
            session_names: 目标会话名称列表
            content: 广播内容
            mode: 发送模式

        Returns:
            Dict[str, Any]: 广播结果统计
        """
        results = []
        success_count = 0
        failed_sessions = []

        for session_name in session_names:
            result = self.send(session_name, content, mode)
            results.append({
                "session": session_name,
                "success": result.success,
                "error": result.error
            })

            if result.success:
                success_count += 1
            else:
                failed_sessions.append(session_name)

        return {
            "success": success_count > 0,
            "total_sessions": len(session_names),
            "success_count": success_count,
            "failed_count": len(failed_sessions),
            "success_rate": f"{(success_count/len(session_names)*100):.1f}%",
            "failed_sessions": failed_sessions,
            "broadcast_results": results,
            "content_length": len(content),
            "mode": mode.value
        }

    # === 核心发送实现方法（私有） ===

    def _send_raw_content(self, session_name: str, content: str) -> SendResult:
        """发送原始内容的核心实现"""
        return self._execute_two_step_send(session_name, content, SendMode.RAW)

    def _send_command_input(self, session_name: str, command: str) -> SendResult:
        """发送命令输入的核心实现"""
        return self._execute_two_step_send(session_name, command, SendMode.COMMAND)

    def _send_text_input(self, session_name: str, text: str) -> SendResult:
        """发送文本输入的核心实现"""
        return self._execute_two_step_send(session_name, text, SendMode.TEXT)

    def _send_control_key(self, session_name: str, key: str) -> SendResult:
        """发送控制键的核心实现"""
        if self._dry_run:
            logger.info(f"🔄 DRY RUN - Control Key: {session_name} <- {key}")
            return SendResult(
                success=True,
                session_name=session_name,
                content=key,
                mode=SendMode.CONTROL,
                steps_completed=["dry_run_control"]
            )

        try:
            result = subprocess.run([
                'tmux', 'send-keys', '-t', session_name, key
            ], capture_output=True, text=True)

            if result.returncode == 0:
                return SendResult(
                    success=True,
                    session_name=session_name,
                    content=key,
                    mode=SendMode.CONTROL,
                    steps_completed=["control_key"],
                    return_code_1=result.returncode
                )
            else:
                return SendResult(
                    success=False,
                    session_name=session_name,
                    content=key,
                    mode=SendMode.CONTROL,
                    steps_completed=[],
                    error=f"Control key send failed: {result.stderr}",
                    error_step="control_execution",
                    return_code_1=result.returncode
                )

        except Exception as e:
            return SendResult(
                success=False,
                session_name=session_name,
                content=key,
                mode=SendMode.CONTROL,
                steps_completed=[],
                error=f"Control key exception: {str(e)}",
                error_step="control_exception"
            )

    def _execute_two_step_send(self, session_name: str, content: str, mode: SendMode) -> SendResult:
        """
        执行两步发送的核心方法 - 项目中唯一的tmux send-keys执行点

        🚨 这里是整个项目唯一允许调用subprocess执行tmux send-keys的地方！
        """
        if self._dry_run:
            logger.info(f"🔄 DRY RUN - Two Step Send: {session_name} <- {content[:50]}...")
            return SendResult(
                success=True,
                session_name=session_name,
                content=content,
                mode=mode,
                steps_completed=["dry_run_content", "dry_run_enter"]
            )

        steps_completed = []

        try:
            # 🎯 第一步：发送内容（无引号包装）
            step1_result = subprocess.run([
                'tmux', 'send-keys', '-t', session_name, content
            ], capture_output=True, text=True)

            if step1_result.returncode != 0:
                return SendResult(
                    success=False,
                    session_name=session_name,
                    content=content,
                    mode=mode,
                    steps_completed=steps_completed,
                    error=f"Step 1 failed: {step1_result.stderr}",
                    error_step="content_send",
                    return_code_1=step1_result.returncode
                )

            steps_completed.append("content")

            # 🎯 第二步：发送回车键（分离操作）
            step2_result = subprocess.run([
                'tmux', 'send-keys', '-t', session_name, 'C-m'
            ], capture_output=True, text=True)

            if step2_result.returncode != 0:
                return SendResult(
                    success=False,
                    session_name=session_name,
                    content=content,
                    mode=mode,
                    steps_completed=steps_completed,
                    error=f"Step 2 failed: {step2_result.stderr}",
                    error_step="enter_send",
                    return_code_1=step1_result.returncode,
                    return_code_2=step2_result.returncode
                )

            steps_completed.append("enter")

            # 成功完成两步发送
            if self._debug_mode:
                logger.debug(f"✅ Two-step send completed: {session_name}")

            return SendResult(
                success=True,
                session_name=session_name,
                content=content,
                mode=mode,
                steps_completed=steps_completed,
                return_code_1=step1_result.returncode,
                return_code_2=step2_result.returncode
            )

        except Exception as e:
            return SendResult(
                success=False,
                session_name=session_name,
                content=content,
                mode=mode,
                steps_completed=steps_completed,
                error=f"Two-step send exception: {str(e)}",
                error_step="execution_exception"
            )

    def _validate_session(self, session_name: str) -> bool:
        """验证会话是否存在"""
        try:
            result = subprocess.run([
                'tmux', 'has-session', '-t', session_name
            ], capture_output=True, text=True)
            return result.returncode == 0
        except Exception:
            return False

    # === 系统级别方法 ===

    @staticmethod
    def is_tmux_available() -> bool:
        """检查tmux是否可用"""
        try:
            result = subprocess.run(['tmux', '-V'], capture_output=True, text=True)
            return result.returncode == 0
        except Exception:
            return False

    def get_available_sessions(self) -> List[str]:
        """获取所有可用会话列表"""
        try:
            result = subprocess.run([
                'tmux', 'list-sessions', '-F', '#{session_name}'
            ], capture_output=True, text=True)

            if result.returncode == 0:
                return [s.strip() for s in result.stdout.strip().split('\n') if s.strip()]
            else:
                return []
        except Exception:
            return []

    def get_gateway_stats(self) -> Dict[str, Any]:
        """获取网关运行统计"""
        return {
            "gateway_initialized": hasattr(self, '_initialized'),
            "debug_mode": self._debug_mode,
            "dry_run_mode": self._dry_run,
            "tmux_available": self.is_tmux_available(),
            "available_sessions": self.get_available_sessions(),
            "supported_modes": [mode.value for mode in SendMode]
        }


# === 全局网关实例和便捷函数 ===

# 创建全局唯一的网关实例
_gateway = TmuxSendGateway()

def send_to_tmux(session_name: str, content: str, mode: str = "raw") -> SendResult:
    """
    全局便捷发送函数 - 推荐的外部调用接口

    Args:
        session_name: 目标会话名称
        content: 发送内容
        mode: 发送模式 ("raw", "command", "text", "control")

    Returns:
        SendResult: 发送结果
    """
    try:
        send_mode = SendMode(mode)
    except ValueError:
        return SendResult(
            success=False,
            session_name=session_name,
            content=content,
            mode=SendMode.RAW,
            steps_completed=[],
            error=f"Invalid send mode: {mode}",
            error_step="mode_validation"
        )

    return _gateway.send(session_name, content, send_mode)

def broadcast_to_tmux(session_names: List[str], content: str, mode: str = "raw") -> Dict[str, Any]:
    """
    全局便捷广播函数

    Args:
        session_names: 目标会话名称列表
        content: 广播内容
        mode: 发送模式

    Returns:
        Dict[str, Any]: 广播结果
    """
    try:
        send_mode = SendMode(mode)
    except ValueError:
        send_mode = SendMode.RAW

    return _gateway.broadcast_to_sessions(session_names, content, send_mode)

def get_tmux_gateway() -> TmuxSendGateway:
    """获取全局网关实例"""
    return _gateway

# === 便捷类型检查函数 ===

def enable_debug_mode(enabled: bool = True):
    """启用全局调试模式"""
    TmuxSendGateway.enable_debug(enabled)

def enable_dry_run_mode(enabled: bool = True):
    """启用全局干跑模式"""
    TmuxSendGateway.enable_dry_run(enabled)