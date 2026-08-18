"""统一告警结构：所有蜜罐格式先归一化成 Event。"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone


def parse_iso(ts: str) -> datetime:
    """解析 ISO8601 时间串，统一转成 UTC 时区的 aware datetime。

    统一到 UTC 是为了让数据库里的 isoformat 字符串可以直接按字典序比较。
    """
    s = ts.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


@dataclass
class Event:
    """归一化后的告警。必填：ts / src_ip / dst_ip / honeypot / event_type。"""

    ts: datetime
    src_ip: str
    dst_ip: str
    honeypot: str
    event_type: str
    src_port: int | None = None
    dst_port: int | None = None
    payload_hash: str | None = None
    raw: str | None = None

    def dedup_key(self) -> str:
        """复合去重键：同源 + 同目的端口 + 同节点 + 同类型 + 同载荷 = 同一行为。

        不含时间；时间交给 Deduper 的窗口机制处理。
        """
        material = "|".join(
            [
                self.src_ip,
                str(self.dst_port or ""),
                self.honeypot,
                self.event_type,
                self.payload_hash or "",
            ]
        )
        return hashlib.sha256(material.encode("utf-8")).hexdigest()[:16]
