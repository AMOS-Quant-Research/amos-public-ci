import unittest
from types import SimpleNamespace
from research.dagram.match_raw_ticks import match_observations


class RawTickMatchTests(unittest.TestCase):
    def test_first_quote_strictly_after_update(self):
        ticks = [SimpleNamespace(ts_event=1_000_000_000, bid_price=1, ask_price=2),
                 SimpleNamespace(ts_event=2_000_000_000, bid_price=2, ask_price=3)]
        obs = [{"event_type": "pub", "first_seen_update": True,
                "observed_at": "1970-01-01T00:00:01Z"}]
        r = match_observations(obs, ticks)
        self.assertEqual(r[0]["quote_ts_ns"], 2_000_000_000)
        self.assertEqual(r[0]["status"], "MATCHED_FORWARD_ONLY")

    def test_hello_snapshot_blocked(self):
        ticks = [SimpleNamespace(ts_event=2_000_000_000, bid_price=1, ask_price=2)]
        r = match_observations([{"event_type": "hello", "first_seen_update": False,
                                "observed_at": "1970-01-01T00:00:01Z"}], ticks)
        self.assertEqual(r[0]["status"], "BLOCKED")

    def test_unavailable_future_tick(self):
        ticks = [SimpleNamespace(ts_event=1_000_000_000, bid_price=1, ask_price=2)]
        r = match_observations([{"event_type": "pub", "first_seen_update": True,
                                "observed_at": "1970-01-01T00:00:01Z"}], ticks)
        self.assertEqual(r[0]["reason"], "NO_LATER_QUOTE_TICK")


if __name__ == "__main__":
    unittest.main()
