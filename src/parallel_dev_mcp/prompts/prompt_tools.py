# -*- coding: utf-8 -*-
"""
Prompt MCP工具

@description 提供Prompt模板管理的FastMCP工具接口
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

# 获取FastMCP实例
from ..mcp_instance import mcp
from .template_manager import get_template_manager
from .prompt_types import PromptType, PromptContext

# 配置日志系统
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# 移除 generate_prompt_tool - 过度工程化，简单字符串拼接即可


# 移除 list_templates_tool - 模板数量有限，硬编码即可


# 移除 reload_template_tool - 生产环境不需要热重载


# 移除 validate_templates_tool - 可在构建时验证，不需要运行时工具


# 移除 get_template_info_tool - 调试用途，可简化为日志输出


def _generate_continue_prompt_internal(
    session_name: Optional[str] = None,
    context_message: Optional[str] = None
) -> Dict[str, Any]:
    """
    生成继续执行Prompt内部函数

    内部使用，不暴露为MCP工具。系统根据上下文自动生成Prompt。

    专门用于生成继续执行的Prompt，通常在触发限流时使用。

    Args:
        session_name: 会话名称
        context_message: 上下文消息

    Returns:
        Dict[str, Any]: 继续执行Prompt结果
    """
    try:
        # 1. 创建上下文
        context = PromptContext(
            prompt_type=PromptType.CONTINUE_EXECUTION,
            session_name=session_name,
            variables={"context_message": context_message} if context_message else {}
        )

        # 2. 生成继续执行Prompt
        template_manager = get_template_manager()
        result = template_manager.generate_prompt(
            prompt_type=PromptType.CONTINUE_EXECUTION,
            context=context
        )

        # 3. 记录操作
        logger.info(f"生成继续执行Prompt: 会话={session_name}")

        # 4. 返回结果
        return {
            "success": result.success,
            "content": result.content,
            "session_name": session_name,
            "context_message": context_message,
            "generated_at": result.generated_at.isoformat(),
            "error_message": result.error_message
        }

    except Exception as e:
        # 5. 异常处理
        logger.error(f"生成继续执行Prompt工具异常: {e}")
        return {
            "success": False,
            "error": f"生成继续执行Prompt失败: {str(e)}"
        }