# -*- coding: utf-8 -*-
"""
Master节点检测器

@description 检测当前环境是否为Master节点，符合PRD要求
"""

import os
import subprocess
import logging
from typing import Optional, Dict, Any
from pathlib import Path

# 配置日志系统
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def is_master_node() -> bool:
    """
    检测当前是否为Master节点

    根据PRD要求，Master节点需要满足：
    1. tmux会话名称匹配 {PROJECT_PREFIX}_master 模式
    2. 具有session_id.txt写权限
    3. 不是Child节点

    Returns:
        bool: True表示是Master节点
    """
    # 1. 检查环境变量
    project_prefix = os.getenv('PROJECT_PREFIX')
    if not project_prefix:
        logger.warning("PROJECT_PREFIX环境变量未设置，无法确定Master节点")
        return False

    # 2. 检查tmux会话
    current_session = get_current_tmux_session()
    if not current_session:
        logger.info("未在tmux会话中运行")
        return False

    # 3. 检查是否为Master会话
    master_pattern = f"{project_prefix}_master"
    if current_session == master_pattern:
        logger.info(f"检测到Master会话: {current_session}")
        return True

    # 4. 检查是否为Child会话（排除）
    if current_session.startswith(f"{project_prefix}_child_"):
        logger.info(f"检测到Child会话: {current_session}")
        return False

    # 5. 其他情况默认不是Master
    logger.info(f"当前会话 {current_session} 不匹配Master模式 {master_pattern}")
    return False


def get_current_tmux_session() -> Optional[str]:
    """
    获取当前tmux会话名称

    Returns:
        Optional[str]: 会话名称，如果不在tmux中则返回None
    """
    try:
        # 1. 检查是否在tmux中
        if not os.getenv('TMUX'):
            return None

        # 2. 获取当前tmux会话名称
        result = subprocess.run(
            ['tmux', 'display-message', '-p', '#S'],
            capture_output=True,
            text=True,
            timeout=5
        )

        # 3. 处理结果
        if result.returncode == 0:
            session_name = result.stdout.strip()
            logger.debug(f"当前tmux会话: {session_name}")
            return session_name
        else:
            logger.warning(f"获取tmux会话失败: {result.stderr}")
            return None

    except subprocess.TimeoutExpired:
        # 4. 超时处理
        logger.error("获取tmux会话名称超时")
        return None
    except Exception as e:
        # 5. 异常处理
        logger.error(f"获取tmux会话名称异常: {e}")
        return None


def check_session_id_permissions() -> bool:
    """
    检查session_id.txt文件权限

    Master节点需要具有写权限，Child节点禁止写入

    Returns:
        bool: True表示具有写权限
    """
    try:
        # 1. 构造session_id.txt路径
        session_id_file = Path.cwd() / "session_id.txt"

        # 2. 检查文件是否存在
        if session_id_file.exists():
            # 文件存在，检查写权限
            if os.access(session_id_file, os.W_OK):
                logger.debug("session_id.txt文件具有写权限")
                return True
            else:
                logger.info("session_id.txt文件无写权限（可能是Child节点）")
                return False
        else:
            # 3. 文件不存在，检查目录写权限
            parent_dir = session_id_file.parent
            if os.access(parent_dir, os.W_OK):
                logger.debug("可以在当前目录创建session_id.txt")
                return True
            else:
                logger.warning("当前目录无写权限")
                return False

    except Exception as e:
        # 4. 异常处理
        logger.error(f"检查session_id.txt权限异常: {e}")
        return False


def validate_master_environment() -> Dict[str, Any]:
    """
    验证Master节点环境完整性

    检查所有Master节点必需的环境配置

    Returns:
        Dict[str, Any]: 验证结果
    """
    validation_result = {
        "is_master": False,
        "issues": [],
        "environment": {}
    }

    try:
        # 1. 检查环境变量
        project_prefix = os.getenv('PROJECT_PREFIX')
        web_port = os.getenv('WEB_PORT')

        validation_result["environment"] = {
            "PROJECT_PREFIX": project_prefix,
            "WEB_PORT": web_port,
            "current_dir": str(Path.cwd())
        }

        # 2. 验证必需环境变量
        if not project_prefix:
            validation_result["issues"].append("缺少PROJECT_PREFIX环境变量")

        if not web_port:
            validation_result["issues"].append("缺少WEB_PORT环境变量")

        # 3. 检查Master节点状态
        if is_master_node():
            validation_result["is_master"] = True
            logger.info("Master节点环境验证通过")
        else:
            validation_result["issues"].append("当前不是Master节点")

        # 4. 检查文件权限
        if not check_session_id_permissions():
            validation_result["issues"].append("缺少session_id.txt写权限")

        # 5. 记录验证结果
        if validation_result["issues"]:
            logger.warning(f"Master环境验证发现问题: {validation_result['issues']}")
        else:
            logger.info("Master节点环境验证完全通过")

        return validation_result

    except Exception as e:
        # 6. 异常处理
        logger.error(f"Master环境验证异常: {e}")
        validation_result["issues"].append(f"验证过程异常: {str(e)}")
        return validation_result


def get_master_session_info() -> Dict[str, Any]:
    """
    获取Master会话详细信息

    Returns:
        Dict[str, Any]: Master会话信息
    """
    try:
        # 1. 收集基础信息
        info = {
            "is_master": is_master_node(),
            "tmux_session": get_current_tmux_session(),
            "project_prefix": os.getenv('PROJECT_PREFIX'),
            "web_port": os.getenv('WEB_PORT'),
            "session_id_writable": check_session_id_permissions(),
            "working_directory": str(Path.cwd())
        }

        # 2. 添加tmux详细信息
        if info["tmux_session"]:
            info["tmux_details"] = get_tmux_session_details(info["tmux_session"])

        # 3. 记录信息收集结果
        logger.info(f"Master会话信息收集完成: {info['is_master']}")
        return info

    except Exception as e:
        # 4. 异常处理
        logger.error(f"获取Master会话信息异常: {e}")
        return {"error": str(e)}


def get_tmux_session_details(session_name: str) -> Dict[str, Any]:
    """
    获取tmux会话详细信息

    Args:
        session_name: 会话名称

    Returns:
        Dict[str, Any]: 会话详细信息
    """
    try:
        # 1. 获取会话信息
        result = subprocess.run(
            ['tmux', 'list-sessions', '-F', '#{session_name}:#{session_windows}:#{session_created}'],
            capture_output=True,
            text=True,
            timeout=5
        )

        # 2. 解析结果
        if result.returncode == 0:
            for line in result.stdout.strip().split('\n'):
                if line.startswith(session_name + ':'):
                    parts = line.split(':')
                    return {
                        "name": parts[0],
                        "windows": int(parts[1]) if parts[1].isdigit() else 0,
                        "created": parts[2] if len(parts) > 2 else "unknown"
                    }

        # 3. 默认返回
        return {"name": session_name, "windows": 0, "created": "unknown"}

    except Exception as e:
        # 4. 异常处理
        logger.error(f"获取tmux会话详情异常: {e}")
        return {"error": str(e)}