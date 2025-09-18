# -*- coding: utf-8 -*-
"""
Web服务生命周期管理器

@description 管理Master节点Web服务的自动启动和生命周期
"""

import os
import logging
import threading
import time
from typing import Dict, Any, Optional
from datetime import datetime

# 导入Master节点检测器
from ..session.master_detector import (
    is_master_node,
    validate_master_environment,
    get_master_session_info
)

# 配置日志系统
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 全局Web服务生命周期管理器实例
_lifecycle_manager = None
_lifecycle_lock = threading.Lock()


class WebServiceLifecycleManager:
    """
    Web服务生命周期管理器

    负责Master节点Web服务的自动启动、监控和停止
    """

    def __init__(self):
        """
        初始化生命周期管理器
        """
        # 1. 初始化状态
        self.is_running = False
        self.web_server_active = False
        self.monitor_thread = None
        self.last_check_time = None

        # 2. 配置参数
        self.check_interval = 5  # 每5秒检查一次
        self.auto_start_enabled = True

        # 3. 记录初始化
        logger.info("Web服务生命周期管理器初始化完成")

    def start_lifecycle_monitoring(self) -> Dict[str, Any]:
        """
        启动生命周期监控

        Returns:
            Dict[str, Any]: 启动结果
        """
        try:
            # 1. 检查是否已经启动
            if self.is_running:
                return {
                    "success": True,
                    "message": "生命周期监控已在运行",
                    "status": "already_running"
                }

            # 2. 验证Master环境
            validation = validate_master_environment()
            if not validation["is_master"]:
                return {
                    "success": False,
                    "message": "非Master节点，无法启动Web服务监控",
                    "issues": validation["issues"]
                }

            # 3. 启动监控线程
            self.monitor_thread = threading.Thread(
                target=self._monitoring_loop,
                daemon=True,
                name="WebServiceLifecycleMonitor"
            )

            self.is_running = True
            self.monitor_thread.start()

            # 4. 记录启动成功
            logger.info("Web服务生命周期监控启动成功")
            return {
                "success": True,
                "message": "生命周期监控启动成功",
                "status": "started",
                "check_interval": self.check_interval
            }

        except Exception as e:
            # 5. 异常处理
            logger.error(f"启动生命周期监控异常: {e}")
            return {
                "success": False,
                "error": f"启动失败: {str(e)}"
            }

    def stop_lifecycle_monitoring(self) -> Dict[str, Any]:
        """
        停止生命周期监控

        Returns:
            Dict[str, Any]: 停止结果
        """
        try:
            # 1. 检查运行状态
            if not self.is_running:
                return {
                    "success": True,
                    "message": "生命周期监控未在运行",
                    "status": "not_running"
                }

            # 2. 停止监控
            self.is_running = False

            # 3. 等待线程结束
            if self.monitor_thread and self.monitor_thread.is_alive():
                self.monitor_thread.join(timeout=10)

            # 4. 停止Web服务
            if self.web_server_active:
                self._stop_web_service()

            # 5. 记录停止
            logger.info("Web服务生命周期监控已停止")
            return {
                "success": True,
                "message": "生命周期监控停止成功",
                "status": "stopped"
            }

        except Exception as e:
            # 6. 异常处理
            logger.error(f"停止生命周期监控异常: {e}")
            return {
                "success": False,
                "error": f"停止失败: {str(e)}"
            }

    def get_lifecycle_status(self) -> Dict[str, Any]:
        """
        获取生命周期状态

        Returns:
            Dict[str, Any]: 当前状态
        """
        try:
            # 1. 收集基础状态
            status = {
                "monitoring_active": self.is_running,
                "web_server_active": self.web_server_active,
                "last_check": self.last_check_time.isoformat() if self.last_check_time else None,
                "check_interval": self.check_interval,
                "auto_start_enabled": self.auto_start_enabled
            }

            # 2. 添加Master节点信息
            master_info = get_master_session_info()
            status["master_info"] = master_info

            # 3. 添加环境验证
            validation = validate_master_environment()
            status["environment_validation"] = validation

            # 4. 返回完整状态
            return {
                "success": True,
                "status": status,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            # 5. 异常处理
            logger.error(f"获取生命周期状态异常: {e}")
            return {
                "success": False,
                "error": f"状态查询失败: {str(e)}"
            }

    def _monitoring_loop(self) -> None:
        """
        监控循环主逻辑

        每5秒检查Master状态并自动管理Web服务
        """
        logger.info("Web服务监控循环启动")

        while self.is_running:
            try:
                # 1. 更新检查时间
                self.last_check_time = datetime.now()

                # 2. 检查Master状态
                if is_master_node():
                    # Master节点，确保Web服务运行
                    if not self.web_server_active and self.auto_start_enabled:
                        self._start_web_service()
                else:
                    # 非Master节点，确保Web服务停止
                    if self.web_server_active:
                        self._stop_web_service()

                # 3. 等待下次检查
                time.sleep(self.check_interval)

            except Exception as e:
                # 4. 异常处理
                logger.error(f"监控循环异常: {e}")
                time.sleep(self.check_interval)

        # 5. 循环结束
        logger.info("Web服务监控循环结束")

    def _start_web_service(self) -> bool:
        """
        启动Web服务

        Returns:
            bool: 启动是否成功
        """
        try:
            # 1. 验证环境
            validation = validate_master_environment()
            if validation["issues"]:
                logger.warning(f"Master环境验证失败，无法启动Web服务: {validation['issues']}")
                return False

            # 2. 导入Web服务管理
            from .web_tools import _start_flask_server

            # 3. 获取配置
            web_port = int(os.getenv('WEB_PORT', 8765))
            project_prefix = os.getenv('PROJECT_PREFIX', '')

            # 4. 启动Flask服务
            result = _start_flask_server(web_port, project_prefix)

            if result.get("success"):
                self.web_server_active = True
                logger.info(f"Web服务自动启动成功: 端口 {web_port}")
                return True
            else:
                logger.error(f"Web服务启动失败: {result.get('error')}")
                return False

        except Exception as e:
            # 5. 异常处理
            logger.error(f"启动Web服务异常: {e}")
            return False

    def _stop_web_service(self) -> bool:
        """
        停止Web服务

        Returns:
            bool: 停止是否成功
        """
        try:
            # 1. 导入Web服务管理
            from .web_tools import _stop_flask_server

            # 2. 停止Flask服务
            result = _stop_flask_server()

            if result.get("success"):
                self.web_server_active = False
                logger.info("Web服务自动停止成功")
                return True
            else:
                logger.error(f"Web服务停止失败: {result.get('error')}")
                return False

        except Exception as e:
            # 3. 异常处理
            logger.error(f"停止Web服务异常: {e}")
            return False

    def force_web_service_restart(self) -> Dict[str, Any]:
        """
        强制重启Web服务

        Returns:
            Dict[str, Any]: 重启结果
        """
        try:
            # 1. 停止现有服务
            if self.web_server_active:
                stop_success = self._stop_web_service()
                if not stop_success:
                    logger.warning("强制重启：停止现有服务失败")

            # 2. 等待短暂时间
            time.sleep(2)

            # 3. 启动新服务
            if is_master_node():
                start_success = self._start_web_service()
                if start_success:
                    return {
                        "success": True,
                        "message": "Web服务强制重启成功",
                        "web_server_active": self.web_server_active
                    }
                else:
                    return {
                        "success": False,
                        "message": "Web服务重启失败：启动阶段失败"
                    }
            else:
                return {
                    "success": False,
                    "message": "当前不是Master节点，无法启动Web服务"
                }

        except Exception as e:
            # 4. 异常处理
            logger.error(f"强制重启Web服务异常: {e}")
            return {
                "success": False,
                "error": f"重启失败: {str(e)}"
            }


def get_lifecycle_manager() -> WebServiceLifecycleManager:
    """
    获取全局生命周期管理器实例

    Returns:
        WebServiceLifecycleManager: 生命周期管理器实例
    """
    global _lifecycle_manager

    with _lifecycle_lock:
        if _lifecycle_manager is None:
            _lifecycle_manager = WebServiceLifecycleManager()
            logger.info("创建全局Web服务生命周期管理器实例")
        return _lifecycle_manager


def initialize_web_lifecycle() -> Dict[str, Any]:
    """
    初始化Web服务生命周期管理

    如果是Master节点，自动启动监控

    Returns:
        Dict[str, Any]: 初始化结果
    """
    try:
        # 1. 获取管理器实例
        manager = get_lifecycle_manager()

        # 2. 检查是否为Master节点
        if is_master_node():
            # Master节点，启动监控
            result = manager.start_lifecycle_monitoring()
            logger.info("Master节点检测到，已启动Web服务生命周期监控")
            return result
        else:
            # 非Master节点，仅初始化不启动
            logger.info("非Master节点，Web服务生命周期管理器已初始化但未启动监控")
            return {
                "success": True,
                "message": "非Master节点，生命周期管理器已初始化",
                "monitoring_started": False
            }

    except Exception as e:
        # 3. 异常处理
        logger.error(f"初始化Web服务生命周期管理异常: {e}")
        return {
            "success": False,
            "error": f"初始化失败: {str(e)}"
        }