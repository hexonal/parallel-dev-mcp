# -*- coding: utf-8 -*-
"""
Tmux MCP工具集

@description 实现tmux会话管理的MCP工具，包括会话列表、删除和消息发送功能
"""

import subprocess
import logging
import re
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, validator
from fastmcp import FastMCP

# 获取FastMCP实例
from ..mcp_instance import mcp

# 配置日志系统
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class TmuxSessionModel(BaseModel):
    """Tmux会话数据模型"""

    session_name: str = Field(..., description="会话名称")
    session_id: str = Field(..., description="会话ID")
    is_attached: bool = Field(False, description="是否有客户端连接")
    created_at: Optional[str] = Field(None, description="创建时间")
    window_count: int = Field(0, description="窗口数量", ge=0)
    pane_count: int = Field(0, description="面板数量", ge=0)
    project_prefix: Optional[str] = Field(None, description="项目前缀")
    task_id: Optional[str] = Field(None, description="任务ID")

    @validator('session_name')
    def validate_session_name(cls, v: str) -> str:
        """验证会话名称格式"""
        if not v or not v.strip():
            raise ValueError('会话名称不能为空')
        return v.strip()


class TmuxOperationResult(BaseModel):
    """Tmux操作结果模型"""

    success: bool = Field(..., description="操作是否成功")
    message: str = Field("", description="操作结果消息")
    data: Dict[str, Any] = Field(default_factory=dict, description="返回数据")
    error_code: Optional[int] = Field(None, description="错误码")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat(), description="操作时间")


def _execute_tmux_command(command: List[str]) -> subprocess.CompletedProcess:
    """
    执行tmux命令

    Args:
        command: tmux命令列表

    Returns:
        subprocess.CompletedProcess: 执行结果
    """
    try:
        # 1. 执行命令
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=30,
            check=False
        )

        # 2. 记录执行信息
        logger.debug(f"执行tmux命令: {' '.join(command)}")

        return result

    except subprocess.TimeoutExpired as e:
        # 3. 处理超时
        logger.error(f"tmux命令超时: {' '.join(command)}")
        raise RuntimeError(f"命令执行超时: {e}")

    except Exception as e:
        # 4. 处理其他异常
        logger.error(f"tmux命令执行失败: {' '.join(command)}, 错误: {e}")
        raise RuntimeError(f"命令执行失败: {e}")


def _parse_session_name(session_name: str) -> Dict[str, Optional[str]]:
    """
    解析会话名称，提取项目前缀和任务ID

    Args:
        session_name: 会话名称

    Returns:
        Dict[str, Optional[str]]: 解析结果
    """
    # 1. 初始化结果
    result = {
        "project_prefix": None,
        "task_id": None,
        "is_child": False,
        "is_master": False
    }

    try:
        # 2. 检查是否为child会话格式：{PROJECT_PREFIX}_child_{task_id}
        child_pattern = r'^(.+?)_child_(.+)$'
        child_match = re.match(child_pattern, session_name, re.IGNORECASE)

        if child_match:
            result["project_prefix"] = child_match.group(1)
            result["task_id"] = child_match.group(2)
            result["is_child"] = True
            return result

        # 3. 检查是否为master会话格式：{PROJECT_PREFIX}_master_{name}
        master_pattern = r'^(.+?)_master_(.+)$'
        master_match = re.match(master_pattern, session_name, re.IGNORECASE)

        if master_match:
            result["project_prefix"] = master_match.group(1)
            result["is_master"] = True
            return result

        # 4. 检查是否以环境变量PROJECT_PREFIX开头
        project_prefix = os.environ.get('PROJECT_PREFIX', 'PARALLEL')
        if session_name.startswith(project_prefix):
            result["project_prefix"] = project_prefix
            # 可能是简化的项目会话
            remaining = session_name[len(project_prefix):].lstrip('_')
            if remaining:
                result["task_id"] = remaining

        return result

    except Exception as e:
        # 5. 解析异常
        logger.warning(f"解析会话名称失败: {session_name}, 错误: {e}")
        return result


@mcp.tool
def list_tmux_sessions(project_prefix: Optional[str] = None, child_only: bool = True) -> Dict[str, Any]:
    """
    列出tmux会话

    获取系统中的tmux会话列表，可按项目前缀过滤，默认只返回child会话。

    Args:
        project_prefix: 项目前缀过滤，None则使用环境变量PROJECT_PREFIX
        child_only: 是否只返回child会话

    Returns:
        Dict[str, Any]: 会话列表和统计信息
    """
    try:
        # 1. 获取项目前缀
        if project_prefix is None:
            project_prefix = os.environ.get('PROJECT_PREFIX', 'PARALLEL')

        # 2. 执行tmux命令获取会话列表
        command = ['tmux', 'list-sessions', '-F', '#{session_name}:#{session_id}:#{session_attached}:#{session_created}:#{session_windows}']
        result = _execute_tmux_command(command)

        if result.returncode != 0:
            if 'no server running' in result.stderr.lower():
                return TmuxOperationResult(
                    success=True,
                    message="没有运行的tmux服务器",
                    data={"sessions": [], "total_count": 0, "child_count": 0, "master_count": 0}
                ).model_dump()
            else:
                raise RuntimeError(f"获取会话列表失败: {result.stderr}")

        # 3. 解析会话信息
        sessions = []
        child_count = 0
        master_count = 0

        for line in result.stdout.strip().split('\n'):
            if not line:
                continue

            try:
                # 4. 解析会话行
                parts = line.split(':')
                if len(parts) < 5:
                    continue

                session_name = parts[0]
                session_id = parts[1]
                is_attached = parts[2] == '1'
                created_timestamp = parts[3]
                window_count = int(parts[4]) if parts[4].isdigit() else 0

                # 5. 解析会话名称
                name_info = _parse_session_name(session_name)

                # 6. 检查是否匹配项目前缀
                if name_info["project_prefix"] != project_prefix:
                    continue

                # 7. 检查是否只返回child会话
                if child_only and not name_info["is_child"]:
                    continue

                # 8. 创建会话模型
                session_model = TmuxSessionModel(
                    session_name=session_name,
                    session_id=session_id,
                    is_attached=is_attached,
                    created_at=created_timestamp,
                    window_count=window_count,
                    pane_count=0,  # 需要额外查询
                    project_prefix=name_info["project_prefix"],
                    task_id=name_info["task_id"]
                )

                sessions.append(session_model.model_dump())

                # 9. 统计计数
                if name_info["is_child"]:
                    child_count += 1
                elif name_info["is_master"]:
                    master_count += 1

            except Exception as e:
                logger.warning(f"解析会话行失败: {line}, 错误: {e}")
                continue

        # 10. 返回结果
        return TmuxOperationResult(
            success=True,
            message=f"成功获取{len(sessions)}个会话",
            data={
                "sessions": sessions,
                "total_count": len(sessions),
                "child_count": child_count,
                "master_count": master_count,
                "project_prefix": project_prefix,
                "child_only": child_only
            }
        ).model_dump()

    except Exception as e:
        # 11. 处理异常
        logger.error(f"列出tmux会话失败: {e}")
        return TmuxOperationResult(
            success=False,
            message=f"列出会话失败: {str(e)}",
            data={"sessions": [], "total_count": 0}
        ).model_dump()


@mcp.tool
def kill_tmux_session(session_name: str, force: bool = False) -> Dict[str, Any]:
    """
    删除指定的tmux会话

    删除指定名称的tmux会话，可选择是否强制删除。

    Args:
        session_name: 要删除的会话名称
        force: 是否强制删除（即使有客户端连接）

    Returns:
        Dict[str, Any]: 删除操作结果
    """
    try:
        # 1. 验证会话名称
        if not session_name or not session_name.strip():
            raise ValueError("会话名称不能为空")

        session_name = session_name.strip()

        # 2. 检查会话是否存在
        check_command = ['tmux', 'has-session', '-t', session_name]
        check_result = _execute_tmux_command(check_command)

        if check_result.returncode != 0:
            return TmuxOperationResult(
                success=False,
                message=f"会话不存在: {session_name}",
                data={"session_name": session_name, "existed": False}
            ).model_dump()

        # 3. 检查会话是否有客户端连接（如果不强制删除）
        if not force:
            info_command = ['tmux', 'list-sessions', '-F', '#{session_name}:#{session_attached}']
            info_result = _execute_tmux_command(info_command)

            if info_result.returncode == 0:
                for line in info_result.stdout.strip().split('\n'):
                    if line.startswith(session_name + ':'):
                        parts = line.split(':')
                        if len(parts) >= 2 and parts[1] == '1':
                            return TmuxOperationResult(
                                success=False,
                                message=f"会话有客户端连接，请使用force=True强制删除: {session_name}",
                                data={"session_name": session_name, "is_attached": True}
                            ).model_dump()

        # 4. 执行删除命令
        kill_command = ['tmux', 'kill-session', '-t', session_name]
        kill_result = _execute_tmux_command(kill_command)

        if kill_result.returncode != 0:
            raise RuntimeError(f"删除会话失败: {kill_result.stderr}")

        # 5. 记录删除操作
        logger.info(f"成功删除tmux会话: {session_name}")

        # 6. 返回成功结果
        return TmuxOperationResult(
            success=True,
            message=f"成功删除会话: {session_name}",
            data={
                "session_name": session_name,
                "force": force,
                "existed": True
            }
        ).model_dump()

    except Exception as e:
        # 7. 处理异常
        logger.error(f"删除tmux会话失败: {session_name}, 错误: {e}")
        return TmuxOperationResult(
            success=False,
            message=f"删除会话失败: {str(e)}",
            data={"session_name": session_name, "error": str(e)}
        ).model_dump()


@mcp.tool
def send_keys_to_tmux_session(
    session_name: str,
    keys: str,
    window_index: Optional[int] = None,
    pane_index: Optional[int] = None,
    enter: bool = True
) -> Dict[str, Any]:
    """
    向tmux会话发送按键

    向指定的tmux会话发送按键序列，可指定窗口和面板。

    Args:
        session_name: 目标会话名称
        keys: 要发送的按键序列
        window_index: 目标窗口索引（可选）
        pane_index: 目标面板索引（可选）
        enter: 是否在按键后发送回车键

    Returns:
        Dict[str, Any]: 发送操作结果
    """
    try:
        # 1. 验证参数
        if not session_name or not session_name.strip():
            raise ValueError("会话名称不能为空")

        if not keys:
            raise ValueError("按键序列不能为空")

        session_name = session_name.strip()

        # 2. 检查会话是否存在
        check_command = ['tmux', 'has-session', '-t', session_name]
        check_result = _execute_tmux_command(check_command)

        if check_result.returncode != 0:
            return TmuxOperationResult(
                success=False,
                message=f"会话不存在: {session_name}",
                data={"session_name": session_name, "existed": False}
            ).model_dump()

        # 3. 构建目标字符串
        target = session_name
        if window_index is not None:
            target += f':{window_index}'
            if pane_index is not None:
                target += f'.{pane_index}'

        # 4. 构建发送命令
        send_command = ['tmux', 'send-keys', '-t', target, keys]
        if enter:
            send_command.append('Enter')

        # 5. 执行发送命令
        send_result = _execute_tmux_command(send_command)

        if send_result.returncode != 0:
            raise RuntimeError(f"发送按键失败: {send_result.stderr}")

        # 6. 记录发送操作
        logger.info(f"成功向tmux会话发送按键: {session_name} -> {keys}")

        # 7. 返回成功结果
        return TmuxOperationResult(
            success=True,
            message=f"成功发送按键到会话: {session_name}",
            data={
                "session_name": session_name,
                "target": target,
                "keys": keys,
                "enter": enter,
                "window_index": window_index,
                "pane_index": pane_index
            }
        ).model_dump()

    except Exception as e:
        # 8. 处理异常
        logger.error(f"向tmux会话发送按键失败: {session_name}, 错误: {e}")
        return TmuxOperationResult(
            success=False,
            message=f"发送按键失败: {str(e)}",
            data={
                "session_name": session_name,
                "keys": keys,
                "error": str(e)
            }
        ).model_dump()


@mcp.tool
def get_tmux_session_info(session_name: str) -> Dict[str, Any]:
    """
    获取tmux会话详细信息

    获取指定会话的详细信息，包括窗口、面板等。

    Args:
        session_name: 会话名称

    Returns:
        Dict[str, Any]: 会话详细信息
    """
    try:
        # 1. 验证会话名称
        if not session_name or not session_name.strip():
            raise ValueError("会话名称不能为空")

        session_name = session_name.strip()

        # 2. 检查会话是否存在
        check_command = ['tmux', 'has-session', '-t', session_name]
        check_result = _execute_tmux_command(check_command)

        if check_result.returncode != 0:
            return TmuxOperationResult(
                success=False,
                message=f"会话不存在: {session_name}",
                data={"session_name": session_name, "existed": False}
            ).model_dump()

        # 3. 获取会话基本信息
        session_command = ['tmux', 'display-message', '-t', session_name, '-p', '#{session_name}:#{session_id}:#{session_attached}:#{session_created}:#{session_windows}']
        session_result = _execute_tmux_command(session_command)

        if session_result.returncode != 0:
            raise RuntimeError(f"获取会话信息失败: {session_result.stderr}")

        # 4. 解析会话基本信息
        session_line = session_result.stdout.strip()
        parts = session_line.split(':')

        if len(parts) < 5:
            raise ValueError(f"会话信息格式错误: {session_line}")

        session_info = {
            "session_name": parts[0],
            "session_id": parts[1],
            "is_attached": parts[2] == '1',
            "created_at": parts[3],
            "window_count": int(parts[4]) if parts[4].isdigit() else 0
        }

        # 5. 获取窗口信息
        windows_command = ['tmux', 'list-windows', '-t', session_name, '-F', '#{window_index}:#{window_name}:#{window_active}:#{window_panes}']
        windows_result = _execute_tmux_command(windows_command)

        windows = []
        total_panes = 0

        if windows_result.returncode == 0:
            for line in windows_result.stdout.strip().split('\n'):
                if not line:
                    continue

                try:
                    win_parts = line.split(':')
                    if len(win_parts) >= 4:
                        window_panes = int(win_parts[3]) if win_parts[3].isdigit() else 0
                        windows.append({
                            "index": int(win_parts[0]) if win_parts[0].isdigit() else 0,
                            "name": win_parts[1],
                            "is_active": win_parts[2] == '1',
                            "pane_count": window_panes
                        })
                        total_panes += window_panes

                except Exception as e:
                    logger.warning(f"解析窗口信息失败: {line}, 错误: {e}")

        # 6. 解析会话名称
        name_info = _parse_session_name(session_name)

        # 7. 构建完整信息
        complete_info = {
            **session_info,
            "windows": windows,
            "total_panes": total_panes,
            "project_prefix": name_info["project_prefix"],
            "task_id": name_info["task_id"],
            "is_child": name_info["is_child"],
            "is_master": name_info["is_master"]
        }

        # 8. 返回结果
        return TmuxOperationResult(
            success=True,
            message=f"成功获取会话信息: {session_name}",
            data=complete_info
        ).model_dump()

    except Exception as e:
        # 9. 处理异常
        logger.error(f"获取tmux会话信息失败: {session_name}, 错误: {e}")
        return TmuxOperationResult(
            success=False,
            message=f"获取会话信息失败: {str(e)}",
            data={"session_name": session_name, "error": str(e)}
        ).model_dump()