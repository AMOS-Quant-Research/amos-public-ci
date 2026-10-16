"""Public synthetic-only risk mathematics checks; no private AMOS imports."""
import unittest


def drawdown_from_equity(equity, initial):
    peak = initial
    worst_amount = 0.0
    worst_pct = 0.0
    for value in equity:
        peak = max(peak, value)
        worst_amount = max(worst_amount, peak - value)
        worst_pct = max(worst_pct, 100 * (peak - value) / peak)
    return worst_amount, worst_pct


class PublicRiskMathTests(unittest.TestCase):
    def test_peak_to_trough_floating_dd(self):
        amount, pct = drawdown_from_equity([110, 99, 120], 100)
        self.assertEqual(amount, 11)
        self.assertEqual(pct, 10)

    def test_margin_level_formula(self):
        equity, used_margin = 99, 20
        self.assertEqual(100 * equity / used_margin, 495)

    def test_synthetic_mae_mfe(self):
        unrealized_pnl = [0, -5, 8, 3]
        self.assertEqual(min(unrealized_pnl), -5)
        self.assertEqual(max(unrealized_pnl), 8)

    def test_drawdown_percent_is_peak_relative(self):
        amount, pct = drawdown_from_equity([150, 120], 100)
        self.assertEqual(amount, 30)
        self.assertEqual(pct, 20)


if __name__ == "__main__":
    unittest.main()
