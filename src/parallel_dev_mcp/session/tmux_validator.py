# -*- coding: utf-8 -*-
"""
Tmux环境验证器

@description 验证当前是否在tmux环境中运行，实现PRD要求的运行约束
"""

import os
import sys
import logging
import subprocess
from typing import Dict, Any, Optional
from datetime import datetime

# 配置日志系统
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class TmuxValidator:
    """
    Tmux环境验证器

    实现PRD要求："必须在 tmux 中运行（非 tmux 环境自动退出）"
    """

    def __init__(self):
        """
        初始化Tmux验证器
        """
        # 1. 记录初始化
        logger.info("Tmux环境验证器初始化")

    def is_in_tmux(self) -> bool:
        """
        检查当前是否在tmux环境中

        Returns:
            bool: 是否在tmux环境中
        """
        try:
            # 1. 检查TMUX环境变量
            tmux_env = os.environ.get('TMUX')
            if tmux_env:
                logger.info(f"检测到TMUX环境变量: {tmux_env}")
                return True

            # 2. 检查TMUX_PANE环境变量
            tmux_pane = os.environ.get('TMUX_PANE')
            if tmux_pane:
                logger.info(f"检测到TMUX_PANE环境变量: {tmux_pane}")
                return True

            # 3. 尝试运行tmux命令检查
            result = subprocess.run(
                ['tmux', 'display-message', '-p', '#{session_name}'],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                session_name = result.stdout.strip()
                logger.info(f"通过tmux命令检测到会话: {session_name}")
                return True

            # 4. 不在tmux环境中
            logger.warning("未检测到tmux环境")
            return False

        except FileNotFoundError:
            # 5. tmux命令不存在
            logger.warning("tmux命令不可用")
            return False
        except subprocess.TimeoutExpired:
            # 6. 命令超时
            logger.warning("tmux命令执行超时")
            return False
        except Exception as e:
            # 7. 其他异常
            logger.error(f"检测tmux环境时异常: {e}")
            return False

    def get_tmux_info(self) -> Dict[str, Any]:
        """
        获取tmux环境信息

        Returns:
            Dict[str, Any]: tmux环境信息
        """
        try:
            # 1. 基础信息
            info = {
                "is_in_tmux": self.is_in_tmux(),
                "timestamp": datetime.now().isoformat()
            }

            # 2. 如果在tmux中，获取详细信息
            if info["is_in_tmux"]:
                # 获取会话名
                session_result = subprocess.run(
                    ['tmux', 'display-message', '-p', '#{session_name}'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if session_result.returncode == 0:
                    info["session_name"] = session_result.stdout.strip()

                # 获取窗口索引
                window_result = subprocess.run(
                    ['tmux', 'display-message', '-p', '#{window_index}'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if window_result.returncode == 0:
                    info["window_index"] = window_result.stdout.strip()

                # 获取面板索引
                pane_result = subprocess.run(
                    ['tmux', 'display-message', '-p', '#{pane_index}'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if pane_result.returncode == 0:
                    info["pane_index"] = pane_result.stdout.strip()

                # 环境变量
                info["tmux_env"] = os.environ.get('TMUX', '')
                info["tmux_pane"] = os.environ.get('TMUX_PANE', '')

            # 3. 返回信息
            return info

        except Exception as e:
            # 4. 异常处理
            logger.error(f"获取tmux信息异常: {e}")
            return {
                "is_in_tmux": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    def validate_and_exit_if_needed(self, force_exit: bool = True) -> Dict[str, Any]:
        """
        验证tmux环境，如果不在tmux中则退出

        Args:
            force_exit: 是否强制退出（默认True）

        Returns:
            Dict[str, Any]: 验证结果
        """
        try:
            # 1. 检查tmux环境
            if not self.is_in_tmux():
                error_msg = "错误：必须在tmux环境中运行此程序！"
                logger.error(error_msg)

                result = {
                    "success": False,
                    "error": error_msg,
                    "action": "exit_required",
                    "timestamp": datetime.now().isoformat()
                }

                # 2. 如果设置了强制退出
                if force_exit:
                    print(f"\n{error_msg}")
                    print("请先启动tmux会话：")
                    print("  tmux new-session -s my_session")
                    print("或加入现有会话：")
                    print("  tmux attach-session -t my_session\n")
                    sys.exit(1)

                return result

            # 3. 在tmux环境中，返回成功
            tmux_info = self.get_tmux_info()
            logger.info(f"Tmux环境验证通过: {tmux_info.get('session_name', 'unknown')}")

            return {
                "success": True,
                "message": "Tmux环境验证通过",
                "tmux_info": tmux_info,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            # 4. 异常处理
            logger.error(f"Tmux环境验证异常: {e}")
            return {
                "success": False,
                "error": f"验证失败: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }


# 全局Tmux验证器实例
_tmux_validator = None


def get_tmux_validator() -> TmuxValidator:
    """
    获取全局Tmux验证器实例

    Returns:
        TmuxValidator: 验证器实例
    """
    global _tmux_validator

    if _tmux_validator is None:
        _tmux_validator = TmuxValidator()
        logger.info("创建全局Tmux验证器实例")

    return _tmux_validator


def validate_tmux_environment() -> Dict[str, Any]:
    """
    验证tmux环境（便捷函数）

    Returns:
        Dict[str, Any]: 验证结果
    """
    validator = get_tmux_validator()
    return validator.validate_and_exit_if_needed(force_exit=False)


def ensure_tmux_environment() -> None:
    """
    确保在tmux环境中运行，否则退出程序

    在系统启动时调用此函数，强制tmux环境要求
    """
    validator = get_tmux_validator()
    validator.validate_and_exit_if_needed(force_exit=True)