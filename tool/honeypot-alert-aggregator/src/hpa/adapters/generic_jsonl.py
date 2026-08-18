"""Generic JSON Lines adapter: one JSON alert per line.

Required fields: ts, src_ip, dst_ip, honeypot, event_type
Optional fields: src_port, dst_port, payload_hash, raw
When payload_hash is absent, the first 16 hex digits of raw's sha256 are used if raw is provided.
"""
from __future__ import annotations

import hashlib
import json
from typing import Optional

from ..models import Event, parse_iso

REQUIRED = ("ts", "src_ip", "dst_ip", "honeypot", "event_type")


def line_to_event(line: str) -> Optional[Event]:
    """Parse one JSONL line. Returns None for blank lines; raises ValueError on malformed input (counted as skipped by the caller)."""
    line = line.strip()
    if not line:
        return None
    try:
        obj = json.loads(line)
    except json.JSONDecodeError as e:
        raise ValueError(f"not valid JSON: {e}") from e
    if not isinstance(obj, dict):
        raise ValueError("top-level JSON must be an object")

    missing = [k for k in REQUIRED if k not in obj or obj[k] in (None, "")]
    if missing:
        raise ValueError(f"missing required fields: {missing}")

    raw = obj.get("raw")
    payload_hash = obj.get("payload_hash") or ""
    if not payload_hash and raw:
        payload_hash = hashlib.sha256(str(raw).encode("utf-8")).hexdigest()[:16]

    try:
        ts = parse_iso(str(obj["ts"]))
    except ValueError as e:
        raise ValueError(f"cannot parse ts: {obj['ts']!r}") from e

    def _int(key: str) -> Optional[int]:
        v = obj.get(key)
        if v is None or v == "":
            return None
        return int(v)

    return Event(
        ts=ts,
        src_ip=str(obj["src_ip"]),
        dst_ip=str(obj["dst_ip"]),
        honeypot=str(obj["honeypot"]),
        event_type=str(obj["event_type"]),
        src_port=_int("src_port"),
        dst_port=_int("dst_port"),
        payload_hash=payload_hash or None,
        raw=raw,
    )
