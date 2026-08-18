# DESIGN.md — Honeypot Alert Aggregator Design Review

> Purpose: write down the key decisions before coding so the implementation phase has less rework. This document is for code reviewers and future me.

## 1. Requirements and Non-Goals

**Requirements (Must)**

1. Accept alerts from multiple sources (JSON Lines input, extensible adapters), normalize into a unified structure;
2. Time-window deduplication: merge duplicate alerts of the same source, type, and payload;
3. Time-bucket aggregation: hourly/daily summaries; per source IP count connections, event-type distribution, and honeypots hit;
4. Output three formats: text (for humans), JSON/CSV (for machines);
5. Persist state to a single sqlite3 file, no loss across restarts.

**Non-Goals (Not now)**

- No real-time stream processing (batch ingest/report first);
- No SIEM integration (e.g. Elasticsearch/Splunk); only output standard formats to leave an interface;
- No automatic alert response (blocking, firewall orchestration) — that's SOAR territory;
- No built-in weaponization detection rule base (aggregation first, detection rules left for later).

## 2. Data Flow

```text
honeypot logs ──► adapter ──► unified alert (models) ──► dedup
                                                        │
report ◄── aggregate ◄── store (sqlite3) ◄───────────────┘
```

- **Adapter**: only responsible for "translation", not judgment; a new honeypot type = a new adapter file.
- **Dedup**: stateless pure function; takes a unified alert stream, outputs "is this a new event".
- **Aggregate**: pure function; reads a batch of events, outputs a stats structure; the report command decides the window.
- **Storage**: the only module with IO; schema in §4.

## 3. Dedup Design (this tool's core decision)

### 3.1 Composite Key

```text
dedup_key = sha256(src_ip | dst_port | honeypot | event_type | payload_hash)[:16]
```

- **Why include payload_hash**: scanners/worms repeatedly replay the same payload against the same port; deduplicating only on the five-tuple would treat this noise as new events; the payload hash makes "the same behavior" actually merge.
- **Why include honeypot**: the same behavior hitting two nodes is two nodes' separate observations; dedup does not cross nodes (cross-node is instead highlighted at the aggregation layer).
- **No time**: time is handled by the window mechanism; the key itself is time-independent.

### 3.2 Time Window

- Default fixed window 300 s (configurable); the implementation records "the event's last occurrence time" and uses **last-seen + TTL with expiry** rather than strict sliding-window counting: simpler to implement, bounded memory, and it also merges "scans that last a few minutes".
- Trade-off note: a strict sliding window (e.g. exact 5-minute counting) would need to retain all events in the window, which brings little benefit in the batch ingest scenario, so it's not done.

## 4. Storage Schema (sqlite3)

```sql
CREATE TABLE events (
  id INTEGER PRIMARY KEY,
  ts TEXT NOT NULL,               -- ISO8601 UTC
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
CREATE INDEX idx_events_ts ON events(ts);
CREATE INDEX idx_events_dedup ON events(dedup_key, ts);
CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT);  -- schema version etc.
```

Design point: `raw` keeps the original line, ensuring any aggregation conclusion can be traced back to the original alert (the source of verifiability).

## 5. Aggregation Rules

1. **Time buckets**: UTC hour buckets and day buckets, avoiding local timezone ambiguity;
2. **Per-source-IP metrics**: post-dedup event count, event-type distribution, honeypots hit, first/last occurrence time (the implementation does not collect connection-level counts, to avoid state bloat);
3. **Cross-node hit hint**: source IPs with `honeypots_hit ≥ 2` are placed on top and flagged `[cross-node]` in the report — the same source scanning multiple honeypots at once is usually a signal worth manual review;
4. **Output ordering**: cross-node flag first, then event count descending.

## 6. Configuration (config.example.toml)

```toml
[dedup]
window_seconds = 300

[store]
path = "hpa.db"

[report]
default_window_hours = 24
top_n = 20
```

## 7. Test Strategy

- **Pure-function unit tests first**: dedup and aggregate don't depend on IO, build cases from `samples/alerts.jsonl` (e.g. two alerts with the same key → 1 new event; same source across nodes → flagged cross-node);
- **CLI smoke test**: ingest the sample file → report output is non-empty and well-formed (JSON parses);
- **Not doing**: real honeypot traffic testing (the deployment environment doesn't have it, and it's outside this document's promises).

## 8. Evolution Roadmap (recorded, not promised)

1. More adapters: cowrie JSON, dionaea report format;
2. Optional geoip2 enrichment (source IP geo info, annotation only, not part of dedup);
3. Webhook output (immediate push of new events);
4. Rule engine: simple detection rules based on event type/frequency (e.g. "same IP with ≥ 50 ssh-auth failures in 5 minutes").

## 8.5 Implementation Notes (added after v0.1 landed)

- Timestamps are always parsed to UTC and stored as ISO8601 strings, so lexicographic order equals time order;
- `report` supports `--since/--until` explicit windows (`--last` kept as a shortcut);
- Python ≥ 3.11 required (config parsing uses stdlib tomllib);
- The only deviation from this document in the implementation: §5's "connection count" landed as "post-dedup event count", already noted in §5.

## 9. Review Conclusion

- The design trade-offs are sound: stdlib first, pure-function core, sqlite persistence — suitable as a first version of a learning-oriented defensive tool;
- The part that needs the most careful implementation is the **dedup key and window semantics** (§3) — it determines whether the tool's output is "quiet enough and won't miss a real signal";
- Clear boundary: this tool only does aggregation and presentation, does not replace a SIEM, and promises no production-scale performance.
