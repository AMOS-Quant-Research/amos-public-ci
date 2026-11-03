"""No network, no broker, no credentials required."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from ai_hypothesis_generator import (CONTRACT, heuristic, key, load_ledger,
                                     propose, valid)


class GeneratorTests(unittest.TestCase):
    def test_rejects_code_and_out_of_bounds(self):
        self.assertFalse(valid({"lambda": 0.0, "momentum": 5, "lookback": 80}))
        self.assertFalse(valid({"lambda": 1.0, "momentum": "5", "lookback": 80}))
        self.assertFalse(valid({"lambda": 1.0, "momentum": 5, "lookback": 80, "source": "import os"}))
        self.assertTrue(valid({"lambda": 1.0, "momentum": 5, "lookback": 80}))

    def test_metric_feedback_and_dedup(self):
        ledger = [
            {"plan": {"lambda": 1.0, "momentum": 5, "lookback": 80},
             "returncode": 0, "kpis": {"PF": 2.0, "EV": 5.0, "MaxDD": 80.0}},
            {"plan": {"lambda": 2.0, "momentum": 8, "lookback": 80},
             "returncode": 0, "kpis": {"PF": 1.0, "EV": -1.0, "MaxDD": 140.0}},
        ]
        original = [x["plan"] for x in ledger]
        a = heuristic(ledger, original, 3)
        b = heuristic(ledger, original, 3)
        self.assertEqual(a, b)
        self.assertEqual(len(a), 3)
        self.assertEqual(len({key(x) for x in a}), 3)
        self.assertFalse(set(map(key, a)) & set(map(key, original)))

    def test_checkpointed_proposal_without_nim(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            ledger = d / "ledger.json"
            ledger.write_text(json.dumps({"contract": "amos.ae.autonomous-ledger.v1",
                                          "completed": []}))
            registry = d / "registry.json"
            registry.write_text(json.dumps({"contract": CONTRACT, "candidates": []}))
            output = d / "proposed.json"
            with patch.dict(os.environ, {"NVIDIA_API_KEY": "", "NVIDIA_NIM_MODEL": ""}):
                report = propose(ledger, registry, output, 3)
            self.assertEqual(report["generator"], "metric_guided_deterministic")
            self.assertEqual(report["candidate_count"], 3)
            self.assertEqual(len(json.loads(output.read_text())["candidates"]), 3)
            self.assertFalse(report["promotion_allowed"])
            self.assertFalse(report["live_trading"])


if __name__ == "__main__":
    unittest.main()
