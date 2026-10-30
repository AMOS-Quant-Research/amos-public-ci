import unittest
from research.potential.analyzer import analyze

def candidate(name):
    return {"id": name, "thesis": "liquidity sweep", "mechanism": "forced liquidation",
        "market": "XAUUSD", "timeframe": "M1", "entry": "MSS after sweep",
        "exit": "stop or target", "execution": "bid/ask market",
        "data": {"source": "Dukascopy quote ticks", "bid_ask": True},
        "costs": {"spread": "observed bid/ask", "slippage": "scenario", "commission": "broker schedule"},
        "risk": {"max_loss": "0.5% equity", "stop_rule": "sweep invalidation"},
        "validation": {"oos": "chronological holdout", "wfo": "rolling windows"},
        "signals": ["sweep", "MSS"]}

class TestPotential(unittest.TestCase):
    def test_ready_is_not_profitability(self):
        r = analyze({"contract": "amos.potential.input.v1", "sources": [candidate("A")]})
        self.assertEqual(r["by_source"][0]["verdict"], "READY_FOR_NATIVE_BT")
        self.assertEqual(r["profitability_claim"], "NOT_ASSESSED")
        self.assertFalse(r["native_bt_executed"])
        self.assertEqual(r["order_permission"], "DENIED")
    def test_missing_bid_ask_blocks(self):
        c = candidate("A")
        c["data"]["bid_ask"] = False
        r = analyze({"contract": "amos.potential.input.v1", "sources": [c]})
        self.assertEqual(r["by_source"][0]["verdict"], "BLOCKED")
    def test_confluence_not_claimed(self):
        r = analyze({"contract": "amos.potential.input.v1", "sources": [candidate("A"), candidate("B")],
                     "confluences": [{"id": "pair", "members": ["A", "B"]}]})
        self.assertEqual(r["by_confluence"][0]["simultaneous_execution_interaction"], "NOT_MEASURED")
        self.assertIsNone(r["by_confluence"][0]["correlation"])
    def test_duplicate_ids_rejected(self):
        with self.assertRaises(ValueError):
            analyze({"contract": "amos.potential.input.v1", "sources": [candidate("A"), candidate("A")]})
    def test_no_fabricated_performance(self):
        c = candidate("A")
        c["projected_pf"] = 8
        with self.assertRaises(ValueError):
            analyze({"contract": "amos.potential.input.v1", "sources": [c]})

if __name__ == "__main__":
    unittest.main()
