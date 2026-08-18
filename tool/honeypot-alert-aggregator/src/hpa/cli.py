"""命令行入口：ingest / report / status 三个子命令。"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone

from . import __version__
from .adapters.generic_jsonl import line_to_event
from .aggregate import aggregate
from .config import load_settings
from .dedup import Deduper
from .models import parse_iso
from .report import format_csv, format_json, format_text
from .store import Store


def _ingest(args: argparse.Namespace) -> int:
    settings = load_settings()
    window = args.window if args.window is not None else settings.dedup_window_seconds
    store = Store(args.db or settings.store_path)
    deduper = Deduper(window_seconds=window)
    deduper.seed(store.last_seen_by_key())

    new_count = 0
    dup_count = 0
    skip_count = 0

    def handle_line(line: str) -> None:
        nonlocal new_count, dup_count, skip_count
        try:
            event = line_to_event(line)
        except ValueError as e:
            skip_count += 1
            print(f"[skip] {e}", file=sys.stderr)
            return
        if event is None:
            return
        key = event.dedup_key()
        if deduper.is_duplicate(key, event.ts):
            dup_count += 1
        else:
            store.add(event, key)
            new_count += 1

    if args.files:
        for path in args.files:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    handle_line(line)
    else:
        for line in sys.stdin:
            handle_line(line)

    store.close()
    print(
        f"ingested: new={new_count} duplicates={dup_count} skipped={skip_count} "
        f"(window={window}s, db={store.path})"
    )
    return 0


def _report(args: argparse.Namespace) -> int:
    settings = load_settings()
    top_n = args.top if args.top is not None else settings.report_top_n
    store = Store(args.db or settings.store_path)

    now = datetime.now(timezone.utc)
    if args.since is not None:
        since = parse_iso(args.since)
        until = parse_iso(args.until) if args.until is not None else now
        window_label = f"{since.isoformat()} ~ {until.isoformat()} (explicit range)"
    else:
        hours = args.last if args.last is not None else settings.report_window_hours
        since = now - timedelta(hours=hours)
        until = now
        window_label = f"{since.isoformat()} ~ {now.isoformat()} (last {hours}h)"
    events = store.events_since(since, until=until)
    store.close()

    result = aggregate(events, top_n=top_n)

    if args.format == "text":
        output = format_text(result, window_label)
    elif args.format == "json":
        output = format_json(result)
    else:
        output = format_csv(result)

    if args.output:
        with open(args.output, "w", encoding="utf-8", newline="") as f:
            f.write(output)
        print(f"wrote {args.output}")
    else:
        print(output)
    return 0


def _status(args: argparse.Namespace) -> int:
    settings = load_settings()
    store = Store(args.db or settings.store_path)
    c = store.counts()
    store.close()
    print(f"db: {args.db or settings.store_path}")
    print(f"events (after dedup): {c['events']}")
    print(f"distinct sources:     {c['sources']}")
    print(f"distinct honeypots:   {c['honeypots']}")
    print(f"last event:           {c['last_event_ts'] or '-'}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hpa", description="蜜罐告警聚合器：归一化、去重、汇总（防御向学习工具）"
    )
    parser.add_argument("--version", action="version", version=f"hpa {__version__}")
    parser.add_argument(
        "--db", default=None, help="sqlite 数据库路径（默认取配置或 hpa.db）"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_ingest = sub.add_parser("ingest", help="接入 JSONL 告警（文件参数或 stdin）")
    p_ingest.add_argument("files", nargs="*", help="JSONL 文件路径，不给则读 stdin")
    p_ingest.add_argument("--window", type=int, default=None, help="去重窗口秒数（默认 300）")
    p_ingest.set_defaults(func=_ingest)

    p_report = sub.add_parser("report", help="输出时间窗口汇总报告")
    p_report.add_argument("--last", type=int, default=None, help="统计最近 N 小时（默认 24）")
    p_report.add_argument("--since", default=None, help="窗口起点（ISO8601，如 2026-02-01T00:00:00Z）")
    p_report.add_argument("--until", default=None, help="窗口终点（ISO8601，默认当前时间）")
    p_report.add_argument("--top", type=int, default=None, help="展示来源 IP 数量（默认 20）")
    p_report.add_argument(
        "--format", choices=["text", "json", "csv"], default="text", help="输出格式"
    )
    p_report.add_argument("-o", "--output", default=None, help="写入文件而不是 stdout")
    p_report.set_defaults(func=_report)

    p_status = sub.add_parser("status", help="查看存储状态")
    p_status.set_defaults(func=_status)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
