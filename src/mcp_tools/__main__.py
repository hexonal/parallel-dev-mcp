"""
MCP Tools Module Entry Point
用作 `python -m src.mcp_tools` 的入口点
"""

import sys
import os

# 添加项目根目录到 Python 路径以确保模块导入
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 启动 parallel_dev_mcp 服务器
from src.parallel_dev_mcp.server import mcp

if __name__ == "__main__":
    mcp.run()