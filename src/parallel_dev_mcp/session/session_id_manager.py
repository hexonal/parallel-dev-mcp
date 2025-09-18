# -*- coding: utf-8 -*-
"""
Session ID 管理器

@description 管理session_id.txt文件，实现PRD要求的Master会话标识
"""

import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
import uuid

# 配置日志系统
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class SessionIdManager:
    """
    Session ID 管理器

    负责Master节点的session_id.txt文件管理，符合PRD要求：
    - 仅Master节点可写入
    - Child节点禁止写入
    - 自动生成和维护session ID
    """

    def __init__(self, project_root: Optional[str] = None):
        """
        初始化Session ID管理器

        Args:
            project_root: 项目根目录，默认为当前目录
        """
        # 1. 设置项目根目录
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.session_id_file = self.project_root / "session_id.txt"

        # 2. 记录初始化
        logger.info(f"Session ID管理器初始化: {self.session_id_file}")

    def write_master_session_id(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        写入Master会话ID

        仅Master节点可以调用此方法。自动生成或使用提供的session ID。

        Args:
            session_id: 会话ID，如果不提供则自动生成

        Returns:
            Dict[str, Any]: 写入结果
        """
        try:
            # 1. 检查Master权限
            from .master_detector import is_master_node
            if not is_master_node():
                return {
                    "success": False,
                    "error": "仅Master节点可以写入session_id.txt",
                    "node_type": "non-master"
                }

            # 2. 生成或使用提供的session ID
            if not session_id:
                session_id = str(uuid.uuid4())

            # 3. 检查文件是否已存在
            if self.session_id_file.exists():
                existing_id = self.read_session_id()
                if existing_id and existing_id.get("session_id"):
                    logger.info(f"session_id.txt已存在，当前ID: {existing_id['session_id']}")
                    return {
                        "success": True,
                        "message": "session_id.txt已存在，无需重写",
                        "session_id": existing_id["session_id"],
                        "action": "existing"
                    }

            # 4. 写入session ID到文件
            with open(self.session_id_file, 'w', encoding='utf-8') as f:
                f.write(session_id)

            # 5. 验证写入
            written_id = self.read_session_id()
            if written_id and written_id.get("session_id") == session_id:
                logger.info(f"Master会话ID写入成功: {session_id}")
                return {
                    "success": True,
                    "message": "Master会话ID写入成功",
                    "session_id": session_id,
                    "file_path": str(self.session_id_file),
                    "action": "created"
                }
            else:
                return {
                    "success": False,
                    "error": "写入验证失败，文件内容不匹配"
                }

        except Exception as e:
            # 6. 异常处理
            logger.error(f"写入Master会话ID异常: {e}")
            return {
                "success": False,
                "error": f"写入失败: {str(e)}"
            }

    def read_session_id(self) -> Dict[str, Any]:
        """
        读取session ID

        任何节点都可以读取session ID。

        Returns:
            Dict[str, Any]: 读取结果
        """
        try:
            # 1. 检查文件是否存在
            if not self.session_id_file.exists():
                return {
                    "success": True,
                    "session_id": None,
                    "message": "session_id.txt文件不存在"
                }

            # 2. 读取文件内容
            with open(self.session_id_file, 'r', encoding='utf-8') as f:
                session_id = f.read().strip()

            # 3. 验证session ID格式
            if not session_id:
                return {
                    "success": True,
                    "session_id": None,
                    "message": "session_id.txt文件为空"
                }

            # 4. 返回读取结果
            return {
                "success": True,
                "session_id": session_id,
                "file_path": str(self.session_id_file),
                "file_size": self.session_id_file.stat().st_size,
                "last_modified": datetime.fromtimestamp(
                    self.session_id_file.stat().st_mtime
                ).isoformat()
            }

        except Exception as e:
            # 5. 异常处理
            logger.error(f"读取session ID异常: {e}")
            return {
                "success": False,
                "error": f"读取失败: {str(e)}"
            }

    def clear_session_id(self) -> Dict[str, Any]:
        """
        清理session ID文件

        仅Master节点可以调用此方法。

        Returns:
            Dict[str, Any]: 清理结果
        """
        try:
            # 1. 检查Master权限
            from .master_detector import is_master_node
            if not is_master_node():
                return {
                    "success": False,
                    "error": "仅Master节点可以清理session_id.txt",
                    "node_type": "non-master"
                }

            # 2. 检查文件是否存在
            if not self.session_id_file.exists():
                return {
                    "success": True,
                    "message": "session_id.txt文件不存在，无需清理"
                }

            # 3. 删除文件
            self.session_id_file.unlink()

            # 4. 验证删除
            if not self.session_id_file.exists():
                logger.info("session_id.txt文件清理成功")
                return {
                    "success": True,
                    "message": "session_id.txt文件清理成功"
                }
            else:
                return {
                    "success": False,
                    "error": "文件删除失败，文件仍然存在"
                }

        except Exception as e:
            # 5. 异常处理
            logger.error(f"清理session ID异常: {e}")
            return {
                "success": False,
                "error": f"清理失败: {str(e)}"
            }

    def get_session_status(self) -> Dict[str, Any]:
        """
        获取session状态信息

        Returns:
            Dict[str, Any]: 状态信息
        """
        try:
            # 1. 读取session ID
            read_result = self.read_session_id()

            # 2. 检查Master权限
            from .master_detector import is_master_node, get_master_session_info
            master_info = get_master_session_info()

            # 3. 构造状态信息
            status = {
                "success": True,
                "session_file_exists": self.session_id_file.exists(),
                "session_id": read_result.get("session_id"),
                "is_master_node": master_info.get("is_master", False),
                "can_write": is_master_node(),
                "file_path": str(self.session_id_file),
                "project_root": str(self.project_root)
            }

            # 4. 添加文件信息
            if self.session_id_file.exists():
                stat = self.session_id_file.stat()
                status.update({
                    "file_size": stat.st_size,
                    "last_modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "permissions": oct(stat.st_mode)[-3:]
                })

            # 5. 添加Master会话信息
            status["master_session_info"] = master_info

            return status

        except Exception as e:
            # 6. 异常处理
            logger.error(f"获取session状态异常: {e}")
            return {
                "success": False,
                "error": f"状态查询失败: {str(e)}"
            }

    def ensure_master_session_id(self) -> Dict[str, Any]:
        """
        确保Master会话ID存在

        如果是Master节点且session_id.txt为空，则自动写入。
        这是PRD要求的自动化行为。

        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            # 1. 检查是否为Master节点
            from .master_detector import is_master_node
            if not is_master_node():
                return {
                    "success": True,
                    "message": "非Master节点，无需写入session_id.txt",
                    "action": "skipped"
                }

            # 2. 检查session_id.txt状态
            read_result = self.read_session_id()

            if read_result.get("session_id"):
                # 已有session ID，无需操作
                return {
                    "success": True,
                    "message": "session_id.txt已存在且有效",
                    "session_id": read_result["session_id"],
                    "action": "existing"
                }
            else:
                # 需要写入新的session ID
                write_result = self.write_master_session_id()
                write_result["action"] = "auto_created"
                logger.info("Master节点自动创建session_id.txt")
                return write_result

        except Exception as e:
            # 3. 异常处理
            logger.error(f"确保Master会话ID异常: {e}")
            return {
                "success": False,
                "error": f"自动处理失败: {str(e)}"
            }


# 全局Session ID管理器实例
_session_id_manager = None


def get_session_id_manager(project_root: Optional[str] = None) -> SessionIdManager:
    """
    获取全局Session ID管理器实例

    Args:
        project_root: 项目根目录

    Returns:
        SessionIdManager: 管理器实例
    """
    global _session_id_manager

    if _session_id_manager is None:
        _session_id_manager = SessionIdManager(project_root)
        logger.info("创建全局Session ID管理器实例")

    return _session_id_manager


def auto_ensure_master_session_id() -> Dict[str, Any]:
    """
    自动确保Master会话ID存在

    在系统初始化时调用，实现PRD要求的自动化。

    Returns:
        Dict[str, Any]: 操作结果
    """
    try:
        # 1. 获取管理器实例
        manager = get_session_id_manager()

        # 2. 执行自动确保逻辑
        result = manager.ensure_master_session_id()

        # 3. 记录结果
        if result.get("success"):
            logger.info(f"Master会话ID自动确保完成: {result.get('action', 'unknown')}")
        else:
            logger.warning(f"Master会话ID自动确保失败: {result.get('error')}")

        return result

    except Exception as e:
        # 4. 异常处理
        logger.error(f"自动确保Master会话ID异常: {e}")
        return {
            "success": False,
            "error": f"自动处理异常: {str(e)}"
        }