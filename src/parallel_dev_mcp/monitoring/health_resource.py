"""
Health Resource - 会话健康只读资源（监控层）

从 SessionRegistry 与 HealthStore 聚合数据，暴露为单一资源以供模型读取。
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, Any

from fastmcp import FastMCP  # type: ignore
from .._internal.health_store import get_health_store
from .._internal.global_registry import get_global_registry
from ..server import _get_env_var, mcp


@mcp.resource("monitoring://sessions")
def health_sessions_resource() -> Dict[str, Any]:
    """返回全量会话健康快照（≤50行）"""
    reg = get_global_registry()
    hs = get_health_store()

    def _to_int(name: str, default: int) -> int:
        v = _get_env_var(name)
        return int(v) if v and str(v).isdigit() else default

    snap = hs.snapshot(
        interval_sec=_to_int("HEALTH_INTERVAL", 5),
        degraded_sec=_to_int("HEALTH_DEGRADED", 15),
        dead_sec=_to_int("HEALTH_DEAD", 45),
    )
    sessions = reg.list_all_sessions()
    out: Dict[str, Any] = {
        "generated_at": datetime.now().isoformat(),
        "thresholds": {
            "interval_sec": _to_int("HEALTH_INTERVAL", 5),
            "degraded_sec": _to_int("HEALTH_DEGRADED", 15),
            "dead_sec": _to_int("HEALTH_DEAD", 45),
        },
        "sessions": {},
    }
    for name, info in sessions.items():
        base = info.to_dict()
        hb = snap["sessions"].get(name, {})
        out["sessions"][name] = {
            **base,
            "health": hb or {
                "status": "unknown",
                "age_sec": None,
                "expected_interval_sec": _to_int("HEALTH_INTERVAL", 5),
            },
        }
    return out
