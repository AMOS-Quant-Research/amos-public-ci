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


class NautilusQuoteTickBridgeTests(unittest.TestCase):
    def test_labels_exact_native_tick_bid_ask_with_provenance(self):
        ticks = [
            _Tick(1_704_067_200_000_000_000, 100.0, 100.2),
            _Tick(1_704_067_201_000_000_000, 99.7, 99.9),
            _Tick(1_704_067_202_000_000_000, 100.6, 100.8),
        ]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            signals = root / "signals.jsonl"
            signals.write_text(json.dumps({
                "signal_id": "native-long", "timestamp": "2024-01-01T00:00:00Z",
                "side": "long", "sweep": True,
            }) + "\n", encoding="utf-8")
            proof = label_native_quote_ticks(
                raw_ticks=ticks, signals_path=signals,
                labels_path=root / "labels.jsonl", evidence_path=root / "evidence.json",
                default_horizon=2,
            )
            row = json.loads((root / "labels.jsonl").read_text(encoding="utf-8"))
            self.assertEqual(proof["source"], "Nautilus QuoteTick replay")
            self.assertEqual(proof["raw_ticks"], 3)
            self.assertEqual(row["entry_executable_price"], 100.2)
            self.assertEqual(row["exit_executable_price"], 100.6)
            self.assertEqual(row["mae_price"], 0.5)
            self.assertEqual(row["mfe_price"], 0.4)

    def test_rejects_non_monotonic_native_ticks(self):
        with self.assertRaisesRegex(ValueError, "strictly increasing"):
            label_native_quote_ticks(
                raw_ticks=[_Tick(10, 1.0, 1.1), _Tick(10, 1.0, 1.1)],
                signals_path=Path(__file__), labels_path=Path("/tmp/nope"),
                evidence_path=Path("/tmp/nope-evidence"), default_horizon=1,
            )


if __name__ == "__main__":
    unittest.main()
