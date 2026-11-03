import unittest
from research.dagram.real_bt_gate import inspect_evidence


class RealBtGateTests(unittest.TestCase):
    def test_no_updates_blocks_profitability(self):
        out = inspect_evidence([{"event_type":"hello", "first_seen_update":False}],
                               "2026-07-27T00:00:00Z","2026-07-27T23:59:59Z")
        self.assertEqual(out["status"], "BLOCKED")
        self.assertIsNone(out["pf"])
        self.assertEqual(out["reason"], "NO_REAL_PUBLICATION_UPDATES")

    def test_update_without_server_issuance_blocks(self):
        out = inspect_evidence([{"event_type":"pub", "first_seen_update":True,
                                 "observed_at":"2026-10-29T01:00:00Z",
                                 "issued_at_verified":False}],
                               "2026-10-29T00:00:00Z","2026-10-30T00:00:00Z")
        self.assertEqual(out["reason"], "ISSUANCE_TIMESTAMPS_UNVERIFIED")

    def test_mismatched_tick_day_blocks(self):
        out = inspect_evidence([{"event_type":"pub", "first_seen_update":True,
                                 "issued_at":"2026-10-29T01:00:00Z",
                                 "issued_at_verified":True}],
                               "2026-07-27T00:00:00Z","2026-07-27T23:59:59Z")
        self.assertEqual(out["reason"], "NO_CONTEMPORANEOUS_RAW_TICKS")


if __name__ == "__main__":
    unittest.main()
