"""聚合逻辑（纯函数，不碰 IO）：按来源 IP 汇总 + 跨节点标记（见 DESIGN.md §5）。"""
from __future__ import annotations

from .models import Event


def aggregate(events: list[Event], top_n: int = 20) -> dict:
    """把窗口内的事件按来源 IP 聚合，输出报告数据结构。

    指标：事件数（去重后）、事件类型分布、命中蜜罐数、首末出现时间；
    命中蜜罐 >= 2 的来源标记 cross_node，报告里置顶（值得人工关注）。
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
