# -*- coding: utf-8 -*-
"""
限流管理器

@description 实现30秒频率限流机制，支持状态存储和管理
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum, unique

# 配置日志系统
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@unique
class RateLimitState(Enum):
    """限流状态枚举"""
    NORMAL = "normal"
    LIMITED = "limited"
    BLOCKED = "blocked"


class RateLimitConfig(BaseModel):
    """限流配置数据模型"""

    rate_limit_seconds: int = Field(30, description="限流时间间隔（秒）", ge=1, le=3600)
    max_requests_per_interval: int = Field(1, description="间隔内最大请求数", ge=1, le=100)
    resolve_message: str = Field("hi", description="解除限流的消息内容")
    storage_file_path: str = Field(".rate_limit_state.json", description="状态存储文件路径")
    cleanup_after_hours: int = Field(24, description="清理过期记录的小时数", ge=1, le=168)

    model_config = ConfigDict()


class RateLimitRecord(BaseModel):
    """限流记录数据模型"""

    request_id: str = Field(..., description="请求ID")
    timestamp: datetime = Field(..., description="请求时间戳")
    source_session: str = Field(..., description="源会话标识")
    request_type: str = Field(..., description="请求类型")
    is_resolve_attempt: bool = Field(False, description="是否为解除限流尝试")

    model_config = ConfigDict(
        # json_encoders deprecated in V2 - datetime fields will use default serialization
    )


class RateLimitStatus(BaseModel):
    """限流状态数据模型"""

    state: RateLimitState = Field(..., description="当前限流状态")
    last_request_time: Optional[datetime] = Field(None, description="最后请求时间")
    requests_in_window: int = Field(0, description="当前时间窗口内请求数", ge=0)
    next_allowed_time: Optional[datetime] = Field(None, description="下次允许请求时间")
    blocked_until: Optional[datetime] = Field(None, description="阻塞截止时间")
    total_blocked_requests: int = Field(0, description="总阻塞请求数", ge=0)

    model_config = ConfigDict(
        # json_encoders deprecated in V2 - datetime fields will use default serialization
    )


class RateLimiterManager:
    """
    限流管理器

    负责30秒频率限流和状态管理
    """

    def __init__(self, config: Optional[RateLimitConfig] = None) -> None:
        """
        初始化限流管理器

        Args:
            config: 限流配置，使用默认配置如果未提供
        """
        # 1. 设置限流配置
        self.config = config or RateLimitConfig()

        # 2. 初始化状态存储
        self.storage_path = Path(self.config.storage_file_path)
        self.current_status = self._load_status()

        # 3. 初始化请求记录
        self.request_records: List[RateLimitRecord] = []

        # 4. 记录初始化信息
        logger.info(f"限流管理器初始化: 间隔={self.config.rate_limit_seconds}秒")

    def check_rate_limit(self, request_data: Dict[str, str]) -> Dict[str, any]:
        """
        检查请求是否超过限流

        Args:
            request_data: 请求数据，包含source_session和request_type

        Returns:
            Dict[str, any]: 检查结果
        """
        # 1. 生成请求ID
        import uuid
        request_id = str(uuid.uuid4())

        # 2. 获取当前时间
        current_time = datetime.now()

        # 3. 清理过期记录
        self._cleanup_expired_records(current_time)

        # 4. 检查当前状态
        is_allowed = self._check_request_allowed(current_time, request_data)

        # 5. 记录请求
        record = RateLimitRecord(
            request_id=request_id,
            timestamp=current_time,
            source_session=request_data.get("source_session", "unknown"),
            request_type=request_data.get("request_type", "unknown"),
            is_resolve_attempt=self._is_resolve_message(request_data)
        )
        self.request_records.append(record)

        # 6. 更新状态
        self._update_status(current_time, is_allowed)

        # 7. 保存状态
        self._save_status()

        # 8. 返回检查结果
        return self._build_check_result(request_id, is_allowed, current_time)

    def _check_request_allowed(self, current_time: datetime, request_data: Dict[str, str]) -> bool:
        """
        检查请求是否被允许

        Args:
            current_time: 当前时间
            request_data: 请求数据

        Returns:
            bool: 是否允许请求
        """
        # 1. 检查是否为解除限流消息
        if self._is_resolve_message(request_data):
            logger.info("检测到解除限流消息，允许通过")
            return True

        # 2. 检查是否在阻塞期间
        if (self.current_status.blocked_until and
            current_time < self.current_status.blocked_until):
            logger.warning("当前处于阻塞期间，拒绝请求")
            return False

        # 3. 检查时间窗口内请求数量
        window_start = current_time - timedelta(seconds=self.config.rate_limit_seconds)
        requests_in_window = self._count_requests_in_window(window_start, current_time)

        # 4. 判断是否超过限制
        if requests_in_window >= self.config.max_requests_per_interval:
            logger.warning(f"请求数量超过限制: {requests_in_window}/{self.config.max_requests_per_interval}")
            return False

        # 5. 请求被允许
        return True

    def _is_resolve_message(self, request_data: Dict[str, str]) -> bool:
        """
        检查是否为解除限流消息

        Args:
            request_data: 请求数据

        Returns:
            bool: 是否为解除限流消息
        """
        # 1. 获取消息内容
        message = request_data.get("message", "").strip().lower()

        # 2. 检查是否匹配解除限流消息
        resolve_message = self.config.resolve_message.strip().lower()

        # 3. 返回匹配结果
        return message == resolve_message

    def _count_requests_in_window(self, window_start: datetime, window_end: datetime) -> int:
        """
        统计时间窗口内的请求数量

        Args:
            window_start: 窗口开始时间
            window_end: 窗口结束时间

        Returns:
            int: 请求数量
        """
        # 1. 过滤时间窗口内的记录
        count = 0
        for record in self.request_records:
            if (window_start <= record.timestamp <= window_end and
                not record.is_resolve_attempt):
                count += 1

        # 2. 返回计数
        return count

    def _update_status(self, current_time: datetime, is_allowed: bool) -> None:
        """
        更新限流状态

        Args:
            current_time: 当前时间
            is_allowed: 请求是否被允许
        """
        # 1. 更新最后请求时间
        self.current_status.last_request_time = current_time

        # 2. 更新状态
        if is_allowed:
            self.current_status.state = RateLimitState.NORMAL
            self.current_status.blocked_until = None
        else:
            self.current_status.state = RateLimitState.LIMITED
            self.current_status.next_allowed_time = (
                current_time + timedelta(seconds=self.config.rate_limit_seconds)
            )
            self.current_status.total_blocked_requests += 1

        # 3. 更新窗口内请求数
        window_start = current_time - timedelta(seconds=self.config.rate_limit_seconds)
        self.current_status.requests_in_window = self._count_requests_in_window(
            window_start, current_time
        )

    def _build_check_result(self, request_id: str, is_allowed: bool, current_time: datetime) -> Dict[str, any]:
        """
        构建检查结果

        Args:
            request_id: 请求ID
            is_allowed: 是否允许
            current_time: 当前时间

        Returns:
            Dict[str, any]: 检查结果
        """
        # 1. 构建基础结果
        result = {
            "request_id": request_id,
            "is_allowed": is_allowed,
            "current_state": self.current_status.state.value,
            "timestamp": current_time.isoformat(),
            "requests_in_window": self.current_status.requests_in_window,
            "rate_limit_seconds": self.config.rate_limit_seconds
        }

        # 2. 添加限流信息
        if not is_allowed:
            result["next_allowed_time"] = self.current_status.next_allowed_time.isoformat()
            result["resolve_message"] = self.config.resolve_message
            result["message"] = f"请求被限流，请等待{self.config.rate_limit_seconds}秒或发送'{self.config.resolve_message}'消息"

        # 3. 返回结果
        return result

    def _cleanup_expired_records(self, current_time: datetime) -> None:
        """
        清理过期的请求记录

        Args:
            current_time: 当前时间
        """
        # 1. 计算过期时间
        expiry_time = current_time - timedelta(hours=self.config.cleanup_after_hours)

        # 2. 过滤过期记录
        before_count = len(self.request_records)
        self.request_records = [
            record for record in self.request_records
            if record.timestamp > expiry_time
        ]

        # 3. 记录清理结果
        cleaned_count = before_count - len(self.request_records)
        if cleaned_count > 0:
            logger.info(f"清理过期请求记录: {cleaned_count} 条")

    def _load_status(self) -> RateLimitStatus:
        """
        从文件加载限流状态

        Returns:
            RateLimitStatus: 加载的状态
        """
        try:
            # 1. 检查文件是否存在
            if not self.storage_path.exists():
                return RateLimitStatus(state=RateLimitState.NORMAL)

            # 2. 读取文件内容
            content = self.storage_path.read_text(encoding='utf-8')
            data = json.loads(content)

            # 3. 解析状态数据
            return RateLimitStatus(**data)

        except Exception as e:
            # 4. 处理加载异常
            logger.warning(f"加载限流状态失败: {e}")
            return RateLimitStatus(state=RateLimitState.NORMAL)

    def _save_status(self) -> None:
        """保存限流状态到文件"""
        try:
            # 1. 序列化状态数据
            status_data = self.current_status.model_dump()

            # 2. 写入文件
            self.storage_path.write_text(
                json.dumps(status_data, ensure_ascii=False, indent=2),
                encoding='utf-8'
            )

        except Exception as e:
            # 3. 处理保存异常
            logger.error(f"保存限流状态失败: {e}")

    def get_current_status(self) -> RateLimitStatus:
        """
        获取当前限流状态

        Returns:
            RateLimitStatus: 当前状态
        """
        # 1. 返回当前状态
        return self.current_status

    def manual_reset(self) -> Dict[str, any]:
        """
        手动重置限流状态

        Returns:
            Dict[str, any]: 重置结果
        """
        # 1. 重置状态
        self.current_status = RateLimitStatus(state=RateLimitState.NORMAL)

        # 2. 清空请求记录
        self.request_records.clear()

        # 3. 保存状态
        self._save_status()

        # 4. 记录重置操作
        logger.info("手动重置限流状态完成")

        # 5. 返回重置结果
        return {
            "status": "success",
            "message": "限流状态已重置",
            "timestamp": datetime.now().isoformat()
        }