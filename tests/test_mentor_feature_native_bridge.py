import json
import tempfile
import unittest
from pathlib import Path

from research.mentor_feature_lab.nautilus_quote_label_bridge import label_native_quote_ticks


class _Tick:
    def __init__(self, ts_event, bid, ask):
        self.ts_event = ts_event
        self.bid_price = bid
        self.ask_price = ask


class MentorFeatureNativeBridgeSmokeTests(unittest.TestCase):
    def test_native_quote_ticks_preserve_executable_sides_and_nanoseconds(self):
        ticks = [
            _Tick(1_704_067_200_000_000_001, 100.0, 100.2),
            _Tick(1_704_067_201_000_000_007, 99.7, 99.9),
            _Tick(1_704_067_202_000_000_009, 100.6, 100.8),
        ]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            signals = root / "signals.jsonl"
            signals.write_text(json.dumps({
                "timestamp": "2024-01-01T00:00:00Z", "side": "long",
                "signal_id": "native-quote-long", "sweep": True,
            }) + "\n", encoding="utf-8")
            proof = label_native_quote_ticks(
                raw_ticks=ticks, signals_path=signals,
                labels_path=root / "labels.jsonl",
                evidence_path=root / "evidence.json", default_horizon=2,
            )
            label = json.loads((root / "labels.jsonl").read_text(encoding="utf-8"))
            self.assertEqual(proof["source"], "Nautilus QuoteTick replay")
            self.assertEqual(proof["raw_ticks"], 3)
            self.assertEqual(label["entry_ts_event_ns"], ticks[0].ts_event)
            self.assertEqual(label["exit_ts_event_ns"], ticks[2].ts_event)
            self.assertEqual(label["entry_executable_price"], 100.2)
            self.assertEqual(label["exit_executable_price"], 100.6)
            self.assertEqual(label["mae_price"], 0.5)
            self.assertEqual(label["mfe_price"], 0.4)


if __name__ == "__main__":
    unittest.main()
