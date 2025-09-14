"""
Configuration Tools - 配置管理工具

MCP环境配置相关的工具函数。
"""

import os
from typing import Dict, Any, Optional

from .response_builder import ResponseBuilder

# MCP工具装饰器
def mcp_tool(name: str = None, description: str = None):
    """MCP工具装饰器"""
    def decorator(func):
        func.mcp_tool_name = name or func.__name__
        func.mcp_tool_description = description or func.__doc__
        return func
    return decorator

# 读取环境变量配置
MCP_CONFIG = os.environ.get('MCP_CONFIG')
HOOKS_MCP_CONFIG = os.environ.get('HOOKS_MCP_CONFIG')
PROJECT_ROOT = os.environ.get('PROJECT_ROOT', os.getcwd())
HOOKS_CONFIG_DIR = os.environ.get('HOOKS_CONFIG_DIR', os.path.join(PROJECT_ROOT, 'config/hooks'))
DANGEROUSLY_SKIP_PERMISSIONS = os.environ.get('DANGEROUSLY_SKIP_PERMISSIONS', 'false').lower() == 'true'

# 全局配置数据存储 - 避免循环导入
_LOADED_CONFIG: Optional[Dict[str, Any]] = None

def set_loaded_config(config: Optional[Dict[str, Any]]) -> None:
    """设置已加载的MCP配置数据 - 由server.py调用"""
    global _LOADED_CONFIG
    _LOADED_CONFIG = config

def get_loaded_config() -> Optional[Dict[str, Any]]:
    """获取已加载的MCP配置数据"""
    return _LOADED_CONFIG

@mcp_tool(
    name="get_environment_config",
    description="获取当前MCP服务器的环境配置"
)
def get_environment_config() -> Dict[str, Any]:
    """获取当前MCP服务器的环境配置"""
    try:
        loaded_config = get_loaded_config()
        config = {
            "mcp_config_path": MCP_CONFIG,
            "loaded_config_data": loaded_config,  # 实际加载的配置数据
            "hooks_mcp_config": HOOKS_MCP_CONFIG,
            "project_root": PROJECT_ROOT,
            "hooks_config_dir": HOOKS_CONFIG_DIR,
            "dangerously_skip_permissions": DANGEROUSLY_SKIP_PERMISSIONS,
            "working_directory": os.getcwd(),
            "config_loaded": loaded_config is not None
        }
        return ResponseBuilder.success(data=config)
    except Exception as e:
        return ResponseBuilder.error(f"获取环境配置失败: {str(e)}")