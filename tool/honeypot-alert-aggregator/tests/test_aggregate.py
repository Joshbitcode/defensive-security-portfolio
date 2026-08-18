"""聚合逻辑单测：跨节点标记与排序。"""
import unittest
from datetime import datetime, timezone

from hpa.aggregate import aggregate
from hpa.models import Event


def ev(ip: str, honeypot: str, ts: str, etype: str = "ssh-auth") -> Event:
    return Event(
        ts=datetime.fromisoformat(ts).replace(tzinfo=timezone.utc),
        src_ip=ip,
        dst_ip="192.0.2.10",
        dst_port=2222,
        honeypot=honeypot,
        event_type=etype,
    )


class TestAggregate(unittest.TestCase):
    def test_cross_node_flag_when_two_honeypots_hit(self):
        events = [
            ev("203.0.113.42", "ssh-01", "2026-02-01T12:34:56+00:00"),
            ev("203.0.113.42", "telnet-02", "2026-02-01T12:40:10+00:00", "login-attempt"),
            ev("198.51.100.7", "web-03", "2026-02-01T13:01:44+00:00", "http-scan"),
        ]
        result = aggregate(events)
        self.assertEqual(result["source_count"], 2)
        first = result["sources"][0]
        self.assertEqual(first["src_ip"], "203.0.113.42")  # cross-node 置顶
        self.assertTrue(first["cross_node"])
        self.assertEqual(first["honeypots_hit"], 2)
        self.assertEqual(first["events"], 2)
        self.assertFalse(result["sources"][1]["cross_node"])

    def test_event_type_distribution(self):
        events = [
            ev("203.0.113.42", "ssh-01", "2026-02-01T12:34:56+00:00", "ssh-auth"),
            ev("203.0.113.42", "ssh-01", "2026-02-01T12:35:00+00:00", "ssh-auth"),
            ev("203.0.113.42", "ssh-01", "2026-02-01T12:36:00+00:00", "scp-download"),
        ]
        result = aggregate(events)
        self.assertEqual(result["sources"][0]["event_types"], {"ssh-auth": 2, "scp-download": 1})


if __name__ == "__main__":
    unittest.main()
