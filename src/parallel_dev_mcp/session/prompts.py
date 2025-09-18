"""
Session Prompts - 主/子会话消息模板（会话层）

说明：
- 模板位于项目根目录下 `.msg/` 目录
- 文件名：master.md / child.md
- 不存在则跳过（不影响业务）
"""

from __future__ import annotations

import os
from typing import List, Dict, Any

from ..server import mcp, PROJECT_ROOT  # 依赖已在 server 中先创建 mcp 实例


def _msg_dir() -> str:
    return os.path.join(PROJECT_ROOT, ".msg")


def ensure_msg_dir() -> None:
    """确保 `.msg` 目录存在（≤50行）"""
    os.makedirs(_msg_dir(), exist_ok=True)


def _read_template(kind: str) -> str:
    """读取模板文本（kind: 'master'|'child'）。若不存在返回空字符串（≤50行）"""
    name = "master.md" if kind == "master" else "child.md"
    fp = os.path.join(_msg_dir(), name)
    try:
        with open(fp, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""


@mcp.prompt
def master_message(task: str | None = None, substitute: bool = False) -> List[Dict[str, Any]]:
    """主会话发送模板（读取 .msg/master.md；缺失则返回 []）"""
    tpl = _read_template("master")
    if not tpl:
        return []
    content = tpl.replace("{task}", task) if (substitute and task) else tpl
    return [{"role": "user", "content": content}]


@mcp.prompt
def child_message(task: str | None = None, substitute: bool = False) -> List[Dict[str, Any]]:
    """子会话发送模板（读取 .msg/child.md；缺失则返回 []）"""
    tpl = _read_template("child")
    if not tpl:
        return []
    content = tpl.replace("{task}", task) if (substitute and task) else tpl
    return [{"role": "user", "content": content}]

