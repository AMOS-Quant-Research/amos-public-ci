import unittest
from research.ai_trader.engine import minute_bars, features, decide, intake, read_quotes

def sample():
    out=[]
    for i in range(80):
        price=2600+i*.2
        out.append({"minute":i,"open":price-.1,"high":price+.15,"low":price-.15,
                    "close":price,"bid":price-.01,"ask":price+.01,"closed":True})
    return out

class ResearchTraderTests(unittest.TestCase):
    def test_indicators_are_finite(self):
        self.assertTrue(all(__import__("math").isfinite(v) for v in features(sample()).values()))
    def test_deterministic_signal_not_order(self):
        a=decide(sample())
        self.assertEqual(a,decide(sample()))
        self.assertFalse(a["signal_is_order"])
        self.assertFalse(a["live_trading"])
    def test_no_partial_bar(self):
        rows=[]
        for m in range(40):
            rows.append((m*60_000_000_000,2600+m,2600+m+.1))
        self.assertEqual(len(minute_bars(rows)),39)
    def test_coreai_blocked_without_native_proof(self):
        s=decide(sample())
        p={"kind":"REAL_XAUUSD_BID_ASK_QUOTETICKS","sha256":"a"*64,"count":1000}
        e=intake(s,p)
        self.assertEqual(e["status"],"BLOCKED_PENDING_NATIVE_OOS_COST_RISK")
        self.assertEqual(e["delivery_status"],"NOT_DELIVERED")
        self.assertEqual(e["order_permission"],"DENIED")
        with self.assertRaises(ValueError):
            intake(s,{"kind":"SYNTHETIC","sha256":"a","count":1000})
    def test_ai_claim_requires_provenance(self):
        s=decide(sample())
        p={"kind":"REAL_XAUUSD_BID_ASK_QUOTETICKS","sha256":"a"*64,"count":1000}
        with self.assertRaises(ValueError):
            intake(s,p,ai_candidate={"source":"NVIDIA_NIM","parameters":s["parameters"]})
    def test_ready_does_not_mean_delivered_or_approved(self):
        s=decide(sample())
        p={"kind":"REAL_XAUUSD_BID_ASK_QUOTETICKS","sha256":"a"*64,"count":1000}
        n={"native_fills":1,"oos_verified":True,"costs_calibrated":True,"risk_verified":True,"reproducible":True}
        e=intake(s,p,n)
        self.assertEqual(e["status"],"RESEARCH_READY_FOR_COREAI")
        self.assertFalse(e["coreai_acknowledged"])
        self.assertFalse(e["risk_governor_approved"])
