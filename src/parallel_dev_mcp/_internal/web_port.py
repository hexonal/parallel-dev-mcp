"""
Web Port Client - 主会话 Web 服务交互工具（内部）

仅提供 HTTP 客户端能力：
- check_service(port) → 校验 /health 可达
- post_health(port, payload) → 上报 /message/health

说明：不启动或引用任何 examples/ 下的实现，调用方只关心端口是否就绪、能否发送。
"""

from __future__ import annotations

from typing import Dict, Any
import urllib.request
import json


def _base_url(port: int) -> str:
    return f"http://127.0.0.1:{port}"


def check_service(port: int, timeout: float = 2.0) -> bool:
    """检查 Web 服务 /health 可达（≤50行）"""
    url = _base_url(port) + "/health"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return resp.status == 200
    except Exception:
        return False


def post_health(port: int, payload: Dict[str, Any], timeout: float = 2.0) -> bool:
    """POST 到 /message/health（≤50行）"""
    url = _base_url(port) + "/message/health"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status == 200
    except Exception:
        return False

