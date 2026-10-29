import unittest
import numpy as np
import pandas as pd

from video_ma_cross import M1_ATR_TRAIL, Spec, generate_targets


def bars(n=900):
    index = pd.date_range("2025-01-01", periods=n, freq="min", tz="UTC")
    close = 2000 + np.r_[np.linspace(0, -8, n // 3), np.linspace(-8, 12, n - n // 3)]
    return pd.DataFrame({"open": close, "high": close + .2, "low": close - .2, "close": close}, index=index)


class VideoMaCrossTests(unittest.TestCase):
    def test_requires_timezone_aware_bars(self):
        frame = bars().tz_localize(None)
        with self.assertRaises(ValueError):
            generate_targets(frame, Spec(timeframe="1min"))

    def test_cross_targets_are_finite_and_signed(self):
        out = generate_targets(bars(), Spec(timeframe="1min", fast=3, slow=10))
        self.assertTrue(np.isfinite(out).all())
        self.assertTrue(set(out.unique()).issubset({-1.0, 0.0, 1.0}))

    def test_atr_variant_is_parameterized(self):
        out = generate_targets(bars(), M1_ATR_TRAIL)
        self.assertEqual(len(out), 900)


if __name__ == "__main__":
    unittest.main()
