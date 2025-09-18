"""
Code Activity Detector - 基于 tmux pane 内容判定是否“正在写代码”。

提供两类检测：
- quick_detect(session): 无等待，使用当前进程+末尾内容启发式
- windowed_detect(session, window_sec): 前后采样对比（较准确但会阻塞 window_sec 秒）

判定启发式（可同时命中则更可信）：
- 进程启发式：pane_current_command 属于编辑器（vim/nvim/nano/micro/helix等）
- 输出启发式：末尾新增行包含明显代码/patch标记（```、diff --git、+++、---、@@、;、{ }、= 等），且行数阈值
"""

from __future__ import annotations

import subprocess
import time
from typing import Dict, Any, List, Tuple


_EDITORS = {"vim", "nvim", "nano", "micro", "hx", "helix", "emacs"}


def _pane_current_command(session: str) -> str:
    """获取 pane 当前进程名（≤50行）"""
    try:
        res = subprocess.run(
            ["tmux", "display-message", "-pt", session, "#{pane_current_command}"],
            capture_output=True, text=True, check=True
        )
        return (res.stdout or "").strip()
    except Exception:
        return ""


def _capture_tail(session: str, lines: int = 150) -> List[str]:
    """抓取 pane 末尾若干行（≤50行）"""
    try:
        res = subprocess.run(
            ["tmux", "capture-pane", "-pt", session], capture_output=True, text=True, check=True
        )
        content = res.stdout.splitlines() if res.stdout else []
        return content[-lines:]
    except Exception:
        return []


def _is_code_like_line(s: str) -> bool:
    s2 = s.strip()
    if not s2:
        return False
    # 代码块/patch常见特征
    markers = ("```", "diff --git ", "+++ ", "--- ", "@@ ")
    if any(m in s2 for m in markers):
        return True
    # 常见语法特征（启发式）
    score = 0
    for ch in "{}();=.[]<>":
        if ch in s2:
            score += 1
    keywords = ("class ", "def ", "func ", "public ", "private ", "return ", "import ", "from ")
    if any(k in s2 for k in keywords):
        score += 1
    return score >= 2


def _quick_detect(session: str) -> Tuple[bool, Dict[str, Any]]:
    """快速检测是否在写代码（≤50行）

    - 无等待；结合进程启发式与末尾内容启发式
    - 返回 (is_writing, reasons)
    """
    cmd = _pane_current_command(session)
    tail = _capture_tail(session, lines=120)
    code_like = sum(1 for ln in tail if _is_code_like_line(ln))
    reasons = {
        "pane_current_command": cmd,
        "code_like_lines": code_like,
        "tail_sample": min(len(tail), 120)
    }
    if cmd in _EDITORS:
        return True, {**reasons, "by": "editor_process"}
    if code_like >= 15:  # 阈值：末尾内容中明显代码行 >= 15
        return True, {**reasons, "by": "tail_content"}
    return False, reasons


def _windowed_detect(session: str, window_sec: float = 3.0) -> Tuple[bool, Dict[str, Any]]:
    """窗口采样检测（≤50行）

    - t0 获取末尾，sleep window_sec，再取末尾，比较新增行的代码特征
    - 返回 (is_writing, reasons)
    """
    t0 = _capture_tail(session, lines=300)
    time.sleep(max(0.1, window_sec))
    t1 = _capture_tail(session, lines=300)
    # 找到 t0 的尾部在 t1 中的位置，粗略比较新增部分
    join0 = "\n".join(t0[-60:])
    join1 = "\n".join(t1)
    idx = join1.rfind(join0)
    new_lines = t1 if idx < 0 else t1[-max(1, len(t1) - len(t0)) :]
    code_like = sum(1 for ln in new_lines if _is_code_like_line(ln))
    reasons = {
        "new_lines": len(new_lines),
        "code_like_new": code_like,
        "window_sec": window_sec
    }
    return (code_like >= 10), reasons  # 新增部分代码行数阈值
