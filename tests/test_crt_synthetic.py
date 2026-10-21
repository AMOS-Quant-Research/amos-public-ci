"""Public synthetic CRT regression only; no private strategy/data and no KPI claim."""
import unittest
from datetime import datetime, timedelta, timezone

def crt_signal(prev, current):
    bullish = current[2] < prev[2] and prev[2] < current[3] < prev[1]
    bearish = current[1] > prev[1] and prev[2] < current[3] < prev[1]
    if bullish == bearish:
        return None
    return "BUY" if bullish else "SELL"

class CRTSyntheticTest(unittest.TestCase):
    def test_bullish_sweep(self):
        self.assertEqual(crt_signal((100, 110, 95, 102), (102, 108, 94, 104)), "BUY")

    def test_bearish_sweep(self):
        self.assertEqual(crt_signal((100, 110, 95, 102), (102, 111, 97, 104)), "SELL")

    def test_no_sweep(self):
        self.assertIsNone(crt_signal((100, 110, 95, 102), (102, 109, 96, 104)))

    def test_double_sweep_ambiguous(self):
        self.assertIsNone(crt_signal((100, 110, 95, 102), (102, 111, 94, 104)))

if __name__ == "__main__":
    unittest.main()
