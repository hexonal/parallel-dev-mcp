# -*- coding: utf-8 -*-
"""
Flask Web 服务器实现

@description 实现 Master 会话的 Flask Web 服务，处理 hooks 事件和消息发送
"""

import logging
import socket
import subprocess
from pathlib import Path
from typing import Optional, List
from flask import Flask, request, jsonify
from flask_cors import CORS
from pydantic import BaseModel, Field, field_validator, ConfigDict

from .._internal.config_tools import get_environment_config, EnvConfig
from .rate_limiter import create_default_tracker, CallFrequencyTracker
from .limit_handler import create_default_limit_handler, ClaudeLimitHandler
from ..session.child_session_scheduler import (
    start_global_scheduler,
    stop_global_scheduler,
    get_global_scheduler_status,
)

# 配置日志系统
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class FlaskConfigModel(BaseModel):
    """
    Flask 应用配置数据模型

    基于环境变量配置，用于 Flask 应用的初始化和验证
    """

    debug: bool = Field(False, description="调试模式开关")
    host: str = Field("127.0.0.1", description="绑定主机地址")
    port: int = Field(..., description="绑定端口号", ge=1024, le=65535)
    project_prefix: str = Field(..., description="项目前缀，用于会话识别", min_length=1)
    cors_enabled: bool = Field(True, description="是否启用CORS跨域支持")

    @field_validator("port")
    @classmethod
    def validate_port_availability(cls, v: int) -> int:
        """
        验证端口可用性

        Args:
            v: 端口号

        Returns:
            int: 验证后的端口号

        Raises:
            ValueError: 端口已被占用时抛出
        """
        # 1. 检查端口是否被占用
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                result = s.connect_ex(("127.0.0.1", v))
                if result == 0:
                    raise ValueError(f"端口 {v} 已被占用")
        except Exception as e:
            logger.warning(f"无法检查端口占用情况: {str(e)}")

        # 2. 返回验证后的端口
        return v

    model_config = ConfigDict(
        # 1. 启用JSON编码器
        # json_encoders deprecated in V2,
        # 2. 示例数据
        json_schema_extra={
            "example": {
                "debug": False,
                "host": "127.0.0.1",
                "port": 5000,
                "project_prefix": "myproject",
                "cors_enabled": True,
            }
        },
    )


class MessageRequest(BaseModel):
    """
    消息发送请求数据模型

    处理 hooks 事件和消息发送请求的数据验证
    """

    message: Optional[str] = Field(None, description="消息内容", max_length=1000)
    session_id: Optional[str] = Field(None, description="会话ID", max_length=100)
    hook_event_name: str = Field(
        ..., description="hooks事件名称", min_length=1, max_length=50
    )
    skip_limit_check: bool = Field(
        False, description="是否跳过5小时限制检测（避免递归）"
    )

    @field_validator("hook_event_name")
    @classmethod
    def validate_hook_event_name(cls, v: str) -> str:
        """
        验证hooks事件名称

        Args:
            v: 事件名称字符串

        Returns:
            str: 验证后的事件名称

        Raises:
            ValueError: 事件名称无效时抛出
        """
        # 1. 检查支持的事件类型
        valid_events = ["SessionStart", "Stop", "SessionEnd"]
        if v not in valid_events:
            raise ValueError(f"不支持的事件类型: {v}, 支持的类型: {valid_events}")

        # 2. 返回验证后的事件名称
        return v

    model_config = ConfigDict(
        # 1. 启用JSON编码器
        # json_encoders deprecated in V2,
        # 2. 示例数据
        json_schema_extra={
            "example": {
                "message": "test message",
                "session_id": "claude_session_123",
                "hook_event_name": "Stop",
            }
        },
    )


class MessageResponse(BaseModel):
    """
    消息发送响应数据模型

    返回消息发送操作的结果和状态信息
    """

    success: bool = Field(..., description="操作是否成功")
    message: str = Field(..., description="响应消息或错误信息")
    session_id: Optional[str] = Field(None, description="会话ID")
    event_name: Optional[str] = Field(None, description="处理的事件名称")
    frequency_info: Optional[str] = Field(None, description="频率限流信息")

    model_config = ConfigDict(
        # 1. 启用JSON编码器
        # json_encoders deprecated in V2,
        # 2. 示例数据
        json_schema_extra={
            "example": {
                "success": True,
                "message": "消息发送成功",
                "session_id": "claude_session_123",
                "event_name": "Stop",
                "frequency_info": "当前窗口内调用次数: 1/1",
            }
        },
    )


class ChildSessionRequest(BaseModel):
    """
    子会话请求数据模型

    处理子会话 SessionEnd 事件和状态更新请求的数据验证
    """

    task_id: str = Field(..., description="任务ID", min_length=1, max_length=50)
    session_name: Optional[str] = Field(None, description="会话名称", max_length=100)
    exit_status: Optional[int] = Field(None, description="退出状态码")
    worktree_path: Optional[str] = Field(None, description="工作树路径", max_length=500)

    @field_validator("task_id")
    @classmethod
    def validate_task_id(cls, v: str) -> str:
        """
        验证任务ID格式

        Args:
            v: 任务ID字符串

        Returns:
            str: 验证后的任务ID

        Raises:
            ValueError: 任务ID格式无效时抛出
        """
        # 1. 检查任务ID格式（支持数字、字母、下划线、点号）
        import re

        if not re.match(r"^[a-zA-Z0-9._-]+$", v):
            raise ValueError(f"无效的任务ID格式: {v}")

        # 2. 返回验证后的任务ID
        return v

    model_config = ConfigDict(
        # 1. 启用JSON编码器
        # json_encoders deprecated in V2,
        # 2. 示例数据
        json_schema_extra={
            "example": {
                "task_id": "task_123",
                "session_name": "parallel_child_task_123",
                "exit_status": 0,
                "worktree_path": "/path/to/worktree",
            }
        },
    )


class ChildSessionResponse(BaseModel):
    """
    子会话响应数据模型

    返回子会话处理操作的结果和状态信息
    """

    success: bool = Field(..., description="操作是否成功")
    message: str = Field(..., description="响应消息或错误信息")
    task_id: str = Field(..., description="任务ID")
    cleanup_status: str = Field(..., description="会话清理状态")
    update_result: Optional[str] = Field(None, description="状态更新结果")
    frequency_info: Optional[str] = Field(None, description="频率限流信息")

    model_config = ConfigDict(
        # 1. 启用JSON编码器
        # json_encoders deprecated in V2,
        # 2. 示例数据
        json_schema_extra={
            "example": {
                "success": True,
                "message": "子会话处理完成",
                "task_id": "task_123",
                "cleanup_status": "会话已清理",
                "update_result": "状态已更新",
                "frequency_info": "当前窗口内调用次数: 1/1",
            }
        },
    )


def create_flask_config(env_config: Optional[EnvConfig] = None) -> FlaskConfigModel:
    """
    创建 Flask 配置实例

    基于环境变量配置创建 Flask 应用配置

    Args:
        env_config: 环境变量配置实例，如果为 None 则自动获取

    Returns:
        FlaskConfigModel: Flask 配置实例

    Raises:
        ValueError: 配置验证失败时抛出
    """
    # 1. 获取环境变量配置
    if env_config is None:
        env_config = get_environment_config()

    # 2. 创建 Flask 配置
    flask_config = FlaskConfigModel(
        debug=False,  # 生产环境默认关闭调试模式
        host="127.0.0.1",
        port=env_config.web_port,
        project_prefix=env_config.project_prefix,
        cors_enabled=True,
    )

    # 3. 记录配置信息
    logger.info(f"Flask 配置创建: {env_config.project_prefix}:{env_config.web_port}")

    # 4. 返回配置实例
    return flask_config


# 全局频率跟踪器实例
_frequency_tracker: Optional[CallFrequencyTracker] = None

# 全局限制处理器实例
_limit_handler: Optional[ClaudeLimitHandler] = None


def get_frequency_tracker() -> CallFrequencyTracker:
    """
    获取全局频率跟踪器实例

    使用单例模式确保全局只有一个跟踪器实例

    Returns:
        CallFrequencyTracker: 频率跟踪器实例
    """
    global _frequency_tracker
    # 1. 如果实例不存在则创建
    if _frequency_tracker is None:
        _frequency_tracker = create_default_tracker()
        logger.info("创建全局频率跟踪器实例")

    # 2. 返回跟踪器实例
    return _frequency_tracker


def get_limit_handler() -> ClaudeLimitHandler:
    """
    获取全局限制处理器实例

    使用单例模式确保全局只有一个处理器实例

    Returns:
        ClaudeLimitHandler: 限制处理器实例
    """
    global _limit_handler
    # 1. 如果实例不存在则创建
    if _limit_handler is None:
        _limit_handler = create_default_limit_handler()
        logger.info("创建全局限制处理器实例")

    # 2. 返回处理器实例
    return _limit_handler


def execute_tmux_command(command: List[str]) -> str:
    """
    执行 tmux 命令

    安全地执行 tmux 命令并返回结果

    Args:
        command: tmux 命令参数列表

    Returns:
        str: 命令执行结果

    Raises:
        subprocess.CalledProcessError: 命令执行失败时抛出
    """
    # 1. 记录即将执行的命令
    logger.info(f"执行 tmux 命令: {' '.join(command)}")

    # 2. 执行命令并捕获输出
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, timeout=10, check=True  # 10秒超时
        )

        # 3. 记录成功结果
        logger.info(f"tmux 命令执行成功: {result.stdout.strip()}")
        return result.stdout.strip()

    except subprocess.CalledProcessError as e:
        # 4. 记录错误信息
        error_msg = f"tmux 命令执行失败: {e.stderr.strip()}"
        logger.error(error_msg)
        raise

    except subprocess.TimeoutExpired:
        # 5. 处理超时情况
        error_msg = "tmux 命令执行超时"
        logger.error(error_msg)
        raise subprocess.CalledProcessError(1, command, stderr=error_msg)


def send_message_to_session(session_name: str, message: str) -> bool:
    """
    向指定会话发送消息

    使用 tmux send-keys 命令向会话发送消息

    Args:
        session_name: 会话名称
        message: 要发送的消息

    Returns:
        bool: 发送是否成功
    """
    # 1. 构建 tmux send-keys 命令
    command = ["tmux", "send-keys", "-t", session_name, message, "Enter"]

    # 2. 执行命令
    try:
        execute_tmux_command(command)
        logger.info(f"消息发送成功: {session_name} <- {message}")
        return True

    except subprocess.CalledProcessError:
        # 3. 处理发送失败
        logger.error(f"消息发送失败: {session_name} <- {message}")
        return False


def save_session_binding(session_id: str, project_prefix: str) -> bool:
    """
    保存会话绑定信息

    将会话ID写入session_id.txt文件，用于SessionStart事件

    Args:
        session_id: 会话ID
        project_prefix: 项目前缀

    Returns:
        bool: 保存是否成功
    """
    # 1. 创建文件路径
    session_file = Path("session_id.txt")

    # 2. 写入会话ID
    try:
        with open(session_file, "w", encoding="utf-8") as f:
            f.write(session_id)

        # 3. 记录成功信息
        logger.info(f"会话绑定保存成功: {session_id} -> {session_file}")
        return True

    except Exception as e:
        # 4. 处理保存失败
        logger.error(f"会话绑定保存失败: {session_id} - {str(e)}")
        return False


def cleanup_child_session(task_id: str, project_prefix: str) -> str:
    """
    清理子会话

    使用 tmux kill-session 命令终止指定的子会话

    Args:
        task_id: 任务ID
        project_prefix: 项目前缀

    Returns:
        str: 清理状态描述
    """
    # 1. 构建子会话名称
    child_session_name = f"{project_prefix}_child_{task_id}"

    # 2. 构建 tmux kill-session 命令
    command = ["tmux", "kill-session", "-t", child_session_name]

    # 3. 执行清理命令
    try:
        execute_tmux_command(command)
        logger.info(f"子会话清理成功: {child_session_name}")
        return "会话已清理"

    except subprocess.CalledProcessError as e:
        # 4. 处理清理失败（可能会话不存在）
        if "can't find session" in str(e.stderr).lower():
            logger.warning(f"子会话不存在，无需清理: {child_session_name}")
            return "会话不存在"
        else:
            logger.error(f"子会话清理失败: {child_session_name} - {str(e)}")
            return "清理失败"


def update_child_session_status(
    task_id: str,
    session_name: str,
    exit_status: Optional[int],
    worktree_path: Optional[str],
) -> str:
    """
    更新子会话状态

    使用 MasterResourceManager 更新子会话状态到 MCP Resource

    Args:
        task_id: 任务ID
        session_name: 会话名称
        exit_status: 退出状态码
        worktree_path: 工作树路径

    Returns:
        str: 更新结果描述
    """
    # 1. 记录状态更新信息
    logger.info(
        f"子会话状态更新: task_id={task_id}, session_name={session_name}, "
        f"exit_status={exit_status}, worktree_path={worktree_path}"
    )

    try:
        # 2. 导入资源管理器
        from ..resources.master_resource import master_resource_manager

        # 3. 确定会话状态
        status = "completed" if exit_status is not None else "active"

        # 4. 更新子会话状态
        success = master_resource_manager.update_child_session(
            task_id=task_id,
            session_name=session_name,
            status=status,
            exit_status=exit_status,
            worktree_path=worktree_path,
        )

        # 5. 返回更新结果
        if success:
            return "状态已更新到MCP Resource"
        else:
            return "MCP Resource更新失败"

    except Exception as e:
        # 6. 处理更新异常
        logger.error(f"更新子会话状态异常: {e}")
        return f"状态更新异常: {str(e)}"


def create_app(config: Optional[FlaskConfigModel] = None) -> Flask:
    """
    创建 Flask 应用实例

    使用工厂模式创建 Flask 应用，支持不同配置的加载

    Args:
        config: Flask 配置实例，如果为 None 则使用默认配置

    Returns:
        Flask: Flask 应用实例
    """
    # 1. 初始化 Flask 应用
    app = Flask(__name__)

    # 2. 获取配置实例
    if config is None:
        config = create_flask_config()

    # 3. 设置 Flask 应用配置
    app.config["DEBUG"] = config.debug
    app.config["HOST"] = config.host
    app.config["PORT"] = config.port
    app.config["PROJECT_PREFIX"] = config.project_prefix

    # 4. 配置 JSON 序列化
    app.config["JSON_SORT_KEYS"] = False
    app.config["JSONIFY_PRETTYPRINT_REGULAR"] = True

    # 5. 启用 CORS 跨域支持
    if config.cors_enabled:
        CORS(app, origins="*", methods=["GET", "POST", "OPTIONS"])
        logger.info("CORS 跨域支持已启用")

    # 6. 配置日志级别
    if config.debug:
        app.logger.setLevel(logging.DEBUG)
    else:
        app.logger.setLevel(logging.INFO)

    # 7. 添加路由端点
    @app.route("/msg/send", methods=["POST"])
    def send_message():
        """
        处理消息发送请求

        处理 Master hooks 的 Stop/SessionEnd 事件，集成限流和 tmux 消息发送

        Returns:
            JSON 响应，包含操作结果和状态信息
        """
        try:
            # 1. 解析请求数据
            request_data = request.get_json()
            if not request_data:
                return (
                    jsonify(
                        MessageResponse(
                            success=False, message="请求体不能为空"
                        ).model_dump()
                    ),
                    400,
                )

            # 2. 验证请求数据
            try:
                msg_request = MessageRequest(**request_data)
            except Exception as e:
                return (
                    jsonify(
                        MessageResponse(
                            success=False, message=f"请求数据验证失败: {str(e)}"
                        ).model_dump()
                    ),
                    400,
                )

            # 3. 获取频率跟踪器
            tracker = get_frequency_tracker()

            # 4. 处理不同的事件类型
            if msg_request.hook_event_name == "SessionStart":
                # SessionStart: 保存会话绑定
                if not msg_request.session_id:
                    return (
                        jsonify(
                            MessageResponse(
                                success=False,
                                message="SessionStart 事件需要提供 session_id",
                            ).model_dump()
                        ),
                        400,
                    )

                success = save_session_binding(
                    msg_request.session_id, config.project_prefix
                )

                return jsonify(
                    MessageResponse(
                        success=success,
                        message="会话绑定成功" if success else "会话绑定失败",
                        session_id=msg_request.session_id,
                        event_name=msg_request.hook_event_name,
                    ).model_dump()
                )

            elif msg_request.hook_event_name == "Stop":
                # Stop: 发送消息到会话
                if not msg_request.message or not msg_request.session_id:
                    return (
                        jsonify(
                            MessageResponse(
                                success=False,
                                message="Stop 事件需要提供 message 和 session_id",
                            ).model_dump()
                        ),
                        400,
                    )

                # 发送消息到指定会话
                session_name = f"{config.project_prefix}_{msg_request.session_id}"
                success = send_message_to_session(session_name, msg_request.message)

                return jsonify(
                    MessageResponse(
                        success=success,
                        message="消息发送成功" if success else "消息发送失败",
                        session_id=msg_request.session_id,
                        event_name=msg_request.hook_event_name,
                    ).model_dump()
                )

            elif msg_request.hook_event_name == "SessionEnd":
                # SessionEnd: 记录频率、检查5小时限制并处理自动消息
                tracker.record_call("SessionEnd")
                current_count = tracker.get_current_call_count()

                # 初始化响应信息
                frequency_info = (
                    f"当前窗口内调用次数: {current_count}/{tracker.config.threshold}"
                )
                limit_info = ""

                # 检查5小时限制（如果有session_id且未跳过检查）
                if msg_request.session_id and not msg_request.skip_limit_check:
                    session_name = f"{config.project_prefix}_{msg_request.session_id}"
                    limit_handler = get_limit_handler()

                    # 执行限制检测
                    limit_result = limit_handler.check_and_handle_limit(
                        session_name, msg_request.skip_limit_check
                    )

                    if limit_result.limit_detected:
                        limit_info = f"5小时限制检测: {limit_result.message}"
                        if limit_result.scheduled:
                            limit_info += " (已调度自动继续消息)"
                    else:
                        limit_info = "5小时限制检测: 未检测到限制"

                # 检查是否需要触发自动消息
                should_auto_message = tracker.should_trigger_auto_message()

                if should_auto_message:
                    # 发送自动 'hi' 消息
                    if msg_request.session_id:
                        session_name = (
                            f"{config.project_prefix}_{msg_request.session_id}"
                        )
                        auto_success = send_message_to_session(session_name, "hi")

                        if auto_success:
                            # 重置跟踪器避免循环触发
                            tracker.reset()
                            frequency_info += " (已发送自动消息并重置跟踪器)"
                        else:
                            frequency_info += " (自动消息发送失败)"
                    else:
                        frequency_info += " (无法发送自动消息：缺少session_id)"

                # 组合响应消息
                response_message = "SessionEnd 事件处理完成"
                if limit_info:
                    response_message += f"; {limit_info}"

                return jsonify(
                    MessageResponse(
                        success=True,
                        message=response_message,
                        session_id=msg_request.session_id,
                        event_name=msg_request.hook_event_name,
                        frequency_info=frequency_info,
                    ).model_dump()
                )

            else:
                # 不支持的事件类型
                return (
                    jsonify(
                        MessageResponse(
                            success=False,
                            message=f"不支持的事件类型: {msg_request.hook_event_name}",
                        ).model_dump()
                    ),
                    400,
                )

        except Exception as e:
            # 统一异常处理
            logger.error(f"/msg/send 端点处理异常: {str(e)}")
            return (
                jsonify(
                    MessageResponse(
                        success=False, message=f"服务器内部错误: {str(e)}"
                    ).model_dump()
                ),
                500,
            )

    @app.route("/msg/send-child", methods=["POST"])
    def send_child_message():
        """
        处理子会话消息发送请求

        处理子会话的 SessionEnd 事件，集成会话清理和状态更新

        Returns:
            JSON 响应，包含清理状态和更新结果
        """
        try:
            # 1. 解析请求数据
            request_data = request.get_json()
            if not request_data:
                return (
                    jsonify(
                        ChildSessionResponse(
                            success=False,
                            message="请求体不能为空",
                            task_id="",
                            cleanup_status="请求无效",
                        ).model_dump()
                    ),
                    400,
                )

            # 2. 验证请求数据
            try:
                child_request = ChildSessionRequest(**request_data)
            except Exception as e:
                return (
                    jsonify(
                        ChildSessionResponse(
                            success=False,
                            message=f"请求数据验证失败: {str(e)}",
                            task_id=request_data.get("task_id", ""),
                            cleanup_status="验证失败",
                        ).model_dump()
                    ),
                    400,
                )

            # 3. 获取频率跟踪器
            tracker = get_frequency_tracker()

            # 4. 记录子会话调用
            tracker.record_call("ChildSessionEnd")
            current_count = tracker.get_current_call_count()

            # 5. 执行子会话清理
            cleanup_status = cleanup_child_session(
                child_request.task_id, config.project_prefix
            )

            # 6. 更新子会话状态
            session_name = (
                child_request.session_name
                or f"{config.project_prefix}_child_{child_request.task_id}"
            )
            update_result = update_child_session_status(
                child_request.task_id,
                session_name,
                child_request.exit_status,
                child_request.worktree_path,
            )

            # 7. 准备频率信息
            frequency_info = (
                f"当前窗口内调用次数: {current_count}/{tracker.config.threshold}"
            )

            # 8. 检查是否需要触发自动消息
            should_auto_message = tracker.should_trigger_auto_message()
            if should_auto_message:
                # 发送自动 'hi' 消息到主会话（如果存在）
                try:
                    # 尝试从session_id.txt读取主会话ID
                    session_file = Path("session_id.txt")
                    if session_file.exists():
                        main_session_id = session_file.read_text(
                            encoding="utf-8"
                        ).strip()
                        main_session_name = f"{config.project_prefix}_{main_session_id}"
                        auto_success = send_message_to_session(main_session_name, "hi")

                        if auto_success:
                            tracker.reset()
                            frequency_info += " (已发送自动消息并重置跟踪器)"
                        else:
                            frequency_info += " (自动消息发送失败)"
                    else:
                        frequency_info += " (无法发送自动消息：未找到主会话)"
                except Exception as e:
                    frequency_info += f" (自动消息处理异常: {str(e)})"

            # 9. 返回成功响应
            return jsonify(
                ChildSessionResponse(
                    success=True,
                    message="子会话处理完成",
                    task_id=child_request.task_id,
                    cleanup_status=cleanup_status,
                    update_result=update_result,
                    frequency_info=frequency_info,
                ).model_dump()
            )

        except Exception as e:
            # 10. 统一异常处理
            logger.error(f"/msg/send-child 端点处理异常: {str(e)}")
            return (
                jsonify(
                    ChildSessionResponse(
                        success=False,
                        message=f"服务器内部错误: {str(e)}",
                        task_id=request_data.get("task_id", "") if request_data else "",
                        cleanup_status="处理异常",
                    ).model_dump()
                ),
                500,
            )

    @app.route("/scheduler/status", methods=["GET"])
    def get_scheduler_status():
        """
        获取子会话调度器状态

        Returns:
            JSON 响应，包含调度器的运行状态和统计信息
        """
        try:
            # 1. 获取调度器状态
            status = get_global_scheduler_status()

            # 2. 返回状态信息
            return jsonify(
                {"success": True, "message": "调度器状态获取成功", "data": status}
            )

        except Exception as e:
            # 3. 处理异常
            logger.error(f"/scheduler/status 端点处理异常: {str(e)}")
            return (
                jsonify({"success": False, "message": f"获取调度器状态失败: {str(e)}"}),
                500,
            )

    @app.route("/scheduler/start", methods=["POST"])
    def start_scheduler():
        """
        启动子会话调度器

        Returns:
            JSON 响应，包含启动结果
        """
        try:
            # 1. 启动调度器
            success = start_global_scheduler()

            # 2. 返回启动结果
            if success:
                return jsonify({"success": True, "message": "子会话调度器启动成功"})
            else:
                return (
                    jsonify({"success": False, "message": "子会话调度器启动失败"}),
                    500,
                )

        except Exception as e:
            # 3. 处理异常
            logger.error(f"/scheduler/start 端点处理异常: {str(e)}")
            return (
                jsonify({"success": False, "message": f"启动调度器异常: {str(e)}"}),
                500,
            )

    @app.route("/scheduler/stop", methods=["POST"])
    def stop_scheduler():
        """
        停止子会话调度器

        Returns:
            JSON 响应，包含停止结果
        """
        try:
            # 1. 停止调度器
            success = stop_global_scheduler()

            # 2. 返回停止结果
            if success:
                return jsonify({"success": True, "message": "子会话调度器停止成功"})
            else:
                return (
                    jsonify({"success": False, "message": "子会话调度器停止失败"}),
                    500,
                )

        except Exception as e:
            # 3. 处理异常
            logger.error(f"/scheduler/stop 端点处理异常: {str(e)}")
            return (
                jsonify({"success": False, "message": f"停止调度器异常: {str(e)}"}),
                500,
            )

    # 8. 启动子会话调度器
    try:
        scheduler_started = start_global_scheduler()
        if scheduler_started:
            logger.info("子会话调度器自动启动成功")
        else:
            logger.warning("子会话调度器自动启动失败")
    except Exception as e:
        logger.error(f"自动启动调度器异常: {e}")

    # 9. 记录应用创建信息
    logger.info(f"Flask 应用创建成功: {config.host}:{config.port}")

    # 10. 返回应用实例
    return app


def validate_flask_config(config: FlaskConfigModel) -> bool:
    """
    验证 Flask 配置完整性

    检查配置参数的有效性和系统兼容性

    Args:
        config: Flask 配置实例

    Returns:
        bool: 配置是否有效

    Raises:
        ValueError: 配置验证失败时抛出
    """
    # 1. 验证端口范围
    if config.port < 1024 or config.port > 65535:
        raise ValueError(f"端口 {config.port} 超出有效范围 (1024-65535)")

    # 2. 验证项目前缀
    if not config.project_prefix or len(config.project_prefix.strip()) == 0:
        raise ValueError("项目前缀不能为空")

    # 3. 验证主机地址格式
    if not config.host or config.host.strip() == "":
        raise ValueError("主机地址不能为空")

    # 4. 记录验证结果
    logger.info(
        f"Flask 配置验证通过: {config.project_prefix}@{config.host}:{config.port}"
    )

    # 5. 返回验证结果
    return True


def run_flask_server(
    host: Optional[str] = None, port: Optional[int] = None, debug: bool = False
) -> None:
    """
    启动 Flask 服务器

    启动 Flask Web 服务器，处理 hooks 事件和消息发送

    Args:
        host: 监听主机地址，如果为 None 则使用配置中的地址
        port: 监听端口号，如果为 None 则使用配置中的端口
        debug: 是否启用调试模式
    """
    # 1. 创建 Flask 配置
    config = create_flask_config()

    # 2. 覆盖配置参数
    if host is not None:
        config.host = host
    if port is not None:
        config.port = port
    config.debug = debug

    # 3. 验证配置
    validate_flask_config(config)

    # 4. 创建应用实例
    app = create_app(config)

    # 5. 启动服务器
    try:
        logger.info(f"Flask 服务器启动: http://{config.host}:{config.port}")
        app.run(host=config.host, port=config.port, debug=config.debug)
    except Exception as e:
        # 6. 异常处理
        logger.error(f"Flask 服务器启动失败: {e}")
        raise


if __name__ == "__main__":
    run_flask_server()
