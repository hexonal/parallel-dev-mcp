# -*- coding: utf-8 -*-
"""
Prompt模板管理包

@description 提供Master/Child Prompt模板和继续执行Prompt系统
"""

from .template_manager import PromptTemplateManager, get_template_manager
from .prompt_types import PromptType, PromptContext, TemplateInfo, PromptResult
from .variable_processor import VariableProcessor, get_variable_processor
# 注意：prompt_tools.py 已删除（YAGNI清理，无MCP工具）

__all__ = [
    "PromptTemplateManager",
    "get_template_manager",
    "PromptType",
    "PromptContext",
    "TemplateInfo",
    "PromptResult",
    "VariableProcessor",
    "get_variable_processor"
]