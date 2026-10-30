import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent

class OvernightDriftContractTests(unittest.TestCase):
    def test_strategy_source_is_parseable_and_independent(self):
        source = (ROOT / "tradebydata_overnight_drift.py").read_text(encoding="utf-8")
        ast.parse(source)
        self.assertIn("not a reconstruction", source)
        self.assertIn("completed M1 bars only", source)
        self.assertIn("return {\"XAUUSD\"", source)

    def test_native_runner_enforces_research_only_evidence(self):
        source = (ROOT / "tradebydata_native_run.py").read_text(encoding="utf-8")
        ast.parse(source)
        self.assertIn("NATIVE_BT_FAILED", source)
        self.assertIn("zero native fills", source)
        self.assertIn("\"live_trading\": False", source)
        self.assertIn("ASSUMPTION_ONLY", source)

if __name__ == "__main__":
    unittest.main()
