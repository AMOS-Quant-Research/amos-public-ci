import unittest
from decimal import Decimal
import json
import sys
import tempfile
from pathlib import Path

from modules.vibe_xauusd_gateway import execute_research_pipeline, prepare_research_run


def proposal(**overrides):
    data = {"proposal_id": "vt-001", "symbol": "XAUUSD", "strategy_path": "strategies/vt_001.py",
            "source": "vibe-trading", "live_trading": False}
    data.update(overrides)
    return data


def cost(**overrides):
    data = {"symbol": "XAUUSD", "commission_per_lot_usd": "7", "slippage_points_per_side": "2",
            "point_size": "0.01", "contract_size": "100", "margin_rate": "0.005", "max_leverage": "2000"}
    data.update(overrides)
    return data


def ticks(count=3):
    return [{"ts_ns": 1_700_000_000_000_000_000 + i, "bid": "2300.00", "ask": "2300.05"}
            for i in range(count)]


def math_hypothesis(**overrides):
    data = {
        "hypothesis_id": "ae-expected-value-001",
        "source_refs": ["doi:10.0000/example"],
        "mathematical_claim": "Conditional expected value remains positive after costs.",
        "economic_rationale": "The signal captures a liquidity transition.",
        "falsifiers": ["OOS EV is non-positive", "cost-adjusted PF is below one"],
        "code_ref": "strategies/ae_ev_001.py",
        "unit_test_refs": ["tests/test_ae_ev_001.py"],
        "train_end": "2025-01-01",
        "oos_start": "2025-01-02",
    }
    data.update(overrides)
    return data


class VibeXauusdGatewayTest(unittest.TestCase):
    def test_accepts_bid_ask_ticks_and_exposes_cost_and_margin(self):
        result = prepare_research_run(proposal(), cost(), ticks(), "0.01", min_ticks=3)
        self.assertTrue(result.accepted)
        self.assertEqual(result.reason, "PREFLIGHT_PASSED_NOT_A_BACKTEST")
        self.assertEqual(result.tick_count, 3)
        self.assertEqual(result.estimated_round_turn_cost_usd, Decimal("0.11"))
        self.assertEqual(result.initial_margin_usd, Decimal("11.50025"))

    def test_rejects_crossed_market(self):
        bad = ticks()
        bad[1]["ask"] = "2299.99"
        result = prepare_research_run(proposal(), cost(), bad, "0.01", min_ticks=3)
        self.assertFalse(result.accepted)
        self.assertIn("ask must be greater", result.reason)

    def test_rejects_duplicate_timestamp(self):
        bad = ticks()
        bad[1]["ts_ns"] = bad[0]["ts_ns"]
        result = prepare_research_run(proposal(), cost(), bad, "0.01", min_ticks=3)
        self.assertFalse(result.accepted)
        self.assertIn("strictly increasing", result.reason)

    def test_rejects_live_trading(self):
        result = prepare_research_run(proposal(live_trading=True), cost(), ticks(), "0.01", min_ticks=3)
        self.assertFalse(result.accepted)
        self.assertIn("live_trading", result.reason)

    def test_rejects_too_few_ticks(self):
        result = prepare_research_run(proposal(), cost(), ticks(2), "0.01", min_ticks=3)
        self.assertFalse(result.accepted)
        self.assertIn("insufficient raw ticks", result.reason)

    def test_pipeline_emits_non_live_risk_candidate_only_with_measured_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            driver = root / "driver.py"
            driver.write_text(
                "import argparse, json\n"
                "p=argparse.ArgumentParser(); p.add_argument('--amos-request'); p.add_argument('--amos-evidence'); a=p.parse_args()\n"
                "json.dump({'contract':'amos.vibe.measured-evidence.v1','live_trading':False,"
                "'engine':'NautilusTrader BacktestEngine','ohlc_resample_used':False,'raw_ticks':3,"
                "'native_fills':2,'kpis':{'PF':1.2,'EV':2,'MaxDD':3,'MAE':4,'MFE':5}},open(a.amos_evidence,'w'))\n",
                encoding="utf-8",
            )
            output = execute_research_pipeline(
                proposal(), cost(), ticks(), "0.01", [sys.executable, str(driver)], root, min_ticks=3)
            self.assertEqual(output["status"], "CANDIDATE_FOR_RISK_GOVERNOR")
            self.assertFalse(output["live_trading"])
            self.assertTrue((root / "request.json").exists())
            self.assertTrue((root / "risk_governor_candidate.json").exists())

    def test_pipeline_rejects_proxy_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            driver = root / "driver.py"
            driver.write_text(
                "import argparse, json\n"
                "p=argparse.ArgumentParser(); p.add_argument('--amos-request'); p.add_argument('--amos-evidence'); a=p.parse_args()\n"
                "json.dump({'contract':'amos.vibe.measured-evidence.v1','live_trading':False,"
                "'engine':'NautilusTrader BacktestEngine','ohlc_resample_used':True,'raw_ticks':3,"
                "'native_fills':2,'kpis':{'PF':1.2,'EV':2,'MaxDD':3,'MAE':4,'MFE':5}},open(a.amos_evidence,'w'))\n",
                encoding="utf-8",
            )
            output = execute_research_pipeline(
                proposal(), cost(), ticks(), "0.01", [sys.executable, str(driver)], root, min_ticks=3)
            self.assertEqual(output["status"], "REJECTED")
            self.assertEqual(output["reason"], "RAW_BIDASK_EVIDENCE_REQUIRED")

    def test_math_edge_requires_oos_wfo_and_monte_carlo_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            driver = root / "driver.py"
            driver.write_text(
                "import argparse, json\n"
                "p=argparse.ArgumentParser(); p.add_argument('--amos-request'); p.add_argument('--amos-evidence'); a=p.parse_args()\n"
                "json.dump({'contract':'amos.vibe.measured-evidence.v1','live_trading':False,"
                "'engine':'NautilusTrader BacktestEngine','ohlc_resample_used':False,'raw_ticks':3,'native_fills':2,"
                "'kpis':{'PF':1.2,'EV':2,'MaxDD':3,'MAE':4,'MFE':5},'math_validation':{"
                "'oos':{'status':'PASS','artifact':'oos.json','run_id':'oos-1'},"
                "'wfo':{'status':'PASS','artifact':'wfo.json','run_id':'wfo-1'},"
                "'monte_carlo':{'status':'PASS','artifact':'mc.json','run_id':'mc-1'}}},open(a.amos_evidence,'w'))\n",
                encoding="utf-8",
            )
            output = execute_research_pipeline(proposal(), cost(), ticks(), "0.01", [sys.executable, str(driver)],
                                               root, min_ticks=3, math_hypothesis=math_hypothesis())
            self.assertEqual(output["status"], "CANDIDATE_FOR_RISK_GOVERNOR")
            request = json.loads((root / "request.json").read_text(encoding="utf-8"))
            self.assertEqual(request["math_edge_hypothesis"]["hypothesis_id"], "ae-expected-value-001")

    def test_math_edge_rejects_missing_monte_carlo_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            driver = root / "driver.py"
            driver.write_text(
                "import argparse, json\n"
                "p=argparse.ArgumentParser(); p.add_argument('--amos-request'); p.add_argument('--amos-evidence'); a=p.parse_args()\n"
                "json.dump({'contract':'amos.vibe.measured-evidence.v1','live_trading':False,"
                "'engine':'NautilusTrader BacktestEngine','ohlc_resample_used':False,'raw_ticks':3,'native_fills':2,"
                "'kpis':{'PF':1.2,'EV':2,'MaxDD':3,'MAE':4,'MFE':5},'math_validation':{"
                "'oos':{'status':'PASS','artifact':'oos.json','run_id':'oos-1'},"
                "'wfo':{'status':'PASS','artifact':'wfo.json','run_id':'wfo-1'}}},open(a.amos_evidence,'w'))\n",
                encoding="utf-8",
            )
            output = execute_research_pipeline(proposal(), cost(), ticks(), "0.01", [sys.executable, str(driver)],
                                               root, min_ticks=3, math_hypothesis=math_hypothesis())
            self.assertEqual(output["status"], "REJECTED")
            self.assertEqual(output["reason"], "MATH_MONTE_CARLO_EVIDENCE_REQUIRED")
