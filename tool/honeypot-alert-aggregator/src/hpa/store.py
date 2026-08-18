"""sqlite3 storage layer: the only module that touches IO (see DESIGN.md §4)."""
from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

from .models import Event, parse_iso

SCHEMA_VERSION = "1"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY,
  ts TEXT NOT NULL,               -- UTC ISO8601; lexicographic order equals time order
  src_ip TEXT NOT NULL,
  src_port INTEGER,
  dst_ip TEXT NOT NULL,
  dst_port INTEGER,
  honeypot TEXT NOT NULL,
  event_type TEXT NOT NULL,
  payload_hash TEXT,
  dedup_key TEXT NOT NULL,
  raw TEXT
);
CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts);
CREATE INDEX IF NOT EXISTS idx_events_dedup ON events(dedup_key, ts);
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
"""


class Store:
    def __init__(self, path: str | Path):
        self.path = str(path)
        self.conn = sqlite3.connect(self.path)
        self.conn.executescript(_SCHEMA)
        cur = self.conn.execute("SELECT value FROM meta WHERE key='schema_version'")
        row = cur.fetchone()
        if row is None:
            with self.conn:
                self.conn.execute(
                    "INSERT INTO meta (key, value) VALUES ('schema_version', ?)",
                    (SCHEMA_VERSION,),
                )

    def add(self, event: Event, key: str) -> None:
        with self.conn:
            self.conn.execute(
                """INSERT INTO events
                   (ts, src_ip, src_port, dst_ip, dst_port, honeypot,
                    event_type, payload_hash, dedup_key, raw)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (
                    event.ts.isoformat(),
                    event.src_ip,
                    event.src_port,
                    event.dst_ip,
                    event.dst_port,
                    event.honeypot,
                    event.event_type,
                    event.payload_hash,
                    key,
                    event.raw,
                ),
            )

    def last_seen_by_key(self) -> dict[str, datetime]:
        rows = self.conn.execute(
            "SELECT dedup_key, MAX(ts) FROM events GROUP BY dedup_key"
        ).fetchall()
        return {k: parse_iso(v) for k, v in rows}

    def events_since(self, since: datetime, until: datetime | None = None) -> list[Event]:
        if until is None:
            rows = self.conn.execute(
                """SELECT ts, src_ip, src_port, dst_ip, dst_port, honeypot,
                          event_type, payload_hash, raw
                   FROM events WHERE ts >= ? ORDER BY ts""",
                (since.isoformat(),),
            ).fetchall()
        else:
            rows = self.conn.execute(
                """SELECT ts, src_ip, src_port, dst_ip, dst_port, honeypot,
                          event_type, payload_hash, raw
                   FROM events WHERE ts >= ? AND ts <= ? ORDER BY ts""",
                (since.isoformat(), until.isoformat()),
            ).fetchall()
        return [
            Event(
                ts=parse_iso(r[0]),
                src_ip=r[1],
                src_port=r[2],
                dst_ip=r[3],
                dst_port=r[4],
                honeypot=r[5],
                event_type=r[6],
                payload_hash=r[7],
                raw=r[8],
            )
            for r in rows
        ]

    def counts(self) -> dict:
        events = self.conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        sources = self.conn.execute(
            "SELECT COUNT(DISTINCT src_ip) FROM events"
        ).fetchone()[0]
        honeypots = self.conn.execute(
            "SELECT COUNT(DISTINCT honeypot) FROM events"
        ).fetchone()[0]
        last = self.conn.execute("SELECT MAX(ts) FROM events").fetchone()[0]
        return {
            "events": events,
            "sources": sources,
            "honeypots": honeypots,
            "last_event_ts": last,
        }

    def close(self) -> None:
        self.conn.close()
