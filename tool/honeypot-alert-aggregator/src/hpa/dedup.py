"""时间窗口去重：last-seen + TTL（见 DESIGN.md §3）。

同一 dedup_key 在窗口内（前后两个方向都算）只保留第一条，重复的刷新
last-seen，实现"带过期的滑动窗口"效果，对持续几分钟的扫描也能合并。
"""
from __future__ import annotations

from datetime import datetime, timedelta


class Deduper:
    def __init__(self, window_seconds: int = 300):
        self.window = timedelta(seconds=window_seconds)
        self._last_seen: dict[str, datetime] = {}

    def seed(self, last_seen: dict[str, datetime]) -> None:
        """用数据库里已有的 last-seen 状态初始化（重启后不丢去重状态）。"""
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
