"""Time-window dedup: last-seen + TTL (see DESIGN.md §3).

Within the window (in both directions), only the first occurrence of the same
dedup_key is kept; duplicates refresh last-seen, producing an "expiring sliding
window" effect that also merges scans lasting a few minutes.
"""
from __future__ import annotations

from datetime import datetime, timedelta


class Deduper:
    def __init__(self, window_seconds: int = 300):
        self.window = timedelta(seconds=window_seconds)
        self._last_seen: dict[str, datetime] = {}

    def seed(self, last_seen: dict[str, datetime]) -> None:
        """Initialize from the last-seen state already in the database (so dedup state survives restarts)."""
        self._last_seen.update(last_seen)

    def is_duplicate(self, key: str, ts: datetime) -> bool:
        last = self._last_seen.get(key)
        if last is None:
            self._last_seen[key] = ts
            return False
        if abs((ts - last).total_seconds()) <= self.window.total_seconds():
            if ts > last:
                self._last_seen[key] = ts
            return True
        self._last_seen[key] = ts
        return False
