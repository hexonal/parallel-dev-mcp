# -*- coding: utf-8 -*-
"""
消息发送统一工具

@description 提供符合CLAUDE.md规范的消息发送MCP工具，遵循YAGNI原则
"""

import time
import logging
import subprocess
import threading
from typing import Optional

from ..mcp_instance import mcp
from .models import MessageResult

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def _send_to_tmux(session_name: str, content: str) -> tuple[bool, str]:
    """
    发送消息到tmux会话

    Args:
        session_name: 会话名称
        content: 消息内容

    Returns:
        tuple[bool, str]: (成功标志, 错误信息)
    """
    try:
        # 1. 检查会话是否存在
        result = subprocess.run(
            ['tmux', 'has-session', '-t', session_name],
            capture_output=True,
            timeout=5
        )

        if result.returncode != 0:
            return (False, f"会话不存在: {session_name}")

        # 2. 发送消息内容（不自动回车）
        result = subprocess.run(
            ['tmux', 'send-keys', '-t', session_name, '-l', content],
            capture_output=True,
            timeout=5
        )

        if result.returncode != 0:
            return (False, f"发送失败: {result.stderr.decode()}")

        # 3. 返回成功
        return (True, "")

    except subprocess.TimeoutExpired:
        # 4. 超时处理
        return (False, "命令执行超时")

    except Exception as e:
        # 5. 异常处理
        return (False, str(e))


def _delayed_send(
    session_name: str,
    content: str,
    delay_seconds: int
) -> None:
    """
    延时发送消息（在后台线程中执行）

    Args:
        session_name: 会话名称
        content: 消息内容
        delay_seconds: 延时秒数
    """
    # 1. 等待延时
    time.sleep(delay_seconds)

    # 2. 发送消息
    success, error = _send_to_tmux(session_name, content)

    # 3. 记录结果
    if success:
        logger.info(f"延时消息发送成功: {session_name} <- {content}")
    else:
        logger.error(f"延时消息发送失败: {session_name}, 错误: {error}")


@mcp.tool
def message(
    session_name: str,
    content: str,
    delay_seconds: int = 0
) -> MessageResult:
    """
    消息发送工具

    向指定会话发送消息，支持立即发送和延时发送。
    符合CLAUDE.md规范和YAGNI原则，返回类型安全的Pydantic Model。

    Args:
        session_name: 目标会话名称
        content: 消息内容
        delay_seconds: 延时秒数，0表示立即发送，最大300秒

    Returns:
        MessageResult: 类型安全的发送结果

    Examples:
        - 立即发送: message(session_name='PARALLEL_child_auth_101', content='测试完成')
        - 延时发送: message(session_name='PARALLEL_child_auth_101', content='继续执行', delay_seconds=10)
    """
    try:
        # 1. 参数验证
        if not session_name or not session_name.strip():
            return MessageResult(
                success=False,
                message="会话名称不能为空",
                session_name="",
                content=content,
                delivered=False,
                error="参数验证失败"
            )

        if not content or not content.strip():
            return MessageResult(
                success=False,
                message="消息内容不能为空",
                session_name=session_name,
                content="",
                delivered=False,
                error="参数验证失败"
            )

        # 2. 清理参数
        session_name = session_name.strip()
        content = content.strip()

        # 3. 限制延时范围
        delay_seconds = max(0, min(delay_seconds, 300))

        # 4. 立即发送
        if delay_seconds == 0:
            success, error = _send_to_tmux(session_name, content)

            if success:
                logger.info(f"消息发送成功: {session_name} <- {content}")
                return MessageResult(
                    success=True,
                    message=f"消息发送成功: {session_name}",
                    session_name=session_name,
                    content=content,
                    delivered=True,
                    delay_seconds=0
                )
            else:
                logger.error(f"消息发送失败: {session_name}, 错误: {error}")
                return MessageResult(
                    success=False,
                    message=f"消息发送失败: {error}",
                    session_name=session_name,
                    content=content,
                    delivered=False,
                    delay_seconds=0,
                    error=error
                )

        # 5. 延时发送（后台线程）
        else:
            thread = threading.Thread(
                target=_delayed_send,
                args=(session_name, content, delay_seconds),
                daemon=True
            )
            thread.start()

            logger.info(f"延时消息已安排: {session_name}, 延时{delay_seconds}秒")
            return MessageResult(
                success=True,
                message=f"延时消息已安排，将在{delay_seconds}秒后发送",
                session_name=session_name,
                content=content,
                delivered=False,
                delay_seconds=delay_seconds
            )

    except Exception as e:
        # 6. 异常处理
        logger.error(f"消息发送异常: {e}")
        return MessageResult(
            success=False,
            message=f"消息发送异常: {str(e)}",
            session_name=session_name if 'session_name' in locals() else "",
            content=content if 'content' in locals() else "",
            delivered=False,
            error=str(e)
        )
