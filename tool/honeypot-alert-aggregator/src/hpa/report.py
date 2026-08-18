"""报告输出：文本（人看）/ JSON / CSV（机器用）。"""
from __future__ import annotations

import csv
import io
import json


def format_text(result: dict, window_label: str) -> str:
    out = [f"Report window: {window_label}"]
    out.append(
        f"unique events (after dedup): {result['window_events']}   "
        f"sources: {result['source_count']}"
    )
    if not result["sources"]:
        out.append("(no events in window)")
        return "\n".join(out)
    out.append("")
    out.append("top source IPs:")
    for s in result["sources"]:
        flag = " [cross-node]" if s["cross_node"] else ""
        types = ", ".join(f"{t}x{n}" for t, n in s["event_types"].items())
        out.append(
            f"  {s['src_ip']:>16}  events={s['events']:<4} "
            f"honeypots={s['honeypots_hit']}  [{types}]{flag}"
        )
    return "\n".join(out)


def format_json(result: dict) -> str:
    return json.dumps(result, ensure_ascii=False, indent=2)


def format_csv(result: dict) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(
        [
            "src_ip", "events", "honeypots_hit", "cross_node",
            "event_types", "first_seen", "last_seen",
        ]
    )
    for s in result["sources"]:
        w.writerow(
            [
                s["src_ip"],
                s["events"],
                s["honeypots_hit"],
                "yes" if s["cross_node"] else "no",
                " ".join(f"{t}x{n}" for t, n in s["event_types"].items()),
                s["first_seen"],
                s["last_seen"],
            ]
        )
    return buf.getvalue()
