"""
Health Store - 子会话健康状态存储与判定

轻量级内存存储，提供：
- record_heartbeat(session, ts, meta): 记录心跳
- snapshot(now, thresholds): 生成所有会话健康快照（healthy/degraded/dead）

阈值建议（秒）：interval=5, degraded=15, dead=45（可由上层通过 env 配置）
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Any, Optional


@dataclass
class Heartbeat:
    last_at: datetime
    seq: int = 0
    meta: Dict[str, Any] = field(default_factory=dict)


class HealthStore:
    """简单的进程内健康存储（单例）"""

    _inst: Optional["HealthStore"] = None

    def __new__(cls):
        if cls._inst is None:
            cls._inst = super().__new__(cls)
            cls._inst._beats = {}
        return cls._inst

    def record_heartbeat(self, session: str, ts: Optional[datetime] = None,
                         seq: Optional[int] = None, meta: Optional[Dict[str, Any]] = None) -> None:
        """记录一次心跳（≤50行）

        - seq 若提供且小于等于已有值则忽略（防重放）
        - ts 默认为当前时间
        """
        ts = ts or datetime.now()
        hb = self._beats.get(session)
        if hb is None:
            self._beats[session] = Heartbeat(last_at=ts, seq=seq or 0, meta=meta or {})
            return
        if seq is not None and seq <= hb.seq:
            return
        hb.last_at = ts
        if seq is not None:
            hb.seq = seq
        if meta:
            hb.meta.update(meta)

    def snapshot(self, now: Optional[datetime] = None, *,
                 interval_sec: int = 5, degraded_sec: int = 15, dead_sec: int = 45) -> Dict[str, Any]:
        """生成所有会话的健康快照（≤50行）

        返回：{"sessions": {name: {last_at, age_sec, status, seq, meta}}}
        """
        now = now or datetime.now()
        out: Dict[str, Any] = {"sessions": {}}
        for name, hb in self._beats.items():
            age = (now - hb.last_at).total_seconds()
            status = "healthy"
            if age > dead_sec:
                status = "dead"
            elif age > degraded_sec:
                status = "degraded"
            out["sessions"][name] = {
                "last_at": hb.last_at.isoformat(),
                "age_sec": age,
                "status": status,
                "seq": hb.seq,
                "meta": hb.meta,
                "expected_interval_sec": interval_sec,
            }
        return out


def get_health_store() -> HealthStore:
    """获取全局 HealthStore"""
    return HealthStore()

