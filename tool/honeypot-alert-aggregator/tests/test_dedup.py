"""Dedup logic unit tests: pure function, using synthetic time series."""
import unittest
from datetime import datetime, timezone

from hpa.dedup import Deduper


def t(iso: str) -> datetime:
    return datetime.fromisoformat(iso).replace(tzinfo=timezone.utc)


class TestDedup(unittest.TestCase):
    def test_same_key_within_window_is_duplicate(self):
        d = Deduper(window_seconds=300)
        self.assertFalse(d.is_duplicate("k1", t("2026-02-01T12:34:56+00:00")))
        self.assertTrue(d.is_duplicate("k1", t("2026-02-01T12:35:02+00:00")))

    def test_same_key_outside_window_is_new(self):
        d = Deduper(window_seconds=300)
        self.assertFalse(d.is_duplicate("k1", t("2026-02-01T12:34:56+00:00")))
        self.assertFalse(d.is_duplicate("k1", t("2026-02-01T13:02:05+00:00")))

    def test_different_keys_never_duplicate(self):
        d = Deduper(window_seconds=300)
        self.assertFalse(d.is_duplicate("k1", t("2026-02-01T12:34:56+00:00")))
        self.assertFalse(d.is_duplicate("k2", t("2026-02-01T12:34:57+00:00")))

    def test_seed_from_store_state(self):
        d = Deduper(window_seconds=300)
        d.seed({"k1": t("2026-02-01T12:34:56+00:00")})
        self.assertTrue(d.is_duplicate("k1", t("2026-02-01T12:35:02+00:00")))


if __name__ == "__main__":
    unittest.main()
