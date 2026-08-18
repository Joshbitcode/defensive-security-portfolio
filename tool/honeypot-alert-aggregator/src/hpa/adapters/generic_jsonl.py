"""通用 JSON Lines 适配器：一行一条 JSON 告警。

必填字段：ts, src_ip, dst_ip, honeypot, event_type
可选字段：src_port, dst_port, payload_hash, raw
payload_hash 缺省时，若提供 raw 则取 raw 的 sha256 前 16 位。
"""
from __future__ import annotations

import hashlib
import json
from typing import Optional

from ..models import Event, parse_iso

REQUIRED = ("ts", "src_ip", "dst_ip", "honeypot", "event_type")


def line_to_event(line: str) -> Optional[Event]:
    """解析一行 JSONL。空行返回 None；格式错误抛 ValueError（由调用方计数跳过）。"""
    line = line.strip()
    if not line:
        return None
    try:
        obj = json.loads(line)
    except json.JSONDecodeError as e:
        raise ValueError(f"不是合法 JSON: {e}") from e
    if not isinstance(obj, dict):
        raise ValueError("JSON 顶层必须是对象")

    missing = [k for k in REQUIRED if k not in obj or obj[k] in (None, "")]
    if missing:
        raise ValueError(f"缺少必填字段: {missing}")

    raw = obj.get("raw")
    payload_hash = obj.get("payload_hash") or ""
    if not payload_hash and raw:
        payload_hash = hashlib.sha256(str(raw).encode("utf-8")).hexdigest()[:16]

    try:
        ts = parse_iso(str(obj["ts"]))
    except ValueError as e:
        raise ValueError(f"ts 无法解析: {obj['ts']!r}") from e

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
