# -*- coding: utf-8 -*-
"""
限流管理器 (内部能力)

@description 为会话系统提供内部限流检测和定时任务能力，不对外暴露MCP工具
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

# 导入限流检测器
from .rate_limit_detector import RateLimitDetector, SessionType

# 导入主会话存储
from .master_session_resource import get_master_storage

# 导入结构化日志
from .structured_logger import log_info, log_warning, log_error, LogCategory

# 配置日志系统
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class RateLimitManager:
    """
    限流管理器 (内部单例)

    为会话系统提供限流检测和定时任务管理的内部能力
    """

    _instance: Optional['RateLimitManager'] = None
    _detector_registry: Dict[str, RateLimitDetector] = {}

    def __new__(cls) -> 'RateLimitManager':
        """单例模式实现"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """初始化限流管理器"""
        if not hasattr(self, '_initialized'):
            # 1. 标记初始化
            self._initialized = True

            # 2. 记录初始化
            log_info(
                LogCategory.SYSTEM,
                "限流管理器初始化完成 (内部能力)"
            )

    def enable_rate_limiting_for_session(self, session_id: str, session_type: str) -> bool:
        """
        为会话启用限流检测 (内部方法)

        Args:
            session_id: 会话标识
            session_type: 会话类型 (master/child)

        Returns:
            bool: 是否启用成功
        """
        try:
            # 1. 参数验证
            if session_type not in ['master', 'child']:
                log_error(LogCategory.SYSTEM, f"无效的会话类型: {session_type}")
                return False

            if session_id in self._detector_registry:
                log_warning(LogCategory.SYSTEM, f"会话 {session_id} 限流检测已启用")
                return True

            # 2. 创建检测器
            detector = RateLimitDetector(
                session_type=SessionType(session_type),
                session_id=session_id
            )

            # 3. 启动检测
            result = detector.start_detection()

            if result.get("success"):
                # 4. 注册检测器
                self._detector_registry[session_id] = detector

                log_info(
                    LogCategory.SESSION,
                    f"为会话启用限流检测 - {session_id} ({session_type})"
                )
                return True
            else:
                log_error(LogCategory.SYSTEM, f"启动限流检测失败: {result.get('error')}")
                return False

        except Exception as e:
            log_error(LogCategory.SYSTEM, f"启用限流检测异常: {str(e)}")
            return False

    def disable_rate_limiting_for_session(self, session_id: str) -> bool:
        """
        为会话禁用限流检测 (内部方法)

        Args:
            session_id: 会话标识

        Returns:
            bool: 是否禁用成功
        """
        try:
            # 1. 检查检测器是否存在
            if session_id not in self._detector_registry:
                log_warning(LogCategory.SYSTEM, f"会话 {session_id} 没有启用限流检测")
                return True

            # 2. 停止检测
            detector = self._detector_registry[session_id]
            result = detector.stop_detection()

            # 3. 从注册表移除
            if result.get("success"):
                del self._detector_registry[session_id]

                log_info(
                    LogCategory.SESSION,
                    f"为会话禁用限流检测 - {session_id}"
                )
                return True
            else:
                log_error(LogCategory.SYSTEM, f"停止限流检测失败: {result.get('error')}")
                return False

        except Exception as e:
            log_error(LogCategory.SYSTEM, f"禁用限流检测异常: {str(e)}")
            return False

    def add_master_prompt_internal(self, session_id: str, prompt: str, target_children: Optional[list] = None) -> bool:
        """
        内部方法：添加主会话prompt到存储

        Args:
            session_id: 主会话标识
            prompt: prompt内容
            target_children: 目标子会话列表

        Returns:
            bool: 是否添加成功
        """
        try:
            # 1. 获取存储实例
            storage = get_master_storage()

            # 2. 添加prompt
            result = storage.add_prompt(session_id, prompt, target_children)

            if result.get("success"):
                log_info(
                    LogCategory.MASTER,
                    f"内部添加主会话prompt - {session_id}: {prompt[:50]}..."
                )
                return True
            else:
                log_error(LogCategory.SYSTEM, f"添加prompt失败: {result.get('error')}")
                return False

        except Exception as e:
            log_error(LogCategory.SYSTEM, f"添加prompt异常: {str(e)}")
            return False

    def get_session_rate_limit_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        获取会话限流状态 (内部方法)

        Args:
            session_id: 会话标识

        Returns:
            Optional[Dict[str, Any]]: 状态信息，None表示会话未启用限流检测
        """
        if session_id not in self._detector_registry:
            return None

        detector = self._detector_registry[session_id]
        return detector.get_status()

    def get_manager_status(self) -> Dict[str, Any]:
        """
        获取管理器整体状态 (内部方法)

        Returns:
            Dict[str, Any]: 管理器状态
        """
        # 1. 统计状态
        active_sessions = len(self._detector_registry)
        master_sessions = len([
            s for s, d in self._detector_registry.items()
            if d.session_type == SessionType.MASTER
        ])
        child_sessions = len([
            s for s, d in self._detector_registry.items()
            if d.session_type == SessionType.CHILD
        ])

        return {
            "manager_status": "running",
            "active_sessions": active_sessions,
            "master_sessions": master_sessions,
            "child_sessions": child_sessions,
            "session_list": list(self._detector_registry.keys()),
            "timestamp": datetime.now().isoformat()
        }

    def cleanup_completed_tasks_internal(self) -> Dict[str, Any]:
        """
        内部清理已完成任务

        Returns:
            Dict[str, Any]: 清理结果
        """
        try:
            total_cleaned = 0
            session_stats = {}

            # 1. 遍历所有检测器
            for session_id, detector in self._detector_registry.items():
                cleaned_count = 0

                # 2. 清理已完成任务
                tasks_to_remove = []
                for task_id, task in detector.scheduled_tasks.items():
                    if task.status in ["executed", "cancelled", "failed"]:
                        tasks_to_remove.append(task_id)

                # 3. 移除任务
                for task_id in tasks_to_remove:
                    del detector.scheduled_tasks[task_id]
                    cleaned_count += 1
                    total_cleaned += 1

                session_stats[session_id] = cleaned_count

            log_info(
                LogCategory.SYSTEM,
                f"内部清理已完成任务 - 总计: {total_cleaned} 个"
            )

            return {
                "success": True,
                "total_cleaned": total_cleaned,
                "session_stats": session_stats,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            log_error(LogCategory.SYSTEM, f"清理任务异常: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }


# 全局单例实例
_rate_limit_manager = RateLimitManager()


def get_rate_limit_manager() -> RateLimitManager:
    """
    获取限流管理器实例

    Returns:
        RateLimitManager: 全局单例实例
    """
    return _rate_limit_manager