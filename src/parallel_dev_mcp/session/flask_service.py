# -*- coding: utf-8 -*-
"""
Flask Web 服务管理器

@description 在Master会话中管理Flask服务的生命周期，提供后台服务启动和优雅关闭
"""

import logging
import threading
import time
import socket
from typing import Optional, Dict, Any
from werkzeug.serving import make_server, BaseWSGIServer
from flask import Flask, jsonify
from pydantic import BaseModel, Field

from .session_manager import SessionIDManager, MasterSessionDetector
from .._internal.config_tools import get_environment_config

# 配置日志系统
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class FlaskServiceConfig(BaseModel):
    """
    Flask 服务配置数据模型

    包含服务端口、主机地址等配置信息
    """

    host: str = Field("127.0.0.1", description="绑定主机地址")
    port: int = Field(5001, description="服务端口", ge=1024, le=65535)
    debug: bool = Field(False, description="调试模式")
    threaded: bool = Field(True, description="多线程模式")
    use_reloader: bool = Field(False, description="自动重载")
    use_debugger: bool = Field(False, description="调试器")

    class Config:
        """模型配置"""

        # 1. JSON编码器
        # json_encoders deprecated in V2


class FlaskServiceManager:
    """
    Flask 服务管理器

    在Master会话中启动和管理Flask Web服务
    """

    def __init__(self) -> None:
        """
        初始化Flask服务管理器
        """
        # 1. 初始化基础属性
        self.app: Optional[Flask] = None
        self.server: Optional[BaseWSGIServer] = None
        self.server_thread: Optional[threading.Thread] = None
        self.config: Optional[FlaskServiceConfig] = None

        # 2. 初始化会话管理器
        self.session_manager = SessionIDManager()
        self.detector = MasterSessionDetector()

        # 3. 服务状态标志
        self.is_running = False
        self.shutdown_event = threading.Event()

        # 4. 记录初始化信息
        logger.info("Flask服务管理器初始化完成")

    def _load_config(self) -> FlaskServiceConfig:
        """
        加载Flask服务配置

        Returns:
            FlaskServiceConfig: 配置实例
        """
        try:
            # 1. 获取环境配置
            env_config = get_environment_config()

            # 2. 从环境变量读取WEB_PORT
            web_port = getattr(env_config, "web_port", 5001)

            # 3. 创建Flask服务配置
            config = FlaskServiceConfig(
                host="127.0.0.1",
                port=web_port,
                debug=False,
                threaded=True,
                use_reloader=False,
                use_debugger=False,
            )

            # 4. 记录配置信息
            logger.info(f"Flask服务配置加载成功: {config.host}:{config.port}")

            # 5. 返回配置
            return config

        except Exception as e:
            # 6. 处理配置加载失败
            logger.warning(f"环境配置加载失败，使用默认配置: {e}")
            return FlaskServiceConfig()

    def _check_port_available(self, host: str, port: int) -> bool:
        """
        检查端口是否可用

        Args:
            host: 主机地址
            port: 端口号

        Returns:
            bool: 端口是否可用
        """
        try:
            # 1. 创建套接字
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)

                # 2. 尝试连接端口
                result = sock.connect_ex((host, port))

                # 3. 检查连接结果
                if result == 0:
                    logger.warning(f"端口 {host}:{port} 已被占用")
                    return False
                else:
                    logger.debug(f"端口 {host}:{port} 可用")
                    return True

        except Exception as e:
            # 4. 处理检查异常
            logger.warning(f"端口可用性检查失败: {e}")
            return True

    def _create_flask_app(self) -> Flask:
        """
        创建Flask应用实例

        Returns:
            Flask: Flask应用实例
        """
        # 1. 创建Flask应用
        app = Flask(__name__)

        # 2. 配置应用设置
        app.config["DEBUG"] = self.config.debug
        app.config["TESTING"] = False
        app.config["SECRET_KEY"] = "master_session_flask_service"

        # 3. 注册健康检查端点
        @app.route("/health", methods=["GET"])
        def health_check():
            """健康检查端点"""
            return self._handle_health_check()

        # 4. 注册服务状态端点
        @app.route("/status", methods=["GET"])
        def service_status():
            """服务状态端点"""
            return self._handle_service_status()

        # 5. 记录应用创建信息
        logger.info("Flask应用实例创建成功")

        # 6. 返回应用实例
        return app

    def _handle_health_check(self) -> Dict[str, Any]:
        """
        处理健康检查请求

        Returns:
            Dict[str, Any]: 健康检查响应
        """
        # 1. 获取session_id
        session_id = self.session_manager.read_session_id()

        # 2. 获取会话信息
        session_info = self.session_manager.get_session_info()

        # 3. 构建响应数据
        health_data = {
            "status": "healthy",
            "service": "parallel-dev-mcp-master",
            "session_id": session_id,
            "session_type": session_info.session_type if session_info else "unknown",
            "is_master": self.detector.is_master_session(),
            "uptime_seconds": int(time.time()) if self.is_running else 0,
        }

        # 4. 记录健康检查
        logger.debug("健康检查请求处理完成")

        # 5. 返回响应
        return jsonify(health_data)

    def _handle_service_status(self) -> Dict[str, Any]:
        """
        处理服务状态请求

        Returns:
            Dict[str, Any]: 服务状态响应
        """
        # 1. 构建状态数据
        status_data = {
            "service_running": self.is_running,
            "config": {
                "host": self.config.host if self.config else "unknown",
                "port": self.config.port if self.config else 0,
                "debug": self.config.debug if self.config else False,
            },
            "thread_active": (
                self.server_thread.is_alive() if self.server_thread else False
            ),
            "shutdown_requested": self.shutdown_event.is_set(),
        }

        # 2. 记录状态查询
        logger.debug("服务状态查询处理完成")

        # 3. 返回响应
        return jsonify(status_data)

    def _run_server(self) -> None:
        """
        在后台线程中运行Flask服务器
        """
        try:
            # 1. 记录服务器启动
            logger.info(f"Flask服务器线程启动: {self.config.host}:{self.config.port}")

            # 2. 设置运行标志
            self.is_running = True

            # 3. 启动服务器
            self.server.serve_forever()

        except Exception as e:
            # 4. 处理服务器异常
            logger.error(f"Flask服务器运行异常: {e}")
            self.is_running = False

        finally:
            # 5. 清理资源
            logger.info("Flask服务器线程结束")
            self.is_running = False

    def start_service(self) -> bool:
        """
        启动Flask服务

        Returns:
            bool: 启动是否成功
        """
        try:
            # 1. 检查是否已经运行
            if self.is_running:
                logger.warning("Flask服务已在运行")
                return True

            # 2. 加载配置
            self.config = self._load_config()

            # 3. 检查端口可用性
            if not self._check_port_available(self.config.host, self.config.port):
                logger.error(f"端口 {self.config.port} 不可用，服务启动失败")
                return False

            # 4. 创建Flask应用
            self.app = self._create_flask_app()

            # 5. 创建WSGI服务器
            self.server = make_server(
                host=self.config.host,
                port=self.config.port,
                app=self.app,
                threaded=self.config.threaded,
            )

            # 6. 创建并启动服务器线程
            self.server_thread = threading.Thread(
                target=self._run_server, name="FlaskServerThread", daemon=True
            )
            self.server_thread.start()

            # 7. 等待服务器启动
            time.sleep(0.5)

            # 8. 验证服务器启动成功
            if self.is_running and self.server_thread.is_alive():
                logger.info(
                    f"Flask服务启动成功: http://{self.config.host}:{self.config.port}"
                )
                return True
            else:
                logger.error("Flask服务启动失败")
                return False

        except Exception as e:
            # 9. 处理启动失败
            logger.error(f"Flask服务启动异常: {e}")
            self.is_running = False
            return False

    def stop_service(self, timeout: int = 5) -> bool:
        """
        停止Flask服务

        Args:
            timeout: 停止超时时间（秒）

        Returns:
            bool: 停止是否成功
        """
        try:
            # 1. 检查服务状态
            if not self.is_running:
                logger.info("Flask服务未运行")
                return True

            # 2. 设置关闭事件
            self.shutdown_event.set()
            logger.info("开始停止Flask服务...")

            # 3. 停止服务器
            if self.server:
                self.server.shutdown()

            # 4. 等待线程结束
            if self.server_thread and self.server_thread.is_alive():
                self.server_thread.join(timeout=timeout)

            # 5. 检查线程是否成功结束
            if self.server_thread and self.server_thread.is_alive():
                logger.warning(f"Flask服务线程未在 {timeout} 秒内结束")
                return False

            # 6. 清理资源
            self.is_running = False
            self.server = None
            self.server_thread = None
            self.shutdown_event.clear()

            # 7. 记录停止成功
            logger.info("Flask服务停止成功")
            return True

        except Exception as e:
            # 8. 处理停止异常
            logger.error(f"Flask服务停止异常: {e}")
            return False

    def is_service_running(self) -> bool:
        """
        检查服务是否在运行

        Returns:
            bool: 服务是否在运行
        """
        return self.is_running and (
            self.server_thread is not None and self.server_thread.is_alive()
        )

    def get_service_url(self) -> Optional[str]:
        """
        获取服务URL

        Returns:
            Optional[str]: 服务URL，服务未运行时返回None
        """
        if self.is_service_running() and self.config:
            return f"http://{self.config.host}:{self.config.port}"
        return None


def create_flask_service_manager() -> FlaskServiceManager:
    """
    创建Flask服务管理器实例

    Returns:
        FlaskServiceManager: 配置好的Flask服务管理器实例
    """
    # 1. 创建管理器实例
    manager = FlaskServiceManager()

    # 2. 记录创建信息
    logger.info("Flask服务管理器实例创建成功")

    # 3. 返回管理器实例
    return manager
