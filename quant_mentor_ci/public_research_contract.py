"""Public, synthetic-only CI contract for Quant Mentor research mathematics.

This is an independent check, not a copy of the private AMOS strategy.
Inputs are deliberately synthetic. No live trading, no private source.
"""
import math
import random


def trade_metrics(pnls, initial_equity=1000.0):
    if not pnls or not math.isfinite(initial_equity) or initial_equity <= 0:
        raise ValueError("Nonempty PnL and positive initial equity required")
    equity = peak = float(initial_equity)
    dd = 0.0
    gains = losses = 0.0
    for value in pnls:
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
            raise ValueError("PnL must be finite")
        gains += max(0.0, value)
        losses += max(0.0, -value)
        equity += value
        peak = max(peak, equity)
        dd = max(dd, (peak - equity) / peak)
        if equity <= 0:
            dd = 1.0
    return {"pnl": sum(pnls), "ending_equity": equity,
            "max_dd_pct": 100.0 * dd,
            "profit_factor": gains / losses if losses else None}


def rolling_oos(pnls, train_size, test_size):
    if train_size < 2 or test_size < 1 or len(pnls) < train_size + test_size:
        raise ValueError("Insufficient data")
    windows = []
    for start in range(0, len(pnls) - train_size - test_size + 1, test_size):
        a, b = start + train_size, start + train_size + test_size
        windows.append({"train": (start, a), "test": (a, b),
                        "test_metrics": trade_metrics(pnls[a:b])})
    return windows


def bootstrap_dd_p95(pnls, samples=100, block=3, seed=42):
    if not pnls or samples < 1 or block < 1:
        raise ValueError("Invalid bootstrap input")
    rng = random.Random(seed)
    dds = []
    for _ in range(samples):
        draw = []
        while len(draw) < len(pnls):
            start = rng.randrange(len(pnls))
            draw.extend(pnls[(start + j) % len(pnls)] for j in range(block))
        dds.append(trade_metrics(draw[:len(pnls)])["max_dd_pct"])
    dds.sort()
    return dds[math.ceil(0.95 * samples) - 1]
