import unittest
from datetime import datetime, timezone

from mentor_feature_scorer import Quote, score_signal


class ExecutableSideScoringTests(unittest.TestCase):
    def setUp(self):
        origin = datetime(2026, 1, 1, tzinfo=timezone.utc)
        self.quotes = [
            Quote(origin, 100.0, 100.2),
            Quote(origin.replace(second=1), 99.7, 99.9),
            Quote(origin.replace(second=2), 100.6, 100.8),
        ]

    def test_long_uses_ask_entry_and_bid_exit_for_mae_mfe(self):
        result = score_signal(self.quotes, {"timestamp": "2026-01-01T00:00:00Z", "side": "long", "sweep": True}, 2)
        self.assertAlmostEqual(result["entry_executable_price"], 100.2)
        self.assertAlmostEqual(result["mae_price"], 0.5)
        self.assertAlmostEqual(result["mfe_price"], 0.4)
        self.assertTrue(result["label_positive"])

    def test_short_uses_bid_entry_and_ask_exit(self):
        result = score_signal(self.quotes, {"timestamp": "2026-01-01T00:00:00Z", "side": "short", "target_price_distance": 0.2}, 2)
        self.assertAlmostEqual(result["mae_price"], 0.8)
        self.assertAlmostEqual(result["mfe_price"], 0.1)
        self.assertFalse(result["target_hit"])


if __name__ == "__main__":
    unittest.main()
