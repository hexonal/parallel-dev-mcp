# -*- coding: utf-8 -*-
"""
parallel_dev_mcp 包

@description Claude Code并行开发系统，采用优雅的四层FastMCP工具架构
"""

__version__ = "1.0.0"
__author__ = "Parallel Dev MCP Team"
__description__ = (
    "Claude Code并行开发系统，采用优雅的四层FastMCP工具架构，基于最新FastMCP 2.11.3+"
)

# 导出主要组件
from .server import mcp

__all__ = ["__version__", "__author__", "__description__", "mcp"]
