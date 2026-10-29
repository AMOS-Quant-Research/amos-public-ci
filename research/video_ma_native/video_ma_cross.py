"""Video-faithful MA cross signal logic and its M1 ATR-trail extension.

Signals are calculated strictly from completed bars.  A target published for a
bar is consumed by the Nautilus strategy on the subsequent raw QuoteTick.
"""
from __future__ import annotations

from dataclasses import dataclass
import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Spec:
    timeframe: str
    fast: int = 44
    slow: int = 332
    atr_period: int = 14
    atr_multiple: float = 2.0
    use_atr_trail: bool = False


VIDEO_M5 = Spec(timeframe="5min")
M1_ATR_TRAIL = Spec(timeframe="1min", use_atr_trail=True)


def _atr(frame: pd.DataFrame, period: int) -> pd.Series:
    previous_close = frame["close"].shift(1)
    tr = pd.concat([
        frame["high"] - frame["low"],
        (frame["high"] - previous_close).abs(),
        (frame["low"] - previous_close).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(period, min_periods=period).mean()


def _previous_day_levels(frame: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    day = frame.index.tz_convert("UTC").normalize()
    daily = frame.groupby(day).agg(high=("high", "max"), low=("low", "min"))
    prior = daily.shift(1).rename(columns={"high": "prior_day_high", "low": "prior_day_low"})
    mapped = pd.DataFrame({"day": day}, index=frame.index).join(prior, on="day")
    return mapped["prior_day_high"], mapped["prior_day_low"]


def generate_targets(frame: pd.DataFrame, spec: Spec) -> pd.Series:
    """Return the desired signed exposure after each completed bar.

    Video fidelity: SMA 44/332 close cross; long stop at prior UTC trading-day
    low, short stop at prior UTC trading-day high; after a stop wait for a new
    cross.  The original video does not define its session time zone, so UTC is
    explicitly used and recorded as an assumption.

    Extension: on M1 only, once a position reaches +2R, trail the protective
    stop by ATR(14) * 2.0.  The multiplier is a declared parameter, not claimed
    by the video.
    """
    required = {"open", "high", "low", "close"}
    if not required.issubset(frame.columns):
        raise ValueError(f"missing OHLC columns: {required - set(frame.columns)}")
    if not isinstance(frame.index, pd.DatetimeIndex) or frame.index.tz is None:
        raise ValueError("a timezone-aware UTC DatetimeIndex is required")
    bars = frame.copy().astype(float)
    fast = bars["close"].rolling(spec.fast, min_periods=spec.fast).mean()
    slow = bars["close"].rolling(spec.slow, min_periods=spec.slow).mean()
    cross_up = (fast > slow) & (fast.shift(1) <= slow.shift(1))
    cross_down = (fast < slow) & (fast.shift(1) >= slow.shift(1))
    prior_high, prior_low = _previous_day_levels(bars)
    atr = _atr(bars, spec.atr_period)

    target = pd.Series(0.0, index=bars.index)
    direction = 0
    entry = np.nan
    risk = np.nan
    stop = np.nan
    armed = False

    for i, ts in enumerate(bars.index):
        row = bars.iloc[i]
        # A cross is evaluated only on a completed candle. Its target is passed
        # to the raw-tick executor, which sends the order on the following tick.
        wanted = 1 if bool(cross_up.iloc[i]) else -1 if bool(cross_down.iloc[i]) else 0
        if direction == 0:
            if wanted and np.isfinite(prior_low.iloc[i] if wanted > 0 else prior_high.iloc[i]):
                direction = wanted
                entry = row["close"]
                stop = prior_low.iloc[i] if wanted > 0 else prior_high.iloc[i]
                risk = abs(entry - stop)
                armed = False
        else:
            stopped = (direction > 0 and row["low"] <= stop) or (direction < 0 and row["high"] >= stop)
            if stopped:
                direction = 0
                entry = risk = stop = np.nan
                armed = False
            elif wanted and wanted != direction:
                direction = wanted
                entry = row["close"]
                stop = prior_low.iloc[i] if wanted > 0 else prior_high.iloc[i]
                risk = abs(entry - stop)
                armed = False
            elif spec.use_atr_trail and np.isfinite(risk) and risk > 0:
                favourable = (row["high"] - entry) if direction > 0 else (entry - row["low"])
                if favourable >= 2.0 * risk:
                    armed = True
                if armed and np.isfinite(atr.iloc[i]):
                    candidate = row["close"] - direction * spec.atr_multiple * atr.iloc[i]
                    stop = max(stop, candidate) if direction > 0 else min(stop, candidate)
        target.iloc[i] = float(direction)
    return target


class SignalEngine:
    """Default entry point is deliberately the video-faithful M5 version."""
    def generate(self, data):
        m1 = data["XAUUSD"]
        m5 = m1.resample("5min", label="left", closed="left").agg(
            open=("open", "first"), high=("high", "max"),
            low=("low", "min"), close=("close", "last"), volume=("volume", "sum"),
        ).dropna()
        target_m5 = generate_targets(m5, VIDEO_M5)
        return {"XAUUSD": target_m5.reindex(m1.index, method="ffill").fillna(0.0)}


class M1AtrTrailSignalEngine:
    def generate(self, data):
        return {"XAUUSD": generate_targets(data["XAUUSD"], M1_ATR_TRAIL).fillna(0.0)}
