"""
FastMCP Server for Parallel Development MCP Tools
优化后的三层MCP工具架构服务器 - 移除过度设计，专注核心功能
"""

from fastmcp import FastMCP
from typing import Dict, Any, List, Optional
import json
import os
from pathlib import Path
from datetime import datetime
import subprocess
import time

# 导入优化后的三层架构核心工具 - 确保@mcp_tool装饰器被执行
from .tmux import orchestrator  # 导入模块以执行@mcp_tool装饰器
from .session import session_manager, message_system, relationship_manager  # 导入模块以执行@mcp_tool装饰器
from .monitoring import health_monitor  # 导入模块以执行@mcp_tool装饰器
from ._internal import config_tools  # 导入模块以执行@mcp_tool装饰器

# 导入具体函数用于服务器逻辑（装饰器已经执行）
from .tmux.orchestrator import tmux_session_orchestrator
from .session.session_manager import create_development_session, terminate_session, query_session_status, list_all_managed_sessions, register_existing_session
from .session.message_system import send_message_to_session, get_session_messages, mark_message_read
from .session.relationship_manager import register_session_relationship, query_child_sessions
from .monitoring.health_monitor import check_system_health

# 读取环境变量配置
MCP_CONFIG = os.environ.get('MCP_CONFIG') or os.environ.get('MCP_CONFIG_PATH')
HOOKS_MCP_CONFIG = os.environ.get('HOOKS_MCP_CONFIG')
PROJECT_ROOT = os.environ.get('PROJECT_ROOT', os.getcwd())

def _get_env_var(name: str, default: str | None = None) -> str | None:
    """从 mcp.json 的 env 或 loaded_config 中读取变量，不再依赖 shell export。
    优先级：loaded_config.env -> loaded_config.environment.env/variables -> loaded_config.mcpServers.*.env -> os.environ
    """
    try:
        cfg = get_loaded_config()
        if isinstance(cfg, dict):
            # 顶层 env
            env = cfg.get('env')
            if isinstance(env, dict) and name in env:
                return str(env[name])
            # environment 下的 env/variables
            environment = cfg.get('environment')
            if isinstance(environment, dict):
                env2 = environment.get('env') or environment.get('variables')
                if isinstance(env2, dict) and name in env2:
                    return str(env2[name])
            # mcpServers.*.env
            ms = cfg.get('mcpServers')
            if isinstance(ms, dict):
                for srv in ms.values():
                    if isinstance(srv, dict):
                        env3 = srv.get('env')
                        if isinstance(env3, dict) and name in env3:
                            return str(env3[name])
        # 回退环境变量
        return os.environ.get(name, default)
    except Exception:
        return os.environ.get(name, default)
HOOKS_CONFIG_DIR = os.environ.get('HOOKS_CONFIG_DIR', os.path.join(PROJECT_ROOT, 'config/hooks'))
DANGEROUSLY_SKIP_PERMISSIONS = os.environ.get('DANGEROUSLY_SKIP_PERMISSIONS', 'false').lower() == 'true'

# 导入配置管理工具
from ._internal.config_tools import set_loaded_config, get_loaded_config
from ._internal import SessionNaming
from ._internal.health_store import get_health_store
from ._internal.web_port import check_service, post_health
from ._internal.code_activity import _quick_detect

# 确保关键目录存在
Path(HOOKS_CONFIG_DIR).mkdir(parents=True, exist_ok=True)

def get_config_value(key: str, default: Any = None) -> Any:
    """从加载的配置中获取指定键的值"""
    loaded_config = get_loaded_config()
    if loaded_config and isinstance(loaded_config, dict):
        return loaded_config.get(key, default)
    return default

# 创建FastMCP服务器实例
mcp = FastMCP("Parallel Development MCP - 优化三层架构")
# 延后导入基于 @mcp 装饰器的资源/提示，避免循环导入
from .monitoring import health_resource  # noqa: F401,E402
from .session import prompts as _prompt_templates  # noqa: F401,E402

# === 🤖 自动会话扫描和注册 ===

def auto_scan_and_register_sessions():
    """启动时自动扫描现有tmux会话并注册到MCP系统"""
    import subprocess
    import re
    from .session.session_manager import register_existing_session
    from ._internal.global_registry import get_global_registry
    
    try:
        # 获取所有tmux会话
        result = subprocess.run(['tmux', 'list-sessions', '-F', '#{session_name}'], 
                              capture_output=True, text=True, check=True)
        tmux_sessions = result.stdout.strip().split('\n') if result.stdout.strip() else []
        
        # 过滤parallel开头的会话
        parallel_sessions = [s for s in tmux_sessions if s.startswith('parallel_')]
        
        if not parallel_sessions:
            print("🔍 未发现parallel相关的tmux会话")
            return {"scanned": 0, "registered": 0}
        
        print(f"🔍 发现 {len(parallel_sessions)} 个parallel会话，开始自动注册...")
        
        registered_count = 0
        for session_name in parallel_sessions:
            try:
                # 调用注册函数
                result = register_existing_session(session_name)
                if result.get("success"):
                    registered_count += 1
                    session_type = result.get("session_type", "unknown")
                    project_id = result.get("project_id", "unknown")
                    print(f"✅ 注册成功: {session_name} [{session_type}] -> {project_id}")
                else:
                    print(f"⚠️  注册失败: {session_name} - {result.get('error', '未知错误')}")
            except Exception as e:
                print(f"❌ 注册异常: {session_name} - {str(e)}")
        
        print(f"🎯 自动扫描完成: 扫描 {len(parallel_sessions)} 个会话，成功注册 {registered_count} 个")
        return {"scanned": len(parallel_sessions), "registered": registered_count}
        
    except subprocess.CalledProcessError:
        print("⚠️  tmux未运行或无可用会话")
        return {"scanned": 0, "registered": 0}
    except Exception as e:
        print(f"❌ 自动扫描失败: {str(e)}")
        return {"scanned": 0, "registered": 0, "error": str(e)}

def _resolve_master_target(current_session: str | None) -> tuple[str | None, str | None, str]:
    """解析主会话绑定目标。

    返回 (master_session, project_id, mode)
    - 优先 MASTER_BASE：{MASTER_BASE}_master
    - 其次当前 tmux 会话为 parallel_*_task_master
    - 最后使用 PROJECT_ID 走并行命名规范
    """
    master_base = _get_env_var('MASTER_BASE')
    if master_base and master_base.strip():
        return f"{master_base.strip()}_master", master_base.strip(), 'env_master'

    if current_session and current_session.endswith('_task_master') and current_session.startswith('parallel_'):
        parts = current_session.split('_')
        if len(parts) >= 4:
            return current_session, parts[1], 'current_session'

    project_id = _get_env_var('PROJECT_ID')
    if project_id and project_id != 'unknown':
        return SessionNaming.master_session(project_id), project_id, 'naming'

    return None, None, 'unknown'


def _tmux_session_exists(name: str) -> bool:
    """判断 tmux 会话是否存在。"""
    try:
        subprocess.run(['tmux', 'has-session', '-t', name], check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError:
        return False


def _register_master_session(master_session: str, project_id: str) -> int | None:
    """在注册中心注册主会话，并写入 web_port（若提供）。返回 web_port。"""
    from ._internal.global_registry import get_global_registry
    registry = get_global_registry()
    if not registry.get_session_info(master_session):
        tmux_web_port = _get_env_var('TMUX_WEB_PORT')
        web_port_val = int(tmux_web_port) if tmux_web_port and str(tmux_web_port).isdigit() else None
        registry.register_session(master_session, "master", project_id, web_port=web_port_val)
    info = registry.get_session_info(master_session)
    return info.to_dict().get('web_port') if info else None


def auto_bind_master_session():
    """自动绑定主会话（<=50行）：解析目标 → 校验存在 → 注册 → 写入全局。"""
    try:
        # 获取当前 tmux 会话名
        try:
            res = subprocess.run(['tmux', 'display-message', '-p', '#S'], capture_output=True, text=True, check=True)
            current_session = res.stdout.strip()
        except subprocess.CalledProcessError:
            current_session = None

        master_session, project_id, _mode = _resolve_master_target(current_session)
        if not master_session:
            return {"bound": False, "reason": "无法确定主会话"}
        if not _tmux_session_exists(master_session):
            return {"bound": False, "reason": f"主会话不存在: {master_session}"}

        web_port = _register_master_session(master_session, project_id)
        global BOUND_MASTER_SESSION, BOUND_PROJECT_ID
        BOUND_MASTER_SESSION, BOUND_PROJECT_ID = master_session, project_id

        print(f"🎯 主会话自动绑定成功: {master_session} (项目: {project_id})")
        return {"bound": True, "master_session": master_session, "project_id": project_id, "web_port": web_port}
    except Exception as e:
        print(f"❌ 主会话绑定失败: {str(e)}")
        return {"bound": False, "error": str(e)}

# 全局绑定状态
BOUND_MASTER_SESSION = None
BOUND_PROJECT_ID = None

# 延迟启动标志
_startup_initialized = False

# === 内部辅助：启动/检查web服务、子会话健康上报 ===

_web_service_process = None  # 不再在此文件内启动 Web 服务

def _start_child_health_reporter(port: int):
    """启动子会话健康上报后台线程，每5秒向 /message/health 上报一次。"""
    import threading
    def _loop():
        while True:
            try:
                from ._internal.global_registry import get_global_registry
                registry = get_global_registry()
                # 仅上报绑定项目下的子会话
                sessions = registry.list_all_sessions()
                for s in sessions.values():
                    if s.session_type == 'child' and (BOUND_PROJECT_ID is None or s.project_id == BOUND_PROJECT_ID):
                        writing, reasons = _quick_detect(s.name)
                        payload = {
                            'session': s.name,
                            'status': 'ok',
                            'timestamp': datetime.now().isoformat(),
                            'meta': {
                                'project_id': s.project_id,
                                'task_id': s.task_id,
                                'activity': 'writing_code' if writing else 'idle',
                            }
                        }
                        # 本地记录心跳（用于资源查询）
                        get_health_store().record_heartbeat(
                            s.name,
                            ts=datetime.now(),
                            meta={'project_id': s.project_id, 'task_id': s.task_id, 'activity': payload['meta']['activity']}
                        )
                        post_health(port, payload)
            except Exception:
                pass
            time.sleep(5)
    t = threading.Thread(target=_loop, name="child-health-reporter", daemon=True)
    t.start()

def initialize_startup():
    """延迟启动初始化 - 避免干扰FastMCP工具注册"""
    global _startup_initialized
    if not _startup_initialized:
        print("🚀 Parallel-Dev-MCP启动中...")
        
        # 先清理过期会话
        from ._internal.global_registry import auto_cleanup_stale_sessions, sync_tmux_to_registry
        cleanup_result = auto_cleanup_stale_sessions()
        if cleanup_result["cleaned_count"] > 0:
            print(f"🧹 清理了 {cleanup_result['cleaned_count']} 个过期会话")
        
        # 同步tmux会话到注册表
        sync_result = sync_tmux_to_registry()
        if sync_result["synced_count"] > 0:
            print(f"🔄 同步了 {sync_result['synced_count']} 个会话到注册表")
        
        # 初始化消息模板目录（提示模板可选）
        try:
            from .session.prompts import ensure_msg_dir as _ensure_msg_dir
            _ensure_msg_dir()
        except Exception:
            pass

        # 主会话绑定
        master_bind_result = auto_bind_master_session()
        # 若显式指定了 MASTER_BASE 且绑定失败，则启动失败
        _master_base = _get_env_var('MASTER_BASE')
        if (_master_base and _master_base.strip()) and not master_bind_result.get('bound'):
            raise RuntimeError(f"主会话绑定失败（MASTER_BASE={_master_base}）：{master_bind_result}")

        # 仅主会话启动 Web 服务；如果设置了端口但启动失败，MCP 启动失败
        web_port = master_bind_result.get('web_port')
        if web_port:
            # 不在此启动服务；仅检查服务可达
            if not check_service(int(web_port)):
                raise RuntimeError(f"Web服务未就绪: 127.0.0.1:{web_port}/health")
            _start_child_health_reporter(int(web_port))
        elif _master_base and _master_base.strip():
            # 指定了 MASTER_BASE 但未提供端口，强制失败，确保注册/传递机制可用
            raise RuntimeError("未提供 TMUX_WEB_PORT，无法启动主会话 Web 服务")

        print(f"📋 启动完成 - 清理: {cleanup_result['cleaned_count']} | 同步: {sync_result['synced_count']} | 绑定: {master_bind_result.get('bound', False)}")
        _startup_initialized = True

# === MCP工具已移至对应模块 ===
# 
# 🔧 TMUX LAYER: tmux/orchestrator.py
# - tmux_session_orchestrator
# - launch_claude_in_session
#
# 📋 SESSION LAYER: session/模块中
# - create_development_session (session/session_manager.py)
# - send_message_to_session (session/message_system.py)
# - get_session_messages (session/message_system.py) 
# - mark_message_read (session/message_system.py)
# - register_session_relationship (session/relationship_manager.py)
# - query_child_sessions (session/relationship_manager.py)
# - get_session_hierarchy (session/relationship_manager.py)
# - find_session_path (session/relationship_manager.py)
# - terminate_session (session/session_manager.py)
# - query_session_status (session/session_manager.py)
# - list_all_managed_sessions (session/session_manager.py)
# - register_existing_session (session/session_manager.py)
#
# 📊 MONITORING LAYER: monitoring/health_monitor.py
# - check_system_health
#
# 👨‍💼 CONFIG LAYER: _internal/config_tools.py
# - get_environment_config



def main():
    """主入口函数 - 基于环境变量的简化启动"""
    import sys
    import json
    
    # 从环境变量读取配置（与uvx兼容）
    continue_on_error = os.environ.get('CONTINUE_ON_ERROR', 'false').lower() == 'true'
    
    # 如果指定了MCP配置文件，尝试加载到全局变量
    if MCP_CONFIG and os.path.exists(MCP_CONFIG):
        try:
            with open(MCP_CONFIG, 'r') as f:
                config_data = json.load(f)
                set_loaded_config(config_data)
            print(f"✅ MCP配置已加载到全局变量: {MCP_CONFIG}", file=sys.stderr)
        except Exception as e:
            print(f"⚠️  MCP配置加载失败: {e}", file=sys.stderr)
            set_loaded_config(None)
    elif MCP_CONFIG:
        print(f"⚠️  MCP配置文件不存在: {MCP_CONFIG}", file=sys.stderr)
        set_loaded_config(None)
    
    # 初始化（包含主会话绑定与会话同步）
    initialize_startup()

    # 启动服务器
    try:
        mcp.run()
    except Exception as e:
        if not continue_on_error:
            sys.stderr.write(f"Server error: {e}\n")
            sys.exit(1)
        else:
            sys.stderr.write(f"Warning: {e}\n")

if __name__ == "__main__":
    main()
