import unittest
from research.ai_trader.bridge import from_amos_ai_trader,from_dagram_observation,from_signalhub_research
class BridgeTests(unittest.TestCase):
    def test_amos_to_common_contract(self):
        s={"contract":"amos.ai-trader.research-signal.v1","live_trading":False,
           "action":"BUY","symbol":"XAUUSD","entry":2600,"sl":2590,"tp":2620}
        result=from_amos_ai_trader(s,123456789,"sha256:abc")
        self.assertEqual(result["contract"],"amos.signal.v1")
        self.assertEqual(result["order_permission"],"DENIED")
    def test_dagram_snapshot_rejected(self):
        with self.assertRaises(ValueError):
            from_dagram_observation({"kind":"hello","source_observed":True})
    def test_dagram_missing_price_blocked(self):
        with self.assertRaises(ValueError):
            from_dagram_observation({"kind":"pub","source_observed":True,
                                    "side":"BUY","observed_at_ns":123,"evidence_ref":"e"})
    def test_signalhub_requires_independent_research(self):
        with self.assertRaises(ValueError):
            from_signalhub_research({"origin":"EXTRACTED_BINARY"})
