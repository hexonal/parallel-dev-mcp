#!/usr/bin/env python3
"""MCP服务器模块主入口

当作为模块运行时（python -m src.mcp_server），启动标准MCP协议服务器
"""

import sys
import os

# 确保能够导入项目模块
if __name__ == "__main__":
    # 添加项目根目录到Python路径
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    sys.path.insert(0, project_root)
    
    from src.mcp_server.mcp_server import main
    import asyncio
    
    # 启动MCP服务器
    asyncio.run(main())