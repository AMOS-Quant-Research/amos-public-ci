import unittest
from decimal import Decimal

from modules.vibe_xauusd_gateway import prepare_research_run


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
