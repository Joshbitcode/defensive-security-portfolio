"""Unified alert structure: all honeypot formats are normalized into Event first."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone


def parse_iso(ts: str) -> datetime:
    """Parse an ISO8601 time string and normalize it to a UTC-aware datetime.

    Normalizing to UTC ensures the isoformat strings stored in the database can be
    compared directly in lexicographic order.
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
    """A normalized alert. Required: ts / src_ip / dst_ip / honeypot / event_type."""

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
        """Composite dedup key: same source + same destination port + same node + same type + same payload = the same behavior.

        No time component; time is handled by Deduper's window mechanism.
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
