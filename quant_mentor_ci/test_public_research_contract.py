import unittest
from public_research_contract import trade_metrics, rolling_oos, bootstrap_dd_p95


class PublicResearchContracts(unittest.TestCase):
    def test_net_pnl_and_pf(self):
        m = trade_metrics([10, -5, 1], initial_equity=100)
        self.assertEqual(m["pnl"], 6)
        self.assertAlmostEqual(m["profit_factor"], 11 / 5)

    def test_drawdown(self):
        m = trade_metrics([10, -20], initial_equity=100)
        self.assertAlmostEqual(m["max_dd_pct"], 100 * 20 / 110)

    def test_oos_nonoverlap(self):
        folds = rolling_oos([1, 2, 3, 4, 5, 6, 7, 8], 2, 2)
        self.assertEqual([x["test"] for x in folds], [(2, 4), (4, 6), (6, 8)])

    def test_mc_repeatable(self):
        sample = [2, -1, 3, -4, 1, 2]
        self.assertEqual(bootstrap_dd_p95(sample), bootstrap_dd_p95(sample))

    def test_broken_pnl_rejected(self):
        with self.assertRaises(ValueError):
            trade_metrics([1, float("nan")])


if __name__ == "__main__":
    unittest.main()
