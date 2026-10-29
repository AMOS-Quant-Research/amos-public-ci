import unittest
from research.financial_os.coreai_intake import build

class CoreAIIntakeTests(unittest.TestCase):
    def test_missing_native_evidence_blocks_and_never_delivers(self):
        result=build({"strategy_id":"a"},{"strategy_id":"a","pf":99})
        self.assertEqual(result["intake_status"],"BLOCKED")
        self.assertIsNone(result["metrics"]["pf"])
        self.assertEqual(result["delivery_status"],"NOT_DELIVERED")
        self.assertFalse(result["coreai_acknowledged"])
        self.assertEqual(result["order_permission"],"DENIED")
    def test_valid_evidence_produces_handoff_not_approval(self):
        ev=dict(strategy_id="a",hypothesis="test",parameter_set={"x":1},
                dataset_sha256="a"*64,raw_tick_count=2000,native_fill_count=2,
                oos_evidence={"run":1},cost_calibration={"spread":1},
                risk_evidence={"dd":1},reproducibility_evidence={"sha":"abc"},
                pf=1.5,win_rate=.5,max_dd=.1,synthetic=False,
                source_kind="REAL_SIGNALS_REAL_RAW_TICKS",live_trading=False)
        result=build({"strategy_id":"a"},ev)
        self.assertEqual(result["intake_status"],"READY_FOR_COREAI_INTAKE")
        self.assertEqual(result["delivery_status"],"NOT_DELIVERED")
        self.assertFalse(result["risk_governor_approval"])
        self.assertEqual(result["order_permission"],"DENIED")
        self.assertEqual(result["content_sha256"],build({"strategy_id":"a"},ev)["content_sha256"])
