# -*- coding: utf-8 -*-
"""
Child会话监控器

@description 实现真正的5秒子会话清单刷新，符合PRD要求
"""

import logging
import threading
import time
import subprocess
from typing import Dict, Any, List, Optional
from datetime import datetime

# 导入资源管理器
from .resource_manager import get_resource_manager

# 配置日志系统
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ChildSessionMonitor:
    """
    Child会话监控器

    负责实现PRD要求的Master职责5：
    "每 5s 刷新子会话清单"
    """

    def __init__(self):
        """
        初始化Child会话监控器
        """
        # 1. 初始化状态
        self.is_monitoring = False
        self.monitor_thread = None
        self.last_refresh_time = None

        # 2. 配置参数
        self.refresh_interval = 5  # 每5秒刷新一次
        self.project_prefix = None

        # 3. 记录初始化
        logger.info("Child会话监控器初始化完成")

    def start_monitoring(self) -> Dict[str, Any]:
        """
        启动子会话清单监控

        Returns:
            Dict[str, Any]: 启动结果
        """
        try:
            # 1. 检查Master权限
            from .master_detector import is_master_node
            if not is_master_node():
                return {
                    "success": False,
                    "error": "仅Master节点可以启动子会话监控",
                    "node_type": "non-master"
                }

            # 2. 检查是否已经启动
            if self.is_monitoring:
                return {
                    "success": True,
                    "message": "子会话监控已在运行",
                    "status": "already_running"
                }

            # 3. 获取PROJECT_PREFIX
            import os
            self.project_prefix = os.getenv('PROJECT_PREFIX')
            if not self.project_prefix:
                return {
                    "success": False,
                    "error": "缺少PROJECT_PREFIX环境变量，无法监控子会话"
                }

            # 4. 启动监控线程
            self.monitor_thread = threading.Thread(
                target=self._monitoring_loop,
                daemon=True,
                name="ChildSessionMonitor"
            )

            self.is_monitoring = True
            self.monitor_thread.start()

            # 5. 记录启动成功
            logger.info(f"子会话监控启动成功，刷新间隔: {self.refresh_interval}秒")
            return {
                "success": True,
                "message": "子会话监控启动成功",
                "refresh_interval": self.refresh_interval,
                "project_prefix": self.project_prefix,
                "status": "started"
            }

        except Exception as e:
            # 6. 异常处理
            logger.error(f"启动子会话监控异常: {e}")
            return {
                "success": False,
                "error": f"启动失败: {str(e)}"
            }

    def stop_monitoring(self) -> Dict[str, Any]:
        """
        停止子会话清单监控

        Returns:
            Dict[str, Any]: 停止结果
        """
        try:
            # 1. 检查运行状态
            if not self.is_monitoring:
                return {
                    "success": True,
                    "message": "子会话监控未在运行",
                    "status": "not_running"
                }

            # 2. 停止监控
            self.is_monitoring = False

            # 3. 等待线程结束
            if self.monitor_thread and self.monitor_thread.is_alive():
                self.monitor_thread.join(timeout=10)

            # 4. 记录停止
            logger.info("子会话监控已停止")
            return {
                "success": True,
                "message": "子会话监控停止成功",
                "status": "stopped"
            }

        except Exception as e:
            # 5. 异常处理
            logger.error(f"停止子会话监控异常: {e}")
            return {
                "success": False,
                "error": f"停止失败: {str(e)}"
            }

    def _monitoring_loop(self) -> None:
        """
        监控循环主逻辑

        每5秒扫描tmux会话并更新子会话清单
        """
        logger.info("子会话监控循环启动")

        while self.is_monitoring:
            try:
                # 1. 更新刷新时间
                self.last_refresh_time = datetime.now()

                # 2. 扫描子会话
                child_sessions = self._scan_child_sessions()

                # 3. 更新MCP资源
                self._update_child_resources(child_sessions)

                # 4. 记录监控状态
                logger.debug(f"子会话清单刷新完成，发现 {len(child_sessions)} 个Child会话")

                # 5. 等待下次刷新
                time.sleep(self.refresh_interval)

            except Exception as e:
                # 6. 异常处理
                logger.error(f"子会话监控循环异常: {e}")
                time.sleep(self.refresh_interval)

        # 7. 循环结束
        logger.info("子会话监控循环结束")

    def _scan_child_sessions(self) -> List[Dict[str, Any]]:
        """
        扫描当前的Child会话

        Returns:
            List[Dict[str, Any]]: Child会话列表
        """
        try:
            # 1. 获取所有tmux会话
            result = subprocess.run(
                ['tmux', 'list-sessions', '-F', '#{session_name}:#{session_windows}:#{session_created}'],
                capture_output=True,
                text=True,
                timeout=10
            )

            child_sessions = []

            if result.returncode == 0:
                # 2. 解析会话信息
                for line in result.stdout.strip().split('\n'):
                    if not line:
                        continue

                    parts = line.split(':')
                    if len(parts) >= 3:
                        session_name = parts[0]

                        # 3. 检查是否为Child会话
                        child_prefix = f"{self.project_prefix}_child_"
                        if session_name.startswith(child_prefix):
                            # 4. 提取task_id
                            task_id = session_name[len(child_prefix):]

                            # 5. 构造会话信息
                            session_info = {
                                "session_name": session_name,
                                "task_id": task_id,
                                "windows": int(parts[1]) if parts[1].isdigit() else 0,
                                "created": parts[2] if len(parts) > 2 else "unknown",
                                "last_seen": datetime.now().isoformat(),
                                "project_prefix": self.project_prefix
                            }

                            child_sessions.append(session_info)

            # 6. 返回扫描结果
            return child_sessions

        except subprocess.TimeoutExpired:
            # 7. 超时处理
            logger.warning("扫描Child会话超时")
            return []
        except Exception as e:
            # 8. 异常处理
            logger.error(f"扫描Child会话异常: {e}")
            return []

    def _update_child_resources(self, child_sessions: List[Dict[str, Any]]) -> None:
        """
        更新MCP资源中的Child会话信息

        Args:
            child_sessions: Child会话列表
        """
        try:
            # 1. 获取资源管理器
            resource_manager = get_resource_manager()
            if not resource_manager:
                logger.warning("无法获取MCP资源管理器，跳过资源更新")
                return

            # 2. 获取当前的Child资源
            current_children = resource_manager.get_children()

            # 3. 构造新的Child资源映射
            new_children = {}
            for session in child_sessions:
                child_id = f"child_{session['task_id']}"

                # 4. 保留现有资源信息，更新会话状态
                if child_id in current_children:
                    child_resource = current_children[child_id].copy()
                    child_resource.update({
                        "session_name": session["session_name"],
                        "tmux_windows": session["windows"],
                        "last_seen": session["last_seen"],
                        "status": "active"
                    })
                else:
                    # 5. 创建新的Child资源
                    child_resource = {
                        "id": child_id,
                        "task_id": session["task_id"],
                        "session_name": session["session_name"],
                        "session_type": "child",
                        "project_prefix": session["project_prefix"],
                        "tmux_windows": session["windows"],
                        "created_at": session["created"],
                        "last_seen": session["last_seen"],
                        "status": "active"
                    }

                new_children[child_id] = child_resource

            # 6. 标记消失的Child会话
            for child_id, child_resource in current_children.items():
                if child_id not in new_children:
                    # Child会话已消失，标记为inactive
                    child_resource["status"] = "inactive"
                    child_resource["last_seen"] = datetime.now().isoformat()
                    new_children[child_id] = child_resource

            # 7. 更新资源管理器
            resource_manager.children = new_children
            resource_manager._notify_resource_change()

            # 8. 记录更新结果
            active_count = len([c for c in new_children.values() if c.get("status") == "active"])
            logger.debug(f"Child资源更新完成: {active_count} 个活跃会话，{len(new_children)} 个总会话")

        except Exception as e:
            # 9. 异常处理
            logger.error(f"更新Child资源异常: {e}")

    def get_monitoring_status(self) -> Dict[str, Any]:
        """
        获取监控状态

        Returns:
            Dict[str, Any]: 监控状态
        """
        try:
            # 1. 基础状态信息
            status = {
                "success": True,
                "is_monitoring": self.is_monitoring,
                "refresh_interval": self.refresh_interval,
                "project_prefix": self.project_prefix,
                "last_refresh_time": self.last_refresh_time.isoformat() if self.last_refresh_time else None,
                "monitor_thread_alive": self.monitor_thread.is_alive() if self.monitor_thread else False
            }

            # 2. 当前子会话信息
            if self.is_monitoring:
                child_sessions = self._scan_child_sessions()
                status["current_child_sessions"] = child_sessions
                status["active_child_count"] = len(child_sessions)
            else:
                status["current_child_sessions"] = []
                status["active_child_count"] = 0

            # 3. Master权限检查
            from .master_detector import is_master_node
            status["can_monitor"] = is_master_node()

            return status

        except Exception as e:
            # 4. 异常处理
            logger.error(f"获取监控状态异常: {e}")
            return {
                "success": False,
                "error": f"状态查询失败: {str(e)}"
            }

    def force_refresh_now(self) -> Dict[str, Any]:
        """
        立即强制刷新子会话清单

        Returns:
            Dict[str, Any]: 刷新结果
        """
        try:
            # 1. 检查Master权限
            from .master_detector import is_master_node
            if not is_master_node():
                return {
                    "success": False,
                    "error": "仅Master节点可以刷新子会话清单",
                    "node_type": "non-master"
                }

            # 2. 获取PROJECT_PREFIX
            import os
            project_prefix = os.getenv('PROJECT_PREFIX')
            if not project_prefix:
                return {
                    "success": False,
                    "error": "缺少PROJECT_PREFIX环境变量"
                }

            # 3. 执行扫描
            child_sessions = self._scan_child_sessions()

            # 4. 更新资源
            self._update_child_resources(child_sessions)

            # 5. 返回刷新结果
            logger.info(f"子会话清单立即刷新完成，发现 {len(child_sessions)} 个Child会话")
            return {
                "success": True,
                "message": "子会话清单刷新成功",
                "child_sessions": child_sessions,
                "active_count": len(child_sessions),
                "refresh_time": datetime.now().isoformat()
            }

        except Exception as e:
            # 6. 异常处理
            logger.error(f"强制刷新子会话异常: {e}")
            return {
                "success": False,
                "error": f"刷新失败: {str(e)}"
            }


# 全局Child会话监控器实例
_child_session_monitor = None
_monitor_lock = threading.Lock()


def get_child_session_monitor() -> ChildSessionMonitor:
    """
    获取全局Child会话监控器实例

    Returns:
        ChildSessionMonitor: 监控器实例
    """
    global _child_session_monitor

    with _monitor_lock:
        if _child_session_monitor is None:
            _child_session_monitor = ChildSessionMonitor()
            logger.info("创建全局Child会话监控器实例")
        return _child_session_monitor


def auto_start_child_monitoring() -> Dict[str, Any]:
    """
    自动启动Child会话监控

    在Master节点初始化时调用，实现PRD要求的自动化。

    Returns:
        Dict[str, Any]: 启动结果
    """
    try:
        # 1. 检查是否为Master节点
        from .master_detector import is_master_node
        if not is_master_node():
            return {
                "success": True,
                "message": "非Master节点，跳过子会话监控",
                "action": "skipped"
            }

        # 2. 获取监控器实例
        monitor = get_child_session_monitor()

        # 3. 启动监控
        result = monitor.start_monitoring()
        result["action"] = "auto_started"

        if result.get("success"):
            logger.info("Child会话监控自动启动完成")
        else:
            logger.warning(f"Child会话监控自动启动失败: {result.get('error')}")

        return result

    except Exception as e:
        # 4. 异常处理
        logger.error(f"自动启动Child会话监控异常: {e}")
        return {
            "success": False,
            "error": f"自动启动失败: {str(e)}"
        }