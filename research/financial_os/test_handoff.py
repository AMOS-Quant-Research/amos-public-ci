import unittest
from research.financial_os.handoff import evaluate


class HandoffTests(unittest.TestCase):
    def test_missing_evidence_blocks(self):
        r = evaluate({"strategy_id": "candidate-a"}, {"strategy_id": "candidate-a"})
        self.assertEqual(r["status"], "BLOCKED")
        self.assertFalse(r["deployment_approved"])

    def test_synthetic_never_promoted(self):
        ev = dict(strategy_id="a", hypothesis="test", parameter_set={"x": 1},
                  dataset_sha256="a"*64, raw_tick_count=2000, native_fill_count=2,
                  oos_evidence={"run": 1}, cost_calibration={"spread": 1},
                  risk_evidence={"dd": 1}, reproducibility_evidence={"sha": "abc"},
                  pf=1.5, win_rate=0.5, max_dd=0.1, synthetic=True,
                  source_kind="SYNTHETIC_FIXTURE", live_trading=False)
        r = evaluate({"strategy_id": "a"}, ev)
        self.assertEqual(r["status"], "BLOCKED")
        self.assertIn("synthetic_false", r["missing_or_invalid"])

    def test_real_evidence_still_not_deployment_approval(self):
        ev = dict(strategy_id="a", hypothesis="test", parameter_set={"x": 1},
                  dataset_sha256="a"*64, raw_tick_count=2000, native_fill_count=2,
                  oos_evidence={"run": 1}, cost_calibration={"spread": 1},
                  risk_evidence={"dd": 1}, reproducibility_evidence={"sha": "abc"},
                  pf=1.5, win_rate=0.5, max_dd=0.1, synthetic=False,
                  source_kind="REAL_SIGNALS_REAL_RAW_TICKS", live_trading=False)
        r = evaluate({"strategy_id": "a"}, ev)
        self.assertEqual(r["status"], "RESEARCH_EVIDENCE_READY")
        self.assertFalse(r["edge_library_promotion"])
        self.assertFalse(r["deployment_approved"])
