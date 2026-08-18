"""Config loading: config.toml (optional) overrides defaults; CLI args override the config in turn."""
from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

DEFAULTS = {
    "dedup_window_seconds": 300,
    "store_path": "hpa.db",
    "report_window_hours": 24,
    "report_top_n": 20,
}


@dataclass
class Settings:
    dedup_window_seconds: int = DEFAULTS["dedup_window_seconds"]
    store_path: str = DEFAULTS["store_path"]
    report_window_hours: int = DEFAULTS["report_window_hours"]
    report_top_n: int = DEFAULTS["report_top_n"]


def load_settings(path: str | Path = "config.toml") -> Settings:
    """Use defaults when config.toml is absent; otherwise read the [dedup]/[store]/[report] sections."""
    s = Settings()
    p = Path(path)
    if not p.is_file():
        return s
    with p.open("rb") as f:
        data = tomllib.load(f)
    dedup = data.get("dedup", {})
    store = data.get("store", {})
    report = data.get("report", {})
    if "window_seconds" in dedup:
        s.dedup_window_seconds = int(dedup["window_seconds"])
    if "path" in store:
        s.store_path = str(store["path"])
    if "default_window_hours" in report:
        s.report_window_hours = int(report["default_window_hours"])
    if "top_n" in report:
        s.report_top_n = int(report["top_n"])
    return s
