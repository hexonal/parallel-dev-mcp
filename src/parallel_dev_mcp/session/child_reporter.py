# -*- coding: utf-8 -*-
"""
Child会话SessionEnd事件上报器

@description 实现Child会话退出状态上报到Master的/msg/send-child端点
"""

import json
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List
from pydantic import BaseModel, Field, ConfigDict
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .session_manager import MasterSessionDetector
from .._internal.config_tools import get_environment_config

# 配置日志系统
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class SessionEndReport(BaseModel):
    """
    SessionEnd事件上报数据模型

    包含Child会话退出时需要上报的完整信息
    """

    task_id: str = Field(..., description="任务ID")
    session_name: str = Field(..., description="tmux会话名称")
    exit_status: str = Field(..., description="退出状态")
    exit_time: datetime = Field(..., description="退出时间")
    worktree_path: Optional[str] = Field(None, description="worktree路径")
    session_duration: Optional[float] = Field(None, description="会话持续时间（秒）")
    project_prefix: str = Field(..., description="项目前缀")
    error_message: Optional[str] = Field(None, description="错误信息")

    model_config = ConfigDict(
        # 1. JSON编码器配置
        # json_encoders deprecated in V2 - datetime fields will use default serialization
    )


class ReportStatus(BaseModel):
    """
    上报状态数据模型

    跟踪上报请求的状态和结果
    """

    report_id: str = Field(..., description="上报ID")
    task_id: str = Field(..., description="任务ID")
    status: str = Field(..., description="上报状态：pending/success/failed")
    attempts: int = Field(0, description="尝试次数", ge=0)
    last_attempt: Optional[datetime] = Field(None, description="最后尝试时间")
    error_message: Optional[str] = Field(None, description="错误信息")
    response_data: Optional[Dict] = Field(None, description="响应数据")

    model_config = ConfigDict(
        # 1. JSON编码器配置
        # json_encoders deprecated in V2 - datetime fields will use default serialization
    )


class ChildSessionReporter:
    """
    Child会话事件上报器

    负责Child会话SessionEnd事件的上报和状态跟踪
    """

    def __init__(self, master_host: str = "127.0.0.1", master_port: int = 5001) -> None:
        """
        初始化Child会话上报器

        Args:
            master_host: Master服务主机地址
            master_port: Master服务端口
        """
        # 1. 设置Master服务地址
        self.master_host = master_host
        self.master_port = master_port
        self.master_url = f"http://{master_host}:{master_port}"

        # 2. 初始化会话检测器
        self.detector = MasterSessionDetector()

        # 3. 配置HTTP会话
        self.session = requests.Session()
        self._configure_http_session()

        # 4. 初始化上报状态跟踪
        self.report_statuses: Dict[str, ReportStatus] = {}

        # 5. 记录初始化信息
        logger.info(f"Child会话上报器初始化: {self.master_url}")

    def _configure_http_session(self) -> None:
        """
        配置HTTP会话的重试策略和适配器
        """
        # 1. 配置重试策略
        retry_strategy = Retry(
            total=3,  # 总重试次数
            status_forcelist=[429, 500, 502, 503, 504],  # 需要重试的HTTP状态码
            method_whitelist=["HEAD", "GET", "POST"],  # 允许重试的HTTP方法
            backoff_factor=1,  # 重试间隔因子
        )

        # 2. 创建HTTP适配器
        adapter = HTTPAdapter(max_retries=retry_strategy)

        # 3. 挂载适配器
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # 4. 设置超时
        self.session.timeout = 30

        # 5. 记录配置信息
        logger.debug("HTTP会话重试策略配置完成")

    def report_session_end(
        self,
        task_id: str,
        exit_status: str,
        error_message: Optional[str] = None,
        session_start_time: Optional[datetime] = None,
    ) -> bool:
        """
        上报Child会话SessionEnd事件

        Args:
            task_id: 任务ID
            exit_status: 退出状态（success/error/timeout/cancelled）
            error_message: 错误信息（可选）
            session_start_time: 会话开始时间（用于计算持续时间）

        Returns:
            bool: 上报是否成功
        """
        try:
            # 1. 获取当前会话信息
            current_session = self.detector.get_current_tmux_session()
            if not current_session:
                logger.error("无法获取当前tmux会话名称")
                return False

            # 2. 验证是否为Child会话
            if not self.detector.is_child_session(current_session):
                logger.warning(f"当前会话不是Child会话: {current_session}")
                return False

            # 3. 获取环境配置
            env_config = get_environment_config()

            # 4. 计算会话持续时间
            session_duration = None
            if session_start_time:
                session_duration = (datetime.now() - session_start_time).total_seconds()

            # 5. 构建worktree路径
            worktree_path = str(Path.cwd() / "worktree" / task_id)

            # 6. 创建上报数据
            report_data = SessionEndReport(
                task_id=task_id,
                session_name=current_session,
                exit_status=exit_status,
                exit_time=datetime.now(),
                worktree_path=worktree_path,
                session_duration=session_duration,
                project_prefix=env_config.project_prefix,
                error_message=error_message,
            )

            # 7. 执行上报
            success = self._send_report(report_data)

            # 8. 记录上报结果
            if success:
                logger.info(f"Child会话SessionEnd上报成功: {task_id}")
            else:
                logger.error(f"Child会话SessionEnd上报失败: {task_id}")

            # 9. 返回上报结果
            return success

        except Exception as e:
            # 10. 处理上报异常
            logger.error(f"Child会话SessionEnd上报异常: {e}")
            return False

    def _send_report(self, report_data: SessionEndReport) -> bool:
        """
        发送上报数据到Master服务

        Args:
            report_data: 上报数据

        Returns:
            bool: 发送是否成功
        """
        # 1. 生成上报ID
        import uuid

        report_id = str(uuid.uuid4())

        # 2. 创建上报状态跟踪
        status = ReportStatus(
            report_id=report_id,
            task_id=report_data.task_id,
            status="pending",
            attempts=0,
            last_attempt=None,
        )

        try:
            # 3. 准备请求数据
            endpoint_url = f"{self.master_url}/msg/send-child"
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "parallel-dev-mcp-child-reporter/1.0.0",
            }

            # 4. 转换为请求格式
            request_data = {
                "taskId": report_data.task_id,
                "sessionName": report_data.session_name,
                "status": report_data.exit_status,
                "exitTime": report_data.exit_time.isoformat(),
                "worktreePath": report_data.worktree_path,
                "sessionDuration": report_data.session_duration,
                "projectPrefix": report_data.project_prefix,
                "errorMessage": report_data.error_message,
                "reportId": report_id,
            }

            # 5. 发送HTTP请求
            status.attempts += 1
            status.last_attempt = datetime.now()

            response = self.session.post(
                endpoint_url, json=request_data, headers=headers, timeout=30
            )

            # 6. 检查响应状态
            if response.status_code == 200:
                # 7. 处理成功响应
                status.status = "success"
                try:
                    status.response_data = response.json()
                except json.JSONDecodeError:
                    status.response_data = {"raw_response": response.text}

                logger.info(f"上报成功: {endpoint_url} -> {response.status_code}")
                self.report_statuses[report_id] = status
                return True

            else:
                # 8. 处理失败响应
                status.status = "failed"
                status.error_message = f"HTTP {response.status_code}: {response.text}"
                logger.error(f"上报失败: {endpoint_url} -> {response.status_code}")
                self.report_statuses[report_id] = status
                return False

        except requests.exceptions.RequestException as e:
            # 9. 处理网络异常
            status.status = "failed"
            status.error_message = f"网络请求异常: {e}"
            logger.error(f"上报网络异常: {e}")
            self.report_statuses[report_id] = status
            return False

        except Exception as e:
            # 10. 处理其他异常
            status.status = "failed"
            status.error_message = f"上报异常: {e}"
            logger.error(f"上报异常: {e}")
            self.report_statuses[report_id] = status
            return False

    def report_with_retry(
        self,
        task_id: str,
        exit_status: str,
        max_retries: int = 3,
        retry_delay: float = 2.0,
        error_message: Optional[str] = None,
        session_start_time: Optional[datetime] = None,
    ) -> bool:
        """
        带重试机制的上报方法

        Args:
            task_id: 任务ID
            exit_status: 退出状态
            max_retries: 最大重试次数
            retry_delay: 重试延迟（秒）
            error_message: 错误信息
            session_start_time: 会话开始时间

        Returns:
            bool: 上报是否成功
        """
        # 1. 执行重试循环
        for attempt in range(max_retries + 1):
            try:
                # 2. 记录尝试信息
                if attempt > 0:
                    logger.info(f"重试上报 ({attempt}/{max_retries}): {task_id}")

                # 3. 执行上报
                success = self.report_session_end(
                    task_id, exit_status, error_message, session_start_time
                )

                # 4. 检查上报结果
                if success:
                    if attempt > 0:
                        logger.info(f"重试上报成功: {task_id}")
                    return True

                # 5. 如果不是最后一次尝试，等待后重试
                if attempt < max_retries:
                    logger.warning(f"上报失败，{retry_delay}秒后重试: {task_id}")
                    time.sleep(retry_delay)
                    # 6. 增加延迟时间（指数退避）
                    retry_delay *= 1.5

            except Exception as e:
                # 7. 处理重试异常
                logger.error(f"重试上报异常 ({attempt}/{max_retries}): {e}")
                if attempt < max_retries:
                    time.sleep(retry_delay)

        # 8. 所有重试都失败
        logger.error(f"上报最终失败，已尝试 {max_retries + 1} 次: {task_id}")
        return False

    def get_report_status(self, report_id: str) -> Optional[ReportStatus]:
        """
        获取上报状态

        Args:
            report_id: 上报ID

        Returns:
            Optional[ReportStatus]: 上报状态，不存在时返回None
        """
        # 1. 返回上报状态
        return self.report_statuses.get(report_id)

    def list_report_statuses(
        self, task_id: Optional[str] = None
    ) -> List[ReportStatus]:
        """
        列出上报状态

        Args:
            task_id: 任务ID过滤条件（可选）

        Returns:
            List[ReportStatus]: 上报状态列表
        """
        # 1. 获取所有状态
        statuses = list(self.report_statuses.values())

        # 2. 按任务ID过滤
        if task_id:
            statuses = [s for s in statuses if s.task_id == task_id]

        # 3. 按时间排序
        statuses.sort(key=lambda x: x.last_attempt or datetime.min, reverse=True)

        # 4. 返回状态列表
        return statuses

    def cleanup_old_statuses(self, max_age_hours: int = 24) -> int:
        """
        清理过期的上报状态记录

        Args:
            max_age_hours: 最大保留时间（小时）

        Returns:
            int: 清理的记录数量
        """
        # 1. 计算过期时间
        expiry_time = datetime.now() - timedelta(hours=max_age_hours)

        # 2. 找出过期记录
        expired_ids = []
        for report_id, status in self.report_statuses.items():
            if status.last_attempt and status.last_attempt < expiry_time:
                expired_ids.append(report_id)

        # 3. 删除过期记录
        for report_id in expired_ids:
            del self.report_statuses[report_id]

        # 4. 记录清理结果
        if expired_ids:
            logger.info(f"清理过期上报状态记录: {len(expired_ids)} 条")

        # 5. 返回清理数量
        return len(expired_ids)


def create_child_reporter(
    master_host: str = "127.0.0.1", master_port: int = 5001
) -> ChildSessionReporter:
    """
    创建Child会话上报器实例

    Args:
        master_host: Master服务主机地址
        master_port: Master服务端口

    Returns:
        ChildSessionReporter: 配置好的上报器实例
    """
    # 1. 尝试从环境配置获取Master服务地址
    try:
        env_config = get_environment_config()
        if hasattr(env_config, "web_port"):
            master_port = env_config.web_port
    except Exception as e:
        logger.warning(f"获取环境配置失败，使用默认端口: {e}")

    # 2. 创建上报器实例
    reporter = ChildSessionReporter(master_host, master_port)

    # 3. 记录创建信息
    logger.info("Child会话上报器实例创建成功")

    # 4. 返回上报器实例
    return reporter


def report_session_end_quick(
    task_id: str,
    exit_status: str = "success",
    error_message: Optional[str] = None,
) -> bool:
    """
    快速上报SessionEnd事件的便捷函数

    Args:
        task_id: 任务ID
        exit_status: 退出状态
        error_message: 错误信息

    Returns:
        bool: 上报是否成功
    """
    # 1. 创建上报器
    reporter = create_child_reporter()

    # 2. 执行上报
    return reporter.report_with_retry(
        task_id=task_id, exit_status=exit_status, error_message=error_message
    )