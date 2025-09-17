# -*- coding: utf-8 -*-
"""
Flask Web 服务器实现

@description 实现 Master 会话的 Flask Web 服务，处理 hooks 事件和消息发送
"""

import logging
import socket
from typing import Optional
from flask import Flask, request, jsonify
from flask_cors import CORS
from pydantic import BaseModel, Field, field_validator, ConfigDict

from .._internal.config_tools import get_environment_config, EnvConfig

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
        json_encoders={},
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
    app.config['DEBUG'] = config.debug
    app.config['HOST'] = config.host
    app.config['PORT'] = config.port
    app.config['PROJECT_PREFIX'] = config.project_prefix

    # 4. 配置 JSON 序列化
    app.config['JSON_SORT_KEYS'] = False
    app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True

    # 5. 启用 CORS 跨域支持
    if config.cors_enabled:
        CORS(app, origins="*", methods=["GET", "POST", "OPTIONS"])
        logger.info("CORS 跨域支持已启用")

    # 6. 配置日志级别
    if config.debug:
        app.logger.setLevel(logging.DEBUG)
    else:
        app.logger.setLevel(logging.INFO)

    # 7. 记录应用创建信息
    logger.info(f"Flask 应用创建成功: {config.host}:{config.port}")

    # 8. 返回应用实例
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
    logger.info(f"Flask 配置验证通过: {config.project_prefix}@{config.host}:{config.port}")

    # 5. 返回验证结果
    return True


def run_flask_server(
    host: Optional[str] = None,
    port: Optional[int] = None,
    debug: bool = False
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