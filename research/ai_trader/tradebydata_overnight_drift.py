"""Independent overnight-drift hypothesis for XAUUSD raw-tick research.

This is an AMOS-authored candidate inspired only by the public phrase
"Overnight Drift". It is not a reconstruction of Trade By Data's paid strategy.
Signals use completed M1 bars only and return target positions (+1, 0, -1).
"""
from __future__ import annotations
import numpy as np
import pandas as pd

PARAMS = {
    "session_start_utc": 22,
    "session_end_utc": 2,
    "entry_lookback": 20,
    "entry_z": 0.90,
    "fast_ema": 12,
    "slow_ema": 48,
    "atr_period": 14,
    "max_spread_atr": 0.30,
    "stop_atr": 1.20,
    "take_profit_atr": 2.40,
    "max_hold_bars": 150,
}

def _in_session(hour: int, start: int, end: int) -> bool:
    return hour >= start or hour <= end if start > end else start <= hour <= end

class SignalEngine:
    def __init__(self, params=None):
        self.params = dict(PARAMS)
        if params:
            self.params.update(params)

    def generate(self, data):
        bars = data["XAUUSD"].copy()
        required = {"open", "high", "low", "close", "bid", "ask"}
        if not required.issubset(bars.columns):
            raise ValueError("XAUUSD bars must contain OHLC and bid/ask")
        if not bars.index.is_monotonic_increasing:
            raise ValueError("bars must be monotonic")

        p = self.params
        close = bars["close"].astype(float)
        previous = close.shift(1)
        tr = pd.concat(
            [(bars["high"] - bars["low"]).abs(),
             (bars["high"] - previous).abs(),
             (bars["low"] - previous).abs()],
            axis=1,
        ).max(axis=1)
        atr = tr.ewm(alpha=1.0 / p["atr_period"], adjust=False,
                     min_periods=p["atr_period"]).mean()
        fast = close.ewm(span=p["fast_ema"], adjust=False,
                         min_periods=p["fast_ema"]).mean()
        slow = close.ewm(span=p["slow_ema"], adjust=False,
                         min_periods=p["slow_ema"]).mean()
        impulse = close.diff().rolling(p["entry_lookback"]).sum()
        impulse_std = close.diff().rolling(p["entry_lookback"]).std(ddof=0)
        z = impulse / impulse_std.replace(0.0, np.nan)

        result, position, entry, entry_atr, held = [], 0.0, None, None, 0
        warmup = max(p["slow_ema"], p["entry_lookback"], p["atr_period"]) + 1
        for i, (stamp, row) in enumerate(bars.iterrows()):
            if i < warmup or not np.isfinite(atr.iat[i]) or not np.isfinite(z.iat[i]):
                result.append(0.0)
                continue
            ts = pd.Timestamp(stamp)
            if ts.tzinfo is None:
                ts = ts.tz_localize("UTC")
            else:
                ts = ts.tz_convert("UTC")
            active = _in_session(ts.hour, p["session_start_utc"], p["session_end_utc"])
            spread_ok = (float(row["ask"]) - float(row["bid"])) <= float(atr.iat[i]) * p["max_spread_atr"]

            if position == 0.0:
                long_ok = active and spread_ok and z.iat[i] >= p["entry_z"] and fast.iat[i] > slow.iat[i]
                short_ok = active and spread_ok and z.iat[i] <= -p["entry_z"] and fast.iat[i] < slow.iat[i]
                if long_ok or short_ok:
                    position = 1.0 if long_ok else -1.0
                    entry, entry_atr, held = float(close.iat[i]), float(atr.iat[i]), 0
            else:
                held += 1
                stop = entry - position * p["stop_atr"] * entry_atr
                target = entry + position * p["take_profit_atr"] * entry_atr
                crossed_stop = position > 0 and close.iat[i] <= stop or position < 0 and close.iat[i] >= stop
                crossed_target = position > 0 and close.iat[i] >= target or position < 0 and close.iat[i] <= target
                trend_flip = position > 0 and fast.iat[i] < slow.iat[i] or position < 0 and fast.iat[i] > slow.iat[i]
                if (not active) or held >= p["max_hold_bars"] or crossed_stop or crossed_target or trend_flip:
                    position, entry, entry_atr, held = 0.0, None, None, 0
            result.append(position)
        return {"XAUUSD": pd.Series(result, index=bars.index, dtype=float)}
