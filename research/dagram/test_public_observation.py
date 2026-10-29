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

    def test_naive_timestamp_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(ValueError):
                normalize_public_events({"sse_events": []}, "2026-10-29T01:00:00", Path(td) / "x")

    def test_no_plans(self):
        self.assertEqual(validate_for_native_bt([])["reason"], "NO_PUBLIC_PLANS")


if __name__ == "__main__":
    unittest.main()
