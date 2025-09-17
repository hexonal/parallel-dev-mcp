# -*- coding: utf-8 -*-
"""
FastMCP 实例

@description 共享的FastMCP实例，避免循环导入问题
"""

from fastmcp import FastMCP

# 创建共享的FastMCP实例
mcp = FastMCP("parallel-dev-mcp")