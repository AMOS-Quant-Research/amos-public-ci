import unittest
from datetime import datetime, timedelta, timezone
from research.kronos_fractal.engine import Tick, bars, make_examples, train_and_evaluate
class FractalEngineTest(unittest.TestCase):
    def setUp(self):
        start=datetime(2026,1,1,tzinfo=timezone.utc)
        self.ticks=[Tick(start+timedelta(seconds=i), 2000+i*.002-.01, 2000+i*.002+.01) for i in range(2000)]
    def test_bars_and_no_future_feature(self):
        minute=bars(self.ticks,60); examples=make_examples(minute,horizon_minutes=5)
        self.assertGreater(len(bars(self.ticks,5)),len(minute)); self.assertLess(examples[0]["input_end"],minute[5]["start"])
    def test_oos_report(self):
        report=train_and_evaluate(self.ticks)
        self.assertFalse(report["live_trading"]); self.assertIn("M5",report["forecasts"]); self.assertGreater(report["forecasts"]["M5"]["oos_samples"],0)
if __name__=="__main__": unittest.main()
