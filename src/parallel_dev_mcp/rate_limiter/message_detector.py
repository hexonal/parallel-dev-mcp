# -*- coding: utf-8 -*-
"""
5小时限制检测器

@description 检测tmux输出中的'5-hour limit reached ∙ resets <time>'模式并解析重置时间
"""

import re
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Pattern
from pydantic import BaseModel, Field
from enum import Enum, unique

# 配置日志系统
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@unique
class LimitType(Enum):
    """限制类型枚举"""
    FIVE_HOUR = "5-hour"
    DAILY = "daily"
    RATE_LIMIT = "rate-limit"
    UNKNOWN = "unknown"


class LimitDetectionResult(BaseModel):
    """限制检测结果数据模型"""

    detected: bool = Field(False, description="是否检测到限制")
    limit_type: LimitType = Field(LimitType.UNKNOWN, description="限制类型")
    original_message: str = Field("", description="原始消息内容")
    reset_time_str: Optional[str] = Field(None, description="重置时间字符串")
    reset_time: Optional[datetime] = Field(None, description="解析后的重置时间")
    parsed_successfully: bool = Field(False, description="时间解析是否成功")
    hours_until_reset: Optional[float] = Field(None, description="距离重置的小时数")
    detection_timestamp: datetime = Field(default_factory=datetime.now, description="检测时间戳")

    class Config:
        """模型配置"""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class FiveHourLimitDetector:
    """
    5小时限制检测器

    检测tmux输出中的限制消息并解析重置时间
    """

    def __init__(self) -> None:
        """
        初始化5小时限制检测器
        """
        # 1. 初始化检测模式
        self._init_patterns()

        # 2. 记录初始化信息
        logger.info("5小时限制检测器初始化完成")

    def _init_patterns(self) -> None:
        """
        初始化检测模式
        """
        # 1. 5小时限制模式
        self.five_hour_patterns: List[Pattern[str]] = [
            # 标准模式: "5-hour limit reached ∙ resets 2:30 PM"
            re.compile(r'5-hour\s+limit\s+reached\s*[∙·•]\s*resets\s+(.+)', re.IGNORECASE),
            # 变体模式: "5 hour limit reached • resets at 2:30 PM"
            re.compile(r'5\s*hour\s+limit\s+reached\s*[∙·•]\s*resets\s+at\s+(.+)', re.IGNORECASE),
            # 简化模式: "5h limit reached, resets 14:30"
            re.compile(r'5h?\s*limit\s+reached[,.]?\s*resets\s+(.+)', re.IGNORECASE),
        ]

        # 2. 其他限制模式
        self.rate_limit_patterns: List[Pattern[str]] = [
            re.compile(r'rate\s+limit\s+exceeded', re.IGNORECASE),
            re.compile(r'too\s+many\s+requests', re.IGNORECASE),
        ]

        # 3. 日限制模式
        self.daily_limit_patterns: List[Pattern[str]] = [
            re.compile(r'daily\s+limit\s+reached\s*[∙·•]\s*resets\s+(.+)', re.IGNORECASE),
            re.compile(r'24-hour\s+limit\s+reached\s*[∙·•]\s*resets\s+(.+)', re.IGNORECASE),
        ]

    def detect_limit_message(self, message: str) -> LimitDetectionResult:
        """
        检测限制消息

        Args:
            message: 待检测的消息内容

        Returns:
            LimitDetectionResult: 检测结果
        """
        # 1. 初始化结果
        result = LimitDetectionResult(original_message=message.strip())

        # 2. 检测5小时限制
        five_hour_result = self._detect_five_hour_limit(message)
        if five_hour_result.detected:
            return five_hour_result

        # 3. 检测日限制
        daily_result = self._detect_daily_limit(message)
        if daily_result.detected:
            return daily_result

        # 4. 检测频率限制
        rate_limit_result = self._detect_rate_limit(message)
        if rate_limit_result.detected:
            return rate_limit_result

        # 5. 未检测到任何限制
        return result

    def _detect_five_hour_limit(self, message: str) -> LimitDetectionResult:
        """
        检测5小时限制

        Args:
            message: 消息内容

        Returns:
            LimitDetectionResult: 检测结果
        """
        # 1. 尝试匹配5小时限制模式
        for pattern in self.five_hour_patterns:
            match = pattern.search(message)
            if match:
                # 2. 创建检测结果
                result = LimitDetectionResult(
                    detected=True,
                    limit_type=LimitType.FIVE_HOUR,
                    original_message=message.strip(),
                    reset_time_str=match.group(1).strip()
                )

                # 3. 解析重置时间
                self._parse_reset_time(result)

                # 4. 记录检测结果
                logger.info(f"检测到5小时限制: {result.reset_time_str}")
                return result

        # 5. 未检测到5小时限制
        return LimitDetectionResult(original_message=message.strip())

    def _detect_daily_limit(self, message: str) -> LimitDetectionResult:
        """
        检测日限制

        Args:
            message: 消息内容

        Returns:
            LimitDetectionResult: 检测结果
        """
        # 1. 尝试匹配日限制模式
        for pattern in self.daily_limit_patterns:
            match = pattern.search(message)
            if match:
                # 2. 创建检测结果
                result = LimitDetectionResult(
                    detected=True,
                    limit_type=LimitType.DAILY,
                    original_message=message.strip(),
                    reset_time_str=match.group(1).strip()
                )

                # 3. 解析重置时间
                self._parse_reset_time(result)

                # 4. 记录检测结果
                logger.info(f"检测到日限制: {result.reset_time_str}")
                return result

        # 5. 未检测到日限制
        return LimitDetectionResult(original_message=message.strip())

    def _detect_rate_limit(self, message: str) -> LimitDetectionResult:
        """
        检测频率限制

        Args:
            message: 消息内容

        Returns:
            LimitDetectionResult: 检测结果
        """
        # 1. 尝试匹配频率限制模式
        for pattern in self.rate_limit_patterns:
            if pattern.search(message):
                # 2. 创建检测结果
                result = LimitDetectionResult(
                    detected=True,
                    limit_type=LimitType.RATE_LIMIT,
                    original_message=message.strip()
                )

                # 3. 记录检测结果
                logger.info("检测到频率限制")
                return result

        # 4. 未检测到频率限制
        return LimitDetectionResult(original_message=message.strip())

    def _parse_reset_time(self, result: LimitDetectionResult) -> None:
        """
        解析重置时间

        Args:
            result: 检测结果，会被直接修改
        """
        # 1. 检查是否有时间字符串
        if not result.reset_time_str:
            return

        # 2. 尝试解析时间
        try:
            parsed_time = self._parse_time_string(result.reset_time_str)
            if parsed_time:
                # 3. 设置解析结果
                result.reset_time = parsed_time
                result.parsed_successfully = True

                # 4. 计算距离重置的时间
                current_time = datetime.now()
                time_diff = parsed_time - current_time
                result.hours_until_reset = time_diff.total_seconds() / 3600

                # 5. 记录解析成功
                logger.info(f"时间解析成功: {parsed_time.isoformat()}")

        except Exception as e:
            # 6. 处理解析异常
            logger.warning(f"时间解析失败: {result.reset_time_str}, 错误: {e}")
            result.parsed_successfully = False

    def _parse_time_string(self, time_str: str) -> Optional[datetime]:
        """
        解析时间字符串

        Args:
            time_str: 时间字符串

        Returns:
            Optional[datetime]: 解析后的时间，失败返回None
        """
        # 1. 清理时间字符串
        clean_time = time_str.strip()

        # 2. 常用时间格式
        time_formats = [
            # 12小时制
            "%I:%M %p",      # "2:30 PM"
            "%I:%M%p",       # "2:30PM"
            "%I %p",         # "2 PM"
            "%I%p",          # "2PM"

            # 24小时制
            "%H:%M",         # "14:30"
            "%H.%M",         # "14.30"
            "%H:%M:%S",      # "14:30:00"

            # 带日期
            "%Y-%m-%d %H:%M",    # "2024-01-15 14:30"
            "%m/%d %I:%M %p",    # "01/15 2:30 PM"
            "%d/%m %H:%M",       # "15/01 14:30"
        ]

        # 3. 尝试不同格式解析
        current_date = datetime.now().date()

        for fmt in time_formats:
            try:
                # 4. 尝试解析时间
                if "%Y" in fmt or "%m" in fmt or "%d" in fmt:
                    # 包含日期的格式
                    parsed = datetime.strptime(clean_time, fmt)
                else:
                    # 只有时间的格式，使用今天的日期
                    parsed_time = datetime.strptime(clean_time, fmt).time()
                    parsed = datetime.combine(current_date, parsed_time)

                # 5. 如果解析的时间是过去时间，假设是明天
                if parsed < datetime.now():
                    parsed += timedelta(days=1)

                # 6. 返回解析结果
                return parsed

            except ValueError:
                continue

        # 7. 尝试相对时间解析 (如 "in 5 hours", "5小时后")
        relative_time = self._parse_relative_time(clean_time)
        if relative_time:
            return relative_time

        # 8. 解析失败
        return None

    def _parse_relative_time(self, time_str: str) -> Optional[datetime]:
        """
        解析相对时间

        Args:
            time_str: 时间字符串

        Returns:
            Optional[datetime]: 解析后的时间
        """
        # 1. 相对时间模式
        relative_patterns = [
            (r'in\s+(\d+)\s+hours?', lambda h: datetime.now() + timedelta(hours=int(h))),
            (r'in\s+(\d+)\s+mins?', lambda m: datetime.now() + timedelta(minutes=int(m))),
            (r'(\d+)\s*小时后', lambda h: datetime.now() + timedelta(hours=int(h))),
            (r'(\d+)\s*分钟后', lambda m: datetime.now() + timedelta(minutes=int(m))),
            (r'(\d+)h\s*later', lambda h: datetime.now() + timedelta(hours=int(h))),
            (r'(\d+)m\s*later', lambda m: datetime.now() + timedelta(minutes=int(m))),
        ]

        # 2. 尝试匹配相对时间
        for pattern, calculator in relative_patterns:
            match = re.search(pattern, time_str, re.IGNORECASE)
            if match:
                try:
                    return calculator(match.group(1))
                except (ValueError, IndexError):
                    continue

        # 3. 解析失败
        return None

    def get_supported_patterns(self) -> Dict[str, List[str]]:
        """
        获取支持的时间模式

        Returns:
            Dict[str, List[str]]: 支持的模式列表
        """
        # 1. 返回支持的模式
        return {
            "5_hour_patterns": [
                "5-hour limit reached ∙ resets 2:30 PM",
                "5 hour limit reached • resets at 14:30",
                "5h limit reached, resets 2:30 PM"
            ],
            "time_formats": [
                "2:30 PM (12小时制)",
                "14:30 (24小时制)",
                "2024-01-15 14:30 (带日期)",
                "in 5 hours (相对时间)",
                "5小时后 (中文相对时间)"
            ],
            "daily_patterns": [
                "daily limit reached ∙ resets tomorrow 9:00 AM",
                "24-hour limit reached • resets at midnight"
            ],
            "rate_limit_patterns": [
                "rate limit exceeded",
                "too many requests"
            ]
        }