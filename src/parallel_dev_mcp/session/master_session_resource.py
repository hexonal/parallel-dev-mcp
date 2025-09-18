# -*- coding: utf-8 -*-
"""
主会话信息MCP资源

@description 提供主会话信息的MCP资源接口，用于存储和共享主会话发送的prompt信息
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path

# 导入FastMCP实例
from ..mcp_instance import mcp

# 导入结构化日志
from .structured_logger import log_info, log_warning, log_error, LogCategory

# 配置日志系统
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class MasterSessionStorage:
    """
    主会话信息存储器

    管理主会话发送的prompt信息和状态数据
    """

    def __init__(self) -> None:
        """初始化存储器"""
        # 1. 设置存储路径
        self.storage_dir = Path(".parallel_dev_mcp") / "session_data"
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self.master_info_file = self.storage_dir / "master_session_info.json"
        self.prompt_history_file = self.storage_dir / "prompt_history.json"

        # 2. 初始化数据结构
        self.master_info: Dict[str, Any] = {}
        self.prompt_history: List[Dict[str, Any]] = []

        # 3. 加载已有数据
        self._load_data()

        # 4. 记录初始化
        log_info(
            LogCategory.SYSTEM,
            "主会话信息存储器初始化完成"
        )

    def _load_data(self) -> None:
        """加载已有数据"""
        try:
            # 1. 加载主会话信息
            if self.master_info_file.exists():
                with open(self.master_info_file, 'r', encoding='utf-8') as f:
                    self.master_info = json.load(f)

            # 2. 加载prompt历史
            if self.prompt_history_file.exists():
                with open(self.prompt_history_file, 'r', encoding='utf-8') as f:
                    self.prompt_history = json.load(f)

        except Exception as e:
            log_error(
                LogCategory.SYSTEM,
                f"加载主会话数据失败: {str(e)}"
            )

    def _save_data(self) -> None:
        """保存数据到文件"""
        try:
            # 1. 保存主会话信息
            with open(self.master_info_file, 'w', encoding='utf-8') as f:
                json.dump(self.master_info, f, ensure_ascii=False, indent=2)

            # 2. 保存prompt历史
            with open(self.prompt_history_file, 'w', encoding='utf-8') as f:
                json.dump(self.prompt_history, f, ensure_ascii=False, indent=2)

        except Exception as e:
            log_error(
                LogCategory.SYSTEM,
                f"保存主会话数据失败: {str(e)}"
            )

    def update_master_info(self, session_id: str, info: Dict[str, Any]) -> Dict[str, Any]:
        """
        更新主会话信息

        Args:
            session_id: 会话ID
            info: 会话信息

        Returns:
            Dict[str, Any]: 更新结果
        """
        try:
            # 1. 更新会话信息
            self.master_info[session_id] = {
                **info,
                "last_updated": datetime.now().isoformat(),
                "session_id": session_id
            }

            # 2. 保存数据
            self._save_data()

            # 3. 记录更新
            log_info(
                LogCategory.MASTER,
                f"更新主会话信息 - 会话ID: {session_id}"
            )

            return {
                "success": True,
                "message": "主会话信息更新成功",
                "session_id": session_id,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            log_error(
                LogCategory.SYSTEM,
                f"更新主会话信息失败: {str(e)}"
            )
            return {
                "success": False,
                "error": f"更新失败: {str(e)}"
            }

    def add_prompt(self, session_id: str, prompt: str, target_children: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        添加prompt信息

        Args:
            session_id: 主会话ID
            prompt: prompt内容
            target_children: 目标子会话列表

        Returns:
            Dict[str, Any]: 添加结果
        """
        try:
            # 1. 创建prompt记录
            prompt_record = {
                "id": f"prompt_{int(datetime.now().timestamp() * 1000)}",
                "session_id": session_id,
                "prompt": prompt,
                "target_children": target_children or [],
                "created_at": datetime.now().isoformat(),
                "status": "active"
            }

            # 2. 添加到历史记录
            self.prompt_history.append(prompt_record)

            # 3. 保持历史记录数量限制（最多保存100条）
            if len(self.prompt_history) > 100:
                self.prompt_history = self.prompt_history[-100:]

            # 4. 保存数据
            self._save_data()

            # 5. 记录添加
            log_info(
                LogCategory.MASTER,
                f"添加prompt信息 - 会话ID: {session_id}, prompt: {prompt[:50]}..."
            )

            return {
                "success": True,
                "message": "Prompt信息添加成功",
                "prompt_id": prompt_record["id"],
                "timestamp": prompt_record["created_at"]
            }

        except Exception as e:
            log_error(
                LogCategory.SYSTEM,
                f"添加prompt信息失败: {str(e)}"
            )
            return {
                "success": False,
                "error": f"添加失败: {str(e)}"
            }

    def get_master_info(self, session_id: str) -> Dict[str, Any]:
        """
        获取主会话信息

        Args:
            session_id: 会话ID

        Returns:
            Dict[str, Any]: 会话信息
        """
        return self.master_info.get(session_id, {})

    def get_latest_prompt(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        获取最新的prompt信息

        Args:
            session_id: 会话ID

        Returns:
            Optional[Dict[str, Any]]: 最新的prompt信息
        """
        # 1. 筛选该会话的prompt
        session_prompts = [
            p for p in self.prompt_history
            if p["session_id"] == session_id and p["status"] == "active"
        ]

        # 2. 返回最新的
        if session_prompts:
            return session_prompts[-1]
        return None

    def get_all_master_sessions(self) -> Dict[str, Any]:
        """
        获取所有主会话信息

        Returns:
            Dict[str, Any]: 所有会话信息
        """
        return {
            "sessions": self.master_info,
            "total_count": len(self.master_info),
            "timestamp": datetime.now().isoformat()
        }


# 创建全局存储实例
_master_storage = MasterSessionStorage()


@mcp.resource("resource://master-sessions")
def master_sessions_resource() -> str:
    """
    主会话信息资源

    提供所有主会话的基础信息
    """
    try:
        # 1. 获取所有会话信息
        sessions_data = _master_storage.get_all_master_sessions()

        # 2. 格式化输出
        result = {
            "title": "主会话信息汇总",
            "description": "当前系统中所有主会话的基础信息",
            "data": sessions_data,
            "last_updated": datetime.now().isoformat()
        }

        return json.dumps(result, ensure_ascii=False, indent=2)

    except Exception as e:
        log_error(LogCategory.SYSTEM, f"获取主会话资源失败: {str(e)}")
        return json.dumps({
            "error": f"获取失败: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False)


@mcp.resource("resource://master-session-detail/{session_id}")
def master_session_detail_resource(session_id: str) -> str:
    """
    主会话详细信息资源

    提供指定主会话的详细信息，包括prompt历史
    """
    try:
        # 1. 获取会话基础信息
        master_info = _master_storage.get_master_info(session_id)

        # 2. 获取该会话的prompt历史
        session_prompts = [
            p for p in _master_storage.prompt_history
            if p["session_id"] == session_id
        ]

        # 3. 获取最新prompt
        latest_prompt = _master_storage.get_latest_prompt(session_id)

        # 4. 格式化输出
        result = {
            "title": f"主会话详情 - {session_id}",
            "session_id": session_id,
            "basic_info": master_info,
            "prompt_history": session_prompts,
            "latest_prompt": latest_prompt,
            "prompt_count": len(session_prompts),
            "last_updated": datetime.now().isoformat()
        }

        return json.dumps(result, ensure_ascii=False, indent=2)

    except Exception as e:
        log_error(LogCategory.SYSTEM, f"获取主会话详情失败: {str(e)}")
        return json.dumps({
            "error": f"获取失败: {str(e)}",
            "session_id": session_id,
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False)


@mcp.resource("resource://prompt-history")
def prompt_history_resource() -> str:
    """
    Prompt历史资源

    提供所有主会话的prompt历史记录
    """
    try:
        # 1. 获取prompt历史
        prompt_history = _master_storage.prompt_history

        # 2. 统计信息
        stats = {
            "total_prompts": len(prompt_history),
            "active_prompts": len([p for p in prompt_history if p["status"] == "active"]),
            "sessions_with_prompts": len(set(p["session_id"] for p in prompt_history))
        }

        # 3. 格式化输出
        result = {
            "title": "Prompt历史记录",
            "description": "所有主会话的prompt历史",
            "statistics": stats,
            "prompt_history": prompt_history,
            "last_updated": datetime.now().isoformat()
        }

        return json.dumps(result, ensure_ascii=False, indent=2)

    except Exception as e:
        log_error(LogCategory.SYSTEM, f"获取prompt历史失败: {str(e)}")
        return json.dumps({
            "error": f"获取失败: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False)


def get_master_storage() -> MasterSessionStorage:
    """
    获取主会话存储实例

    Returns:
        MasterSessionStorage: 存储实例
    """
    return _master_storage