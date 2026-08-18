"""Aggregation logic (pure functions, no IO): summarize by source IP + cross-node flagging (see DESIGN.md §5)."""
from __future__ import annotations

from .models import Event


def aggregate(events: list[Event], top_n: int = 20) -> dict:
    """Aggregate events in the window by source IP and output a report data structure.

    Metrics: event count (post-dedup), event-type distribution, honeypots hit,
    first/last occurrence time; sources with honeypots hit >= 2 are flagged
    cross_node and placed on top in the report (worth manual review).
    """
    per_src: dict[str, dict] = {}
    for e in events:
        s = per_src.setdefault(
            e.src_ip,
            {
                "src_ip": e.src_ip,
                "events": 0,
                "event_types": {},
                "honeypots": set(),
                "first_seen": e.ts,
                "last_seen": e.ts,
            },
        )
        s["events"] += 1
        s["event_types"][e.event_type] = s["event_types"].get(e.event_type, 0) + 1
        s["honeypots"].add(e.honeypot)
        if e.ts < s["first_seen"]:
            s["first_seen"] = e.ts
        if e.ts > s["last_seen"]:
            s["last_seen"] = e.ts

    rows = []
    for s in per_src.values():
        rows.append(
            {
                "src_ip": s["src_ip"],
                "events": s["events"],
                "event_types": dict(
                    sorted(s["event_types"].items(), key=lambda kv: -kv[1])
                ),
                "honeypots_hit": len(s["honeypots"]),
                "honeypots": sorted(s["honeypots"]),
                "cross_node": len(s["honeypots"]) >= 2,
                "first_seen": s["first_seen"].isoformat(),
                "last_seen": s["last_seen"].isoformat(),
            }
        )
    rows.sort(key=lambda r: (-int(r["cross_node"]), -r["events"], r["src_ip"]))
    return {
        "window_events": len(events),
        "source_count": len(rows),
        "sources": rows[:top_n],
    }
