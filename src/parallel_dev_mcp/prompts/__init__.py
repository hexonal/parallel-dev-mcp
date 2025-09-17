# -*- coding: utf-8 -*-
"""
Prompt模板管理包

@description 提供Master/Child Prompt模板和继续执行Prompt系统
"""

from .template_manager import PromptTemplateManager, get_template_manager
from .prompt_types import PromptType, PromptContext, TemplateInfo, PromptResult
from .variable_processor import VariableProcessor, get_variable_processor
from . import prompt_tools  # 导入MCP工具模块

__all__ = [
    "PromptTemplateManager",
    "get_template_manager",
    "PromptType",
    "PromptContext",
    "TemplateInfo",
    "PromptResult",
    "VariableProcessor",
    "get_variable_processor",
    "prompt_tools"
]