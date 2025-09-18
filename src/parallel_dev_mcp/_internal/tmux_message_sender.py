"""
Tmux Message Sender - 高级tmux消息发送抽象层

🚨 NOTICE: 此模块已重构为使用统一的TmuxSendGateway收口
🔐 NO DIRECT SEND-KEYS: 本文件不再直接执行tmux send-keys
🎯 HIGH-LEVEL API: 提供高级的消息发送业务接口

专门解决你提出的tmux发送问题：
1. 不使用引号包装消息内容
2. 不使用echo命令显示
3. 分两次send-keys操作：消息内容 + 回车
4. 通过统一网关保证高内聚
"""

import os
import logging
import uuid
import time
from collections import deque
from datetime import datetime
from typing import Dict, Any, List, Optional
from .response_builder import ResponseBuilder
from .tmux_send_gateway import send_to_tmux, broadcast_to_tmux, get_tmux_gateway

logger = logging.getLogger(__name__)


class TmuxMessageSender:
    """统一的tmux消息发送器 - 解决引号、echo和回车分离问题，支持会话绑定"""

    # 类变量用于管理全局状态
    _current_session_id = None
    _session_binding_active = False
    _binding_file = None
    # 事件频率跟踪（参考 examples/hooks/tmux_web_service.py 的 hi 发送逻辑）
    _freq_window_seconds = 30
    _freq_threshold = 1
    _session_end_calls = deque()

    @classmethod
    def _get_binding_file_path(cls) -> str:
        """获取 session 绑定文件路径（≤50行）

        存放在项目根目录下的隐藏状态目录：`.state/session_binding.txt`
        """
        if cls._binding_file is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
            cls._binding_file = os.path.join(project_root, '.state', 'session_binding.txt')
        return cls._binding_file

    @classmethod
    def _load_session_binding(cls) -> None:
        """从文件加载会话绑定状态"""
        try:
            binding_file = cls._get_binding_file_path()
            if os.path.exists(binding_file) and os.path.getsize(binding_file) > 0:
                with open(binding_file, 'r') as f:
                    content = f.read().strip()
                    if content:
                        cls._current_session_id = content
                        cls._session_binding_active = True
                        logger.info(f"加载会话绑定: {cls._current_session_id[:8]}...")
                    else:
                        cls._current_session_id = None
                        cls._session_binding_active = False
            else:
                cls._current_session_id = None
                cls._session_binding_active = False
        except Exception as e:
            logger.error(f"加载会话绑定失败: {e}")
            cls._current_session_id = None
            cls._session_binding_active = False

    @classmethod
    def _save_session_binding(cls, session_id: str) -> bool:
        """保存会话绑定到文件"""
        try:
            binding_file = cls._get_binding_file_path()
            os.makedirs(os.path.dirname(binding_file), exist_ok=True)
            with open(binding_file, 'w') as f:
                f.write(f"{session_id}\n")
            cls._current_session_id = session_id
            cls._session_binding_active = True
            logger.info(f"保存会话绑定: {session_id[:8]}...")
            return True
        except Exception as e:
            logger.error(f"保存会话绑定失败: {e}")
            return False

    @classmethod
    def _clear_session_binding(cls) -> bool:
        """清除会话绑定"""
        try:
            binding_file = cls._get_binding_file_path()
            if os.path.exists(binding_file):
                with open(binding_file, 'w') as f:
                    f.write("")
            cls._current_session_id = None
            cls._session_binding_active = False
            logger.info("清除会话绑定")
            return True
        except Exception as e:
            logger.error(f"清除会话绑定失败: {e}")
            return False

    @classmethod
    def bind_session(cls, session_id: str = None, target_session: str = None) -> Dict[str, Any]:
        """绑定会话ID到目标tmux会话"""
        if not session_id:
            session_id = str(uuid.uuid4())

        # 保存绑定状态
        if cls._save_session_binding(session_id):
            return ResponseBuilder.success(
                operation="bind_session",
                session_id=session_id,
                target_session=target_session or "default",
                binding_file=cls._get_binding_file_path(),
                method="tmux_session_binding"
            )
        else:
            return ResponseBuilder.error(
                "会话绑定失败",
                session_id=session_id,
                target_session=target_session
            )

    @classmethod
    def unbind_session(cls, session_id: str = None) -> Dict[str, Any]:
        """解绑会话ID"""
        # 先加载当前状态
        cls._load_session_binding()
        current_session = cls._current_session_id

        if not session_id:
            session_id = current_session

        if not session_id:
            return ResponseBuilder.error(
                "没有可解绑的会话ID",
                operation="unbind_session"
            )

        # 清除绑定状态
        if cls._clear_session_binding():
            return ResponseBuilder.success(
                operation="unbind_session",
                session_id=session_id,
                previous_session=current_session,
                method="tmux_session_unbinding"
            )
        else:
            return ResponseBuilder.error(
                "会话解绑失败",
                session_id=session_id
            )

    @classmethod
    def get_current_session_binding(cls) -> str:
        """获取当前绑定的会话名称（返回字符串，用于web服务）"""
        cls._load_session_binding()  # 重新加载状态
        return cls._current_session_id

    @classmethod
    def get_current_session_binding_info(cls) -> Dict[str, Any]:
        """获取当前会话绑定详细状态（返回完整信息）"""
        cls._load_session_binding()  # 重新加载状态

        return ResponseBuilder.success(
            operation="get_session_binding",
            current_session_id=cls._current_session_id,
            session_binding_active=cls._session_binding_active,
            binding_file=cls._get_binding_file_path(),
            method="tmux_session_status"
        )

    # === 频率跟踪与自动 hi 逻辑 ===
    @classmethod
    def _record_session_end_call(cls) -> int:
        """记录一次 SessionEnd 调用，并裁剪时间窗口内的记录，返回窗口内次数"""
        now = time.time()
        cls._session_end_calls.append(now)
        cutoff = now - cls._freq_window_seconds
        while cls._session_end_calls and cls._session_end_calls[0] < cutoff:
            cls._session_end_calls.popleft()
        return len(cls._session_end_calls)

    @classmethod
    def _should_trigger_auto_hi(cls) -> bool:
        return len(cls._session_end_calls) > cls._freq_threshold

    @classmethod
    def _reset_frequency_tracker(cls) -> None:
        cls._session_end_calls.clear()

    @classmethod
    def send_auto_hi(cls, session_name: str) -> Dict[str, Any]:
        """发送自动 hi（不计入频率统计）"""
        return cls.send_message_raw(session_name, "hi")

    @classmethod
    def send_message_raw(cls, session_name: str, message: str, session_id: str = None) -> Dict[str, Any]:
        """
        原始消息发送 - 无引号，无echo，双步骤发送，支持会话绑定验证

        🔐 GATEWAY: 通过统一网关发送，保证高内聚
        🔗 BINDING: 支持session_id绑定验证

        Args:
            session_name: 目标会话名称
            message: 消息内容（原始文本，无需转义）
            session_id: 可选的会话ID，用于绑定验证

        Returns:
            Dict[str, Any]: 发送结果
        """
        try:
            # 加载当前绑定状态
            cls._load_session_binding()

            # Session ID 验证逻辑
            effective_session_id = session_id or cls._current_session_id

            # 如果有绑定的session但session_id不匹配，跳过发送
            if cls._session_binding_active and cls._current_session_id:
                if session_id and session_id != cls._current_session_id:
                    return ResponseBuilder.error(
                        f"Session ID 不匹配，跳过发送",
                        session=session_name,
                        bound_session_id=cls._current_session_id,
                        received_session_id=session_id,
                        action="skipped",
                        method="session_binding_validation"
                    )

            # 🎯 通过统一网关发送（唯一的send-keys执行点）
            result = send_to_tmux(session_name, message, "raw")

            if result.success:
                return ResponseBuilder.success(
                    operation="send_message_raw",
                    session_name=session_name,
                    message_length=len(message),
                    message_preview=message[:100] + "..." if len(message) > 100 else message,
                    method="gateway_two_step_send",
                    steps_completed=result.steps_completed,
                    gateway_mode=result.mode.value,
                    session_id=effective_session_id,
                    session_binding_active=cls._session_binding_active
                )
            else:
                # 命中限流：直接返回可机读的限流信息
                if getattr(result, "limit_triggered", None):
                    return ResponseBuilder.error(
                        "tmux rate limit active; message skipped",
                        session=session_name,
                        message_preview=message[:50],
                        action="skipped_due_to_limit",
                        limit_triggered=True,
                        limit_reset_time=getattr(result, "limit_reset_time", None),
                        error_step=result.error_step,
                    )
                return ResponseBuilder.error(
                    f"网关发送失败: {result.error}",
                    session=session_name,
                    message_preview=message[:50],
                    error_step=result.error_step,
                    gateway_error=result.error,
                    session_id=effective_session_id
                )

        except Exception as e:
            return ResponseBuilder.error(
                f"发送消息异常: {str(e)}",
                session=session_name,
                exception_type=type(e).__name__,
                session_id=effective_session_id
            )

    @classmethod
    def send_message_with_newline(cls, session_name: str, message: str, session_id: str = None) -> Dict[str, Any]:
        """
        发送消息并自动换行 - send_message_raw的别名方法

        Args:
            session_name: 目标会话名称
            message: 消息内容
            session_id: 可选的会话ID

        Returns:
            Dict[str, Any]: 发送结果
        """
        return cls.send_message_raw(session_name, message, session_id)

    @classmethod
    def send_command_input(cls, session_name: str, command: str, session_id: str = None) -> Dict[str, Any]:
        """
        发送命令输入（类似用户键盘输入）

        🔐 GATEWAY: 通过统一网关发送命令
        与send_message_raw功能相同，但语义上更明确表示这是命令输入

        Args:
            session_name: 目标会话名称
            command: 命令内容

        Returns:
            Dict[str, Any]: 发送结果
        """
        try:
            # 加载当前绑定状态
            cls._load_session_binding()

            # Session ID 验证逻辑
            effective_session_id = session_id or cls._current_session_id

            # 如果有绑定的session但session_id不匹配，跳过发送
            if cls._session_binding_active and cls._current_session_id:
                if session_id and session_id != cls._current_session_id:
                    return ResponseBuilder.error(
                        f"Session ID 不匹配，跳过命令发送",
                        session=session_name,
                        bound_session_id=cls._current_session_id,
                        received_session_id=session_id,
                        action="skipped",
                        method="session_binding_validation"
                    )

            # 🎯 通过统一网关发送命令
            result = send_to_tmux(session_name, command, "command")

            if result.success:
                return ResponseBuilder.success(
                    operation="send_command_input",
                    session_name=session_name,
                    input_type="command",
                    command_length=len(command),
                    method="gateway_command_send",
                    steps_completed=result.steps_completed,
                    gateway_mode=result.mode.value,
                    session_id=effective_session_id,
                    session_binding_active=cls._session_binding_active
                )
            else:
                if getattr(result, "limit_triggered", None):
                    return ResponseBuilder.error(
                        "tmux rate limit active; command skipped",
                        session=session_name,
                        command_preview=command[:50],
                        action="skipped_due_to_limit",
                        limit_triggered=True,
                        limit_reset_time=getattr(result, "limit_reset_time", None),
                        error_step=result.error_step,
                    )
                return ResponseBuilder.error(
                    f"网关命令发送失败: {result.error}",
                    session=session_name,
                    command_preview=command[:50],
                    error_step=result.error_step,
                    session_id=effective_session_id
                )

        except Exception as e:
            return ResponseBuilder.error(
                f"命令发送异常: {str(e)}",
                session=session_name,
                exception_type=type(e).__name__,
                session_id=effective_session_id
            )

    @classmethod
    def send_text_input(cls, session_name: str, text: str, session_id: str = None) -> Dict[str, Any]:
        """
        发送文本输入（纯文本，无命令语义）

        🔐 GATEWAY: 通过统一网关发送文本

        Args:
            session_name: 目标会话名称
            text: 文本内容

        Returns:
            Dict[str, Any]: 发送结果
        """
        try:
            # 加载当前绑定状态
            cls._load_session_binding()

            # Session ID 验证逻辑
            effective_session_id = session_id or cls._current_session_id

            # 如果有绑定的session但session_id不匹配，跳过发送
            if cls._session_binding_active and cls._current_session_id:
                if session_id and session_id != cls._current_session_id:
                    return ResponseBuilder.error(
                        f"Session ID 不匹配，跳过文本发送",
                        session=session_name,
                        bound_session_id=cls._current_session_id,
                        received_session_id=session_id,
                        action="skipped",
                        method="session_binding_validation"
                    )

            # 🎯 通过统一网关发送文本
            result = send_to_tmux(session_name, text, "text")

            if result.success:
                return ResponseBuilder.success(
                    operation="send_text_input",
                    session_name=session_name,
                    input_type="text",
                    text_length=len(text),
                    method="gateway_text_send",
                    steps_completed=result.steps_completed,
                    gateway_mode=result.mode.value,
                    session_id=effective_session_id,
                    session_binding_active=cls._session_binding_active
                )
            else:
                if getattr(result, "limit_triggered", None):
                    return ResponseBuilder.error(
                        "tmux rate limit active; text skipped",
                        session=session_name,
                        text_preview=text[:50],
                        action="skipped_due_to_limit",
                        limit_triggered=True,
                        limit_reset_time=getattr(result, "limit_reset_time", None),
                        error_step=result.error_step,
                    )
                return ResponseBuilder.error(
                    f"网关文本发送失败: {result.error}",
                    session=session_name,
                    text_preview=text[:50],
                    error_step=result.error_step,
                    session_id=effective_session_id
                )

        except Exception as e:
            return ResponseBuilder.error(
                f"文本发送异常: {str(e)}",
                session=session_name,
                exception_type=type(e).__name__,
                session_id=effective_session_id
            )

    @classmethod
    def broadcast_to_project_sessions(cls, project_id: str, message: str,
                                    include_master: bool = True,
                                    include_children: bool = True,
                                    session_id: str = None) -> Dict[str, Any]:
        """
        向项目所有相关会话广播消息

        🔐 GATEWAY: 通过统一网关进行广播，保证高内聚

        Args:
            project_id: 项目ID
            message: 广播消息内容
            include_master: 是否包含主会话
            include_children: 是否包含子会话

        Returns:
            Dict[str, Any]: 广播结果统计
        """
        try:
            # 加载当前绑定状态
            cls._load_session_binding()

            # Session ID 验证逻辑
            effective_session_id = session_id or cls._current_session_id

            target_sessions = cls._find_project_sessions(
                project_id, include_master, include_children
            )

            if not target_sessions:
                return ResponseBuilder.error(
                    f"未找到项目 {project_id} 的任何会话",
                    project_id=project_id,
                    include_master=include_master,
                    include_children=include_children
                )

            # 🎯 通过统一网关进行广播
            gateway_result = broadcast_to_tmux(target_sessions, message, "raw")

            return ResponseBuilder.success(
                operation="broadcast_to_project",
                project_id=project_id,
                total_sessions=gateway_result["total_sessions"],
                success_count=gateway_result["success_count"],
                failed_count=gateway_result["failed_count"],
                success_rate=gateway_result["success_rate"],
                target_sessions=target_sessions,
                failed_sessions=gateway_result["failed_sessions"],
                broadcast_results=gateway_result["broadcast_results"],
                message_length=len(message),
                method="gateway_broadcast",
                gateway_mode=gateway_result["mode"],
                session_id=effective_session_id,
                session_binding_active=cls._session_binding_active
            )

        except Exception as e:
            return ResponseBuilder.error(
                f"广播消息异常: {str(e)}",
                project_id=project_id,
                exception_type=type(e).__name__
            )

    @classmethod
    def send_ctrl_key(cls, session_name: str, ctrl_key: str, session_id: str = None) -> Dict[str, Any]:
        """
        发送控制键（如Ctrl-C, Ctrl-D等）

        🔐 GATEWAY: 通过统一网关发送控制键

        Args:
            session_name: 目标会话名称
            ctrl_key: 控制键（如 'C-c', 'C-d', 'C-l'）

        Returns:
            Dict[str, Any]: 发送结果
        """
        try:
            # 🎯 通过统一网关发送控制键
            result = send_to_tmux(session_name, ctrl_key, "control")

            if result.success:
                return ResponseBuilder.success(
                    operation="send_ctrl_key",
                    session_name=session_name,
                    ctrl_key=ctrl_key,
                    method="gateway_control_send",
                    steps_completed=result.steps_completed,
                    gateway_mode=result.mode.value
                )
            else:
                return ResponseBuilder.error(
                    f"网关控制键发送失败: {result.error}",
                    session=session_name,
                    ctrl_key=ctrl_key,
                    error_step=result.error_step
                )

        except Exception as e:
            return ResponseBuilder.error(
                f"控制键发送异常: {str(e)}",
                session=session_name,
                ctrl_key=ctrl_key,
                exception_type=type(e).__name__
            )

    # === 内部辅助方法 ===

    @classmethod
    def _session_exists(cls, session_name: str) -> bool:
        """检查tmux会话是否存在

        🔐 GATEWAY: 使用网关的会话检查功能
        """
        gateway = get_tmux_gateway()
        available_sessions = gateway.get_available_sessions()
        return session_name in available_sessions

    @classmethod
    def _find_project_sessions(cls, project_id: str, include_master: bool = True,
                              include_children: bool = True) -> List[str]:
        """查找项目相关的所有会话

        🔐 GATEWAY: 使用网关获取会话列表
        """
        try:
            gateway = get_tmux_gateway()
            all_sessions = gateway.get_available_sessions()

            sessions = []
            expected_master = f"parallel_{project_id}_task_master"
            expected_child_prefix = f"parallel_{project_id}_task_child_"

            for session in all_sessions:
                # 检查主会话
                if include_master and session == expected_master:
                    sessions.append(session)

                # 检查子会话
                if include_children and session.startswith(expected_child_prefix):
                    sessions.append(session)

            return sessions

        except Exception as e:
            logger.error(f"查找项目会话时出错: {e}")
            return []

    @classmethod
    def get_available_sessions(cls) -> Dict[str, Any]:
        """获取所有可用的tmux会话列表

        🔐 GATEWAY: 使用网关获取会话列表
        """
        try:
            gateway = get_tmux_gateway()
            sessions = gateway.get_available_sessions()

            return ResponseBuilder.list_result(
                sessions,
                total_count=len(sessions),
                operation="list_available_sessions",
                method="gateway_session_list"
            )

        except Exception as e:
            return ResponseBuilder.error(
                f"获取会话列表异常: {str(e)}",
                exception_type=type(e).__name__
            )

    @classmethod
    def is_tmux_available(cls) -> bool:
        """检查tmux是否可用

        🔐 GATEWAY: 使用网关的tmux可用性检查
        """
        return get_tmux_gateway().is_tmux_available()

    # ===== 实例方法（用于web服务兼容性）=====

    def __init__(self):
        """初始化实例"""
        pass

    def send_message(self, session_name: str, message: str) -> bool:
        """发送消息到指定会话（简化版本，返回bool）"""
        result = self.__class__.send_message_raw(session_name, message)
        return result.get('success', False)

    def list_sessions(self) -> List[str]:
        """获取所有tmux会话列表（简化版本，返回字符串列表）"""
        result = self.__class__.get_available_sessions()
        if result.get('success', False):
            return result.get('items', [])
        return []


# 为了方便使用，提供一些便捷函数
# 🔐 GATEWAY: 所有便捷函数都通过统一网关或高级API

def send_to_session(session_name: str, message: str) -> Dict[str, Any]:
    """便捷函数：发送消息到会话

    🔐 GATEWAY: 直接使用网关发送
    """
    result = send_to_tmux(session_name, message, "raw")
    return {
        "success": result.success,
        "session_name": session_name,
        "message_length": len(message),
        "error": result.error,
        "method": "gateway_convenience"
    }

def send_command_to_session(session_name: str, command: str) -> Dict[str, Any]:
    """便捷函数：发送命令到会话

    🔐 GATEWAY: 直接使用网关发送命令
    """
    result = send_to_tmux(session_name, command, "command")
    return {
        "success": result.success,
        "session_name": session_name,
        "command_length": len(command),
        "error": result.error,
        "method": "gateway_convenience"
    }

def broadcast_to_project(project_id: str, message: str) -> Dict[str, Any]:
    """便捷函数：向项目广播消息

    🔐 GATEWAY: 通过高级API进行广播
    """
    return TmuxMessageSender.broadcast_to_project_sessions(project_id, message)
