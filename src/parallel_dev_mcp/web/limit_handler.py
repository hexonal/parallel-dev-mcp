# -*- coding: utf-8 -*-
"""
Claude 5小时限制检测和定时重试机制

@description 检测Claude 5小时使用限制并自动调度继续命令
"""

import logging
import re
import subprocess
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict
from pydantic import BaseModel, Field

# 配置日志系统
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class LimitDetectionResult(BaseModel):
    """
    限制检测结果数据模型

    用于返回5小时限制检测和处理结果
    """

    limit_detected: bool = Field(False, description="是否检测到5小时限制")
    reset_time: Optional[datetime] = Field(None, description="限制重置时间")
    scheduled: bool = Field(False, description="是否已调度自动继续消息")
    message: str = Field("", description="处理消息")

    class Config:
        """模型配置"""

        # 1. 启用JSON编码器
        # json_encoders deprecated in V2 - datetime fields will use default serialization


class ClaudeLimitHandler:
    """
    Claude 5小时限制处理器

    检测Claude 5小时使用限制并自动调度继续命令
    """

    def __init__(self) -> None:
        """
        初始化限制处理器
        """
        # 1. 初始化正则表达式模式
        self.limit_pattern = re.compile(
            r"5-hour limit reached.*?resets\s+(.+?)(?:\.|$)", re.IGNORECASE | re.DOTALL
        )

        # 2. 初始化时间解析模式
        self.time_patterns = [
            # 12小时制格式：1pm, 12:30am, 9:05PM
            re.compile(r"(\d{1,2})(?::(\d{2}))?(?::(\d{2}))?\s*(am|pm)", re.IGNORECASE),
            # 24小时制格式：13:30, 21:05:30
            re.compile(r"(\d{1,2}):(\d{2})(?::(\d{2}))?"),
        ]

        # 3. 存储调度的定时器
        self._scheduled_timers: Dict[str, threading.Timer] = {}

        # 4. 记录初始化信息
        logger.info("Claude限制处理器初始化完成")

    def capture_pane(self, session_name: str) -> Optional[str]:
        """
        捕获tmux会话面板内容

        Args:
            session_name: tmux会话名称

        Returns:
            Optional[str]: 面板内容文本，失败时返回None
        """
        # 1. 构建tmux命令
        command = ["tmux", "capture-pane", "-p", "-t", session_name]

        try:
            # 2. 执行tmux命令
            result = subprocess.run(
                command, capture_output=True, text=True, timeout=10, check=True
            )

            # 3. 返回捕获的内容
            pane_content = result.stdout.strip()
            logger.debug(f"成功捕获会话 {session_name} 的面板内容")
            return pane_content

        except subprocess.TimeoutExpired:
            # 4. 处理超时异常
            logger.warning(f"捕获会话 {session_name} 面板内容超时")
            return None

        except subprocess.CalledProcessError as e:
            # 5. 处理命令执行错误
            logger.error(f"捕获会话 {session_name} 面板内容失败: {e}")
            return None

        except Exception as e:
            # 6. 处理其他异常
            logger.error(f"捕获面板内容时发生未知错误: {e}")
            return None

    def parse_reset_time(self, pane_text: str) -> Optional[datetime]:
        """
        解析5小时限制重置时间

        Args:
            pane_text: 面板文本内容

        Returns:
            Optional[datetime]: 解析得到的重置时间，失败时返回None
        """
        # 1. 查找限制信息
        match = self.limit_pattern.search(pane_text)
        if not match:
            logger.debug("未找到5小时限制信息")
            return None

        # 2. 提取时间字符串
        time_str = match.group(1).strip()
        logger.info(f"检测到5小时限制，重置时间字符串: {time_str}")

        # 3. 尝试解析时间
        reset_time = self._parse_time_string(time_str)
        if reset_time:
            logger.info(f"成功解析重置时间: {reset_time}")
        else:
            logger.warning(f"无法解析时间字符串: {time_str}")

        # 4. 返回解析结果
        return reset_time

    def _parse_time_string(self, time_str: str) -> Optional[datetime]:
        """
        解析时间字符串为datetime对象

        Args:
            time_str: 时间字符串

        Returns:
            Optional[datetime]: 解析得到的datetime对象
        """
        # 1. 获取当前时间
        now = datetime.now()

        # 2. 尝试12小时制格式
        for pattern in self.time_patterns:
            match = pattern.search(time_str)
            if match:
                return self._create_datetime_from_match(match, now)

        # 3. 解析失败
        return None

    def _create_datetime_from_match(
        self, match: re.Match, base_time: datetime
    ) -> Optional[datetime]:
        """
        从正则匹配结果创建datetime对象

        Args:
            match: 正则表达式匹配结果
            base_time: 基准时间

        Returns:
            Optional[datetime]: 创建的datetime对象
        """
        try:
            # 1. 提取时间组件
            groups = match.groups()
            hour = int(groups[0])
            minute = int(groups[1]) if groups[1] else 0
            second = int(groups[2]) if groups[2] else 0

            # 2. 处理12小时制
            if len(groups) > 3 and groups[3]:
                am_pm = groups[3].lower()
                if am_pm == "pm" and hour != 12:
                    hour += 12
                elif am_pm == "am" and hour == 12:
                    hour = 0

            # 3. 创建目标时间
            target_time = base_time.replace(
                hour=hour, minute=minute, second=second, microsecond=0
            )

            # 4. 如果时间已过，设置为明天
            if target_time <= base_time:
                target_time += timedelta(days=1)

            # 5. 返回结果
            return target_time

        except (ValueError, IndexError) as e:
            # 6. 处理解析错误
            logger.error(f"创建datetime对象失败: {e}")
            return None

    def schedule_continue_message(
        self, session_name: str, reset_time: datetime
    ) -> bool:
        """
        调度自动继续消息

        Args:
            session_name: 目标会话名称
            reset_time: 限制重置时间

        Returns:
            bool: 是否成功调度
        """
        # 1. 计算延时秒数
        now = datetime.now()
        delay_seconds = (reset_time - now).total_seconds()

        # 2. 检查延时有效性
        if delay_seconds <= 0:
            logger.warning(f"重置时间 {reset_time} 已过期，无法调度")
            return False

        # 3. 取消已存在的定时器
        if session_name in self._scheduled_timers:
            self._scheduled_timers[session_name].cancel()
            logger.info(f"取消会话 {session_name} 的已有定时器")

        # 4. 创建新的定时器
        timer = threading.Timer(
            delay_seconds, self._send_continue_message, args=(session_name,)
        )

        # 5. 启动定时器
        timer.start()
        self._scheduled_timers[session_name] = timer

        # 6. 记录调度信息
        logger.info(
            f"成功调度会话 {session_name} 的继续消息，"
            f"将在 {reset_time} 执行（{delay_seconds:.1f}秒后）"
        )

        # 7. 返回成功状态
        return True

    def _send_continue_message(self, session_name: str) -> None:
        """
        发送继续消息到指定会话

        Args:
            session_name: 目标会话名称
        """
        try:
            # 1. 读取继续消息内容
            send_file = Path("examples/hooks/send.txt")
            if not send_file.exists():
                logger.error(f"发送文件不存在: {send_file}")
                return

            # 2. 读取消息内容
            continue_message = send_file.read_text(encoding="utf-8").strip()

            # 3. 发送消息到会话
            command = [
                "tmux",
                "send-keys",
                "-t",
                session_name,
                continue_message,
                "Enter",
            ]

            # 4. 执行发送命令
            subprocess.run(command, check=True, timeout=10)

            # 5. 记录成功信息
            logger.info(f"成功向会话 {session_name} 发送继续消息")

            # 6. 清理定时器记录
            if session_name in self._scheduled_timers:
                del self._scheduled_timers[session_name]

        except Exception as e:
            # 7. 处理发送错误
            logger.error(f"向会话 {session_name} 发送继续消息失败: {e}")

    def check_and_handle_limit(
        self, session_name: str, skip_limit_check: bool = False
    ) -> LimitDetectionResult:
        """
        检查并处理5小时限制

        Args:
            session_name: 会话名称
            skip_limit_check: 是否跳过限制检查（避免递归）

        Returns:
            LimitDetectionResult: 检测和处理结果
        """
        # 1. 检查是否跳过
        if skip_limit_check:
            return LimitDetectionResult(message="跳过限制检查（避免递归）")

        # 2. 捕获面板内容
        pane_content = self.capture_pane(session_name)
        if not pane_content:
            return LimitDetectionResult(message="无法捕获会话面板内容")

        # 3. 解析重置时间
        reset_time = self.parse_reset_time(pane_content)
        if not reset_time:
            return LimitDetectionResult(message="未检测到5小时限制")

        # 4. 调度继续消息
        scheduled = self.schedule_continue_message(session_name, reset_time)

        # 5. 返回结果
        return LimitDetectionResult(
            limit_detected=True,
            reset_time=reset_time,
            scheduled=scheduled,
            message=f"检测到限制，重置时间: {reset_time}, 调度状态: {scheduled}",
        )

    def cancel_scheduled_timer(self, session_name: str) -> bool:
        """
        取消指定会话的调度定时器

        Args:
            session_name: 会话名称

        Returns:
            bool: 是否成功取消
        """
        # 1. 检查定时器存在
        if session_name not in self._scheduled_timers:
            logger.warning(f"会话 {session_name} 没有调度的定时器")
            return False

        # 2. 取消定时器
        timer = self._scheduled_timers[session_name]
        timer.cancel()

        # 3. 清理记录
        del self._scheduled_timers[session_name]

        # 4. 记录取消信息
        logger.info(f"成功取消会话 {session_name} 的调度定时器")

        # 5. 返回成功状态
        return True


def create_default_limit_handler() -> ClaudeLimitHandler:
    """
    创建默认限制处理器实例

    Returns:
        ClaudeLimitHandler: 配置好的限制处理器实例
    """
    # 1. 创建处理器实例
    handler = ClaudeLimitHandler()

    # 2. 记录创建信息
    logger.info("默认Claude限制处理器创建成功")

    # 3. 返回处理器实例
    return handler
