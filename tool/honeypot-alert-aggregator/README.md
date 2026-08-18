# honeypot-alert-aggregator (hpa)

> A defense-oriented utility. **The code is written by the repository owner; this document only provides positioning, design, directory structure, and usage conventions; all example outputs in this document are demo formats, not real run results.**

## Purpose

**Honeypot alert aggregation**: take the alerts reported by multiple honeypot nodes (e.g. cowrie, dionaea, and various low-interaction honeypots), ingest them in one place, and do three things:

1. **Normalize**: raw logs from different honeypots → a unified alert structure;
2. **Deduplicate**: merge duplicate alerts of the same source, type, and payload within a time window (scanners and replay traffic generate a lot of noise);
3. **Aggregate**: summarize by time window / source IP and output summary reports (details, per-source-IP stats, cross-node hit hints).

Typical scenario: an individual or a small team runs 2–5 honeypot nodes, receives hundreds to thousands of alerts a day, and needs to answer three questions fast — **who is hitting me? what are they hitting? which ones deserve my manual review?**

## Tech Stack Choices

| Layer | Choice | Rationale |
|---|---|---|
| Language | Python ≥ 3.10 | Mature ecosystem, simple deployment, same language as the honeypot toolchain |
| CLI | argparse (stdlib) | Zero dependencies |
| Config | TOML (stdlib tomllib, requires Python ≥ 3.11) | Human-readable, machine-writable |
| Storage | sqlite3 (stdlib) | Single file, no service, state survives restarts |
| Dedup / payload summary | hashlib | Payload hash as part of the dedup key |
| Optional enrichment | geoip2 (optional extra) | Kept "optional", not a default dependency |
| Output | text tables / JSON / CSV (stdlib csv, json) | Humans read text, machines consume JSON |

Principle: **stdlib first, heavy dependencies as optional extras**. This tool's value is "correct aggregation logic", not the number of dependencies.

## Directory Structure

```text
honeypot-alert-aggregator/
├── pyproject.toml             # package metadata / entry point
├── README.md                  # this file
├── DESIGN.md                  # design review document
├── config.example.toml        # configuration example
├── samples/
│   └── alerts.jsonl           # sample alerts (synthetic data, not real attack traffic)
├── src/
│   └── hpa/
│       ├── __init__.py
│       ├── __main__.py        # python -m hpa entry point
│       ├── cli.py             # argparse subcommands
│       ├── config.py          # TOML loading and validation
│       ├── models.py          # unified alert structure (dataclass)
│       ├── adapters/          # honeypot-specific formats -> unified structure
│       │   ├── __init__.py
│       │   └── generic_jsonl.py
│       ├── dedup.py           # composite key + time-window dedup (pure functions first)
│       ├── aggregate.py       # time-bucket / per-source-IP aggregation (pure functions first)
│       ├── store.py           # sqlite3 read/write
│       └── report.py          # text/JSON/CSV output
└── tests/
    ├── test_dedup.py          # dedup logic unit tests (sample data)
    └── test_aggregate.py      # aggregation logic unit tests
```

## Usage Examples

The command shapes below are **interface conventions**; concrete behavior is subject to the implementation; example outputs are demo formats.

```bash
# install (optional; after this you can call hpa directly, otherwise use PYTHONPATH=src python -m hpa)
pip install -e .

# ingest one or more alert files (JSON Lines; with no file argument it reads stdin)
python -m hpa ingest samples/alerts.jsonl

# last-24h summary: per source IP, event type, honeypot node
python -m hpa report --last 24 --format text

# explicit time window (useful for looking back at historical alerts)
python -m hpa report --since 2026-02-01T00:00:00Z --until 2026-02-02T00:00:00Z

# export a machine-readable report
python -m hpa report --last 168 --format json -o report.json

# dedup and storage status
python -m hpa status
```

```text
[example output - not a real run]
Report window: 2026-02-01T00:00:00Z ~ 2026-02-02T00:00:00Z
unique events (after dedup): 17   raw events: 1,204

top source IPs:
  203.0.113.42   conn=812  events=3  honeypots=2/3  [ssh-auth, ssh-auth, scp-download]
  198.51.100.7   conn=47   events=1  honeypots=1/3  [http-scan]
```

## Alert Input Format Convention

The unified abstraction layer (`models.py`) field conventions:

```json
{"ts": "2026-02-01T12:34:56Z", "src_ip": "203.0.113.42", "src_port": 48123,
 "dst_ip": "192.0.2.10", "dst_port": 2222, "honeypot": "ssh-01",
 "event_type": "ssh-auth", "payload_hash": "<sha256 prefix, optional>", "raw": "..."}
```

`samples/alerts.jsonl` provides a batch of **synthetic examples** (RFC 5737 documentation address ranges), used only to test the aggregation logic.

## Design Highlights (see DESIGN.md for details)

- Dedup key = `(src_ip, dst_port, honeypot, event_type, payload_hash)` + time window (default 300 s, configurable);
- **Cross-node hit hint**: when the same source IP appears on multiple honeypot nodes, it is automatically flagged as "worth manual review";
- Pure functions first: dedup/aggregation logic does not touch IO, making it easy to unit-test and review.

## Status and Boundaries

- Code is implemented (v0.1, Python ≥ 3.11, stdlib only), unit tests 6/6 passing; the "Verified run output" section below is the real run result over `samples/alerts.jsonl` (synthetic data);
- This tool is a **learning-oriented defensive tool**, not a SIEM/SOAR replacement, and makes no promise of handling large-scale production traffic;
- If ingesting real honeypot data, check local laws and the compliance boundaries of honeypot deployment yourself (deploy only on your own assets).

## Verified Run Output (real test run, input is the synthetic sample)

```text
$ python -m hpa --db tmp-e2e.db ingest samples/alerts.jsonl
ingested: new=4 duplicates=1 skipped=0 (window=300s, db=tmp-e2e.db)

$ python -m hpa --db tmp-e2e.db report --since 2026-02-01T00:00:00Z --until 2026-02-02T00:00:00Z
Report window: 2026-02-01T00:00:00+00:00 ~ 2026-02-02T00:00:00+00:00 (explicit range)
unique events (after dedup): 4   sources: 2

top source IPs:
      203.0.113.42  events=3    honeypots=2  [ssh-authx2, login-attemptx1] [cross-node]
      198.51.100.7  events=1    honeypots=1  [http-scanx1]
```

Interpretation: of 5 raw alerts, 1 was deduplicated by the 300 s window; 203.0.113.42 hit both the ssh-01 and telnet-02 honeypots, was flagged `[cross-node]` and placed on top — exactly the design goal of "who deserves manual review".

## Running Tests

```bash
PYTHONPATH=src python -m unittest discover -s tests -v   # 6 tests, all passing
```
