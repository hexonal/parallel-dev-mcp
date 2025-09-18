# -*- coding: utf-8 -*-
"""
Web服务MCP工具

@description 提供Flask Web服务器管理的FastMCP工具接口
"""

import logging
import os
import threading
import time
from typing import Dict, Any, Optional
from datetime import datetime

# 获取FastMCP实例
from ..mcp_instance import mcp

# 导入Master节点检测和生命周期管理
from ..session.master_detector import (
    is_master_node,
    validate_master_environment,
    get_master_session_info
)
from .lifecycle_manager import get_lifecycle_manager

# 配置日志系统
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 全局Flask应用实例
_flask_app = None
_flask_thread = None
_server_running = False


def _flask_web_server_internal(
    action: str,
    port: Optional[int] = None,
    project_prefix: Optional[str] = None
) -> Dict[str, Any]:
    """
    Flask Web服务器管理内部函数

    内部使用，不暴露为MCP工具。MCP核心自动流转能力。
    实现PRD要求的Flask HTTP服务，处理Master/Child会话通信。
    支持启动、停止和查询Flask服务器状态。

    Args:
        action: 操作类型 (start/stop/status)
        port: 服务端口（可选，默认从WEB_PORT环境变量读取）
        project_prefix: 项目前缀（可选，默认从PROJECT_PREFIX环境变量读取）

    Returns:
        Dict[str, Any]: 操作结果
    """
    global _flask_app, _flask_thread, _server_running

    try:
        # 1. 参数验证
        if action not in ['start', 'stop', 'status']:
            return {
                "success": False,
                "error": "无效的操作类型，必须是: start, stop, status"
            }

        # 2. Master节点验证（仅对start操作）
        if action == 'start':
            validation = validate_master_environment()
            if not validation["is_master"]:
                return {
                    "success": False,
                    "error": "仅Master节点可以启动Web服务",
                    "issues": validation["issues"],
                    "current_node_type": "non-master"
                }

        # 3. 获取配置参数
        web_port = port or int(os.getenv('WEB_PORT', 8765))
        proj_prefix = project_prefix or os.getenv('PROJECT_PREFIX', '')

        # 4. 环境变量验证
        missing_vars = []
        if not proj_prefix:
            missing_vars.append("PROJECT_PREFIX")
        if not os.getenv('WEB_PORT') and port is None:
            missing_vars.append("WEB_PORT")

        if missing_vars:
            return {
                "success": False,
                "error": f"缺少必需的环境变量: {', '.join(missing_vars)}",
                "missing_variables": missing_vars
            }

        # 5. 执行对应操作
        if action == 'start':
            return _start_flask_server(web_port, proj_prefix)
        elif action == 'stop':
            return _stop_flask_server()
        elif action == 'status':
            return _get_flask_status(web_port, proj_prefix)

    except Exception as e:
        # 4. 异常处理
        logger.error(f"Flask Web服务器工具异常: {e}")
        return {
            "success": False,
            "error": f"操作失败: {str(e)}"
        }


def _start_flask_server(port: int, project_prefix: str) -> Dict[str, Any]:
    """
    启动Flask服务器

    Args:
        port: 服务端口
        project_prefix: 项目前缀

    Returns:
        Dict[str, Any]: 启动结果
    """
    global _flask_app, _flask_thread, _server_running

    try:
        # 1. 检查是否已经启动
        if _server_running:
            return {
                "success": True,
                "message": "Flask服务器已经在运行",
                "port": port,
                "project_prefix": project_prefix,
                "status": "already_running"
            }

        # 2. 设置环境变量
        os.environ['WEB_PORT'] = str(port)
        os.environ['PROJECT_PREFIX'] = project_prefix

        # 3. 导入并创建Flask应用
        from .flask_server import create_app, create_flask_config

        config = create_flask_config()
        config.port = port
        config.project_prefix = project_prefix

        _flask_app = create_app(config)

        # 4. 启动服务器线程
        def run_server():
            global _server_running
            try:
                _server_running = True
                logger.info(f"Flask服务器启动线程开始: {config.host}:{config.port}")
                _flask_app.run(
                    host=config.host,
                    port=config.port,
                    debug=config.debug,
                    use_reloader=False,
                    threaded=True
                )
            except Exception as e:
                logger.error(f"Flask服务器运行异常: {e}")
            finally:
                _server_running = False
                logger.info("Flask服务器线程结束")

        _flask_thread = threading.Thread(target=run_server, daemon=True)
        _flask_thread.start()

        # 5. 等待服务器启动
        time.sleep(2)

        # 6. 验证启动状态
        if _server_running:
            logger.info(f"Flask服务器启动成功: 端口 {port}")
            return {
                "success": True,
                "message": "Flask服务器启动成功",
                "port": port,
                "project_prefix": project_prefix,
                "status": "running",
                "endpoints": [
                    f"http://127.0.0.1:{port}/msg/send",
                    f"http://127.0.0.1:{port}/msg/send-child",
                    f"http://127.0.0.1:{port}/health"
                ]
            }
        else:
            return {
                "success": False,
                "message": "Flask服务器启动失败",
                "port": port
            }

    except Exception as e:
        # 7. 异常处理
        logger.error(f"启动Flask服务器异常: {e}")
        return {
            "success": False,
            "error": f"启动失败: {str(e)}"
        }


def _stop_flask_server() -> Dict[str, Any]:
    """
    停止Flask服务器

    Returns:
        Dict[str, Any]: 停止结果
    """
    global _flask_app, _flask_thread, _server_running

    try:
        # 1. 检查服务器状态
        if not _server_running:
            return {
                "success": True,
                "message": "Flask服务器未在运行",
                "status": "not_running"
            }

        # 2. 停止服务器
        _server_running = False

        # 3. 等待线程结束
        if _flask_thread and _flask_thread.is_alive():
            _flask_thread.join(timeout=5)

        # 4. 清理资源
        _flask_app = None
        _flask_thread = None

        # 5. 记录停止
        logger.info("Flask服务器已停止")
        return {
            "success": True,
            "message": "Flask服务器停止成功",
            "status": "stopped"
        }

    except Exception as e:
        # 6. 异常处理
        logger.error(f"停止Flask服务器异常: {e}")
        return {
            "success": False,
            "error": f"停止失败: {str(e)}"
        }


def _get_flask_status(port: int, project_prefix: str) -> Dict[str, Any]:
    """
    获取Flask服务器状态

    Args:
        port: 服务端口
        project_prefix: 项目前缀

    Returns:
        Dict[str, Any]: 状态信息
    """
    global _flask_app, _flask_thread, _server_running

    try:
        # 1. 检查运行状态
        is_running = _server_running and _flask_thread and _flask_thread.is_alive()

        # 2. 构造状态信息
        status_info = {
            "success": True,
            "running": is_running,
            "port": port,
            "project_prefix": project_prefix,
            "thread_alive": _flask_thread.is_alive() if _flask_thread else False,
            "timestamp": datetime.now().isoformat()
        }

        # 3. 添加端点信息
        if is_running:
            status_info["endpoints"] = [
                f"http://127.0.0.1:{port}/msg/send",
                f"http://127.0.0.1:{port}/msg/send-child",
                f"http://127.0.0.1:{port}/health"
            ]

        return status_info

    except Exception as e:
        # 4. 异常处理
        logger.error(f"获取Flask状态异常: {e}")
        return {
            "success": False,
            "error": f"状态查询失败: {str(e)}"
        }


def _rate_limit_manager_internal(
    action: str,
    reset: bool = False
) -> Dict[str, Any]:
    """
    限流管理内部函数

    管理Flask服务器的限流状态和频率跟踪 (内部能力，不暴露为MCP工具)。

    Args:
        action: 操作类型 (status/reset)
        reset: 是否重置限流计数器

    Returns:
        Dict[str, Any]: 操作结果
    """
    try:
        # 1. 参数验证
        if action not in ['status', 'reset']:
            return {
                "success": False,
                "error": "无效的操作类型，必须是: status, reset"
            }

        # 2. 导入限流组件
        from .flask_server import get_frequency_tracker, get_limit_handler

        # 3. 获取限流实例
        tracker = get_frequency_tracker()
        limit_handler = get_limit_handler()

        # 4. 执行对应操作
        if action == 'status':
            # 获取限流状态
            current_count = tracker.get_current_call_count()
            threshold = tracker.config.threshold

            return {
                "success": True,
                "current_count": current_count,
                "threshold": threshold,
                "window_seconds": tracker.config.window_seconds,
                "should_auto_message": tracker.should_trigger_auto_message(),
                "last_call_time": tracker.get_last_call_time().isoformat() if tracker.get_last_call_time() else None
            }

        elif action == 'reset':
            # 重置限流计数器
            if reset:
                tracker.reset()
                logger.info("限流计数器已重置")

            return {
                "success": True,
                "message": "限流计数器重置成功" if reset else "重置参数为False，未执行重置",
                "current_count": tracker.get_current_call_count()
            }

    except Exception as e:
        # 5. 异常处理
        logger.error(f"限流管理工具异常: {e}")
        return {
            "success": False,
            "error": f"操作失败: {str(e)}"
        }


def _scheduled_message_internal(
    action: str,
    session_name: Optional[str] = None,
    message: str = "hi",
    delay_seconds: int = 0
) -> Dict[str, Any]:
    """
    定时消息内部函数

    内部使用，不暴露为MCP工具。MCP核心自动流转能力。
    实现定时发送消息功能，支持5小时限流恢复和自动消息发送。

    Args:
        action: 操作类型 (send/schedule)
        session_name: 目标会话名称
        message: 要发送的消息
        delay_seconds: 延时秒数

    Returns:
        Dict[str, Any]: 操作结果
    """
    try:
        # 1. 参数验证
        if action not in ['send', 'schedule']:
            return {
                "success": False,
                "error": "无效的操作类型，必须是: send, schedule"
            }

        # 2. 执行对应操作
        if action == 'send':
            # 立即发送消息
            if not session_name:
                return {
                    "success": False,
                    "error": "发送消息需要指定session_name"
                }

            from .flask_server import send_message_to_session
            success = send_message_to_session(session_name, message)

            return {
                "success": success,
                "message": f"消息{'发送成功' if success else '发送失败'}",
                "session_name": session_name,
                "sent_message": message
            }

        elif action == 'schedule':
            # 定时发送消息
            if not session_name:
                return {
                    "success": False,
                    "error": "定时消息需要指定session_name"
                }

            def delayed_send():
                time.sleep(delay_seconds)
                from .flask_server import send_message_to_session
                success = send_message_to_session(session_name, message)
                logger.info(f"定时消息发送{'成功' if success else '失败'}: {session_name} <- {message}")

            # 启动定时发送线程
            schedule_thread = threading.Thread(target=delayed_send, daemon=True)
            schedule_thread.start()

            return {
                "success": True,
                "message": f"定时消息已安排，将在{delay_seconds}秒后发送",
                "session_name": session_name,
                "scheduled_message": message,
                "delay_seconds": delay_seconds
            }

    except Exception as e:
        # 3. 异常处理
        logger.error(f"定时消息工具异常: {e}")
        return {
            "success": False,
            "error": f"操作失败: {str(e)}"
        }


def _internal_lifecycle_management(action: str) -> Dict[str, Any]:
    """
    内部Web服务生命周期管理

    内部函数，不暴露为MCP工具。用于系统内部自动管理Web服务生命周期。

    Args:
        action: 操作类型 (start_monitoring/stop_monitoring/status/restart)

    Returns:
        Dict[str, Any]: 操作结果
    """
    try:
        # 1. 参数验证
        if action not in ['start_monitoring', 'stop_monitoring', 'status', 'restart']:
            return {
                "success": False,
                "error": "无效的操作类型，必须是: start_monitoring, stop_monitoring, status, restart"
            }

        # 2. 获取生命周期管理器
        manager = get_lifecycle_manager()

        # 3. 执行对应操作
        if action == 'start_monitoring':
            return manager.start_lifecycle_monitoring()
        elif action == 'stop_monitoring':
            return manager.stop_lifecycle_monitoring()
        elif action == 'status':
            return manager.get_lifecycle_status()
        elif action == 'restart':
            return manager.force_web_service_restart()

    except Exception as e:
        # 4. 异常处理
        logger.error(f"内部生命周期管理异常: {e}")
        return {
            "success": False,
            "error": f"操作失败: {str(e)}"
        }


def _internal_master_detection() -> Dict[str, Any]:
    """
    内部Master节点检测

    内部函数，不暴露为MCP工具。用于系统内部自动检测Master节点状态。

    Returns:
        Dict[str, Any]: 检测结果
    """
    try:
        # 1. 执行Master节点检测
        master_info = get_master_session_info()

        # 2. 执行环境验证
        validation = validate_master_environment()

        # 3. 返回完整检测结果
        return {
            "success": True,
            "is_master_node": master_info.get("is_master", False),
            "master_session_info": master_info,
            "environment_validation": validation,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        # 4. 异常处理
        logger.error(f"内部Master节点检测异常: {e}")
        return {
            "success": False,
            "error": f"检测失败: {str(e)}"
        }