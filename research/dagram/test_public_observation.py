import json
import tempfile
import unittest
from pathlib import Path
from research.dagram.public_observation import normalize_public_events, validate_for_native_bt


class ObservationTests(unittest.TestCase):
    def test_snapshot_blocks_backdating(self):
        with tempfile.TemporaryDirectory() as td:
            rows = normalize_public_events(
                {"sse_events": [{"event": "hello", "publications": [
                    {"tf": "H4", "side": "LONG", "entry": 4068.523, "sl": 4062.073, "tp": 4133.817}]}]},
                "2026-10-29T01:00:00Z", Path(td) / "obs.jsonl")
            self.assertEqual(len(rows), 1)
            self.assertFalse(rows[0]["backtest_eligible"])
            self.assertIsNone(rows[0]["issued_at"])
            self.assertEqual(validate_for_native_bt(rows)["blocked"], 1)
            self.assertEqual(len((Path(td) / "obs.jsonl").read_text().splitlines()), 1)

    def test_actual_public_sell_snapshot_not_a_new_signal(self):
        # Public hello frame observed 2026-10-29 04:51:31 UTC, not an issuance event.
        with tempfile.TemporaryDirectory() as td:
            rows = normalize_public_events({"sse_events": [{
                "event": "hello", "observed_at": "2026-10-29T04:51:31.208541+00:00",
                "publications": [{"tf": "M15", "revision": 3775,
                    "side": "SELL", "time": 1793246400000,
                    "id": "sd8653d356e210f56e6ea",
                    "entry": 4039.6874464285715, "sl": 4046.2874464285715,
                    "tp": 4027.9451804152527}]
            }]}, "2026-10-29T04:52:32Z", Path(td) / "observations.jsonl")
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["side"], "SHORT")
            self.assertEqual(rows[0]["raw_side"], "SELL")
            self.assertEqual(rows[0]["observed_at"], "2026-10-29T04:51:31.208541+00:00")
            self.assertFalse(rows[0]["first_seen_update"])
            self.assertFalse(rows[0]["backtest_eligible"])

    def test_naive_timestamp_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(ValueError):
                normalize_public_events({"sse_events": []}, "2026-10-29T01:00:00", Path(td) / "x")

    def test_no_plans(self):
        self.assertEqual(validate_for_native_bt([])["reason"], "NO_PUBLIC_PLANS")


if __name__ == "__main__":
    unittest.main()
