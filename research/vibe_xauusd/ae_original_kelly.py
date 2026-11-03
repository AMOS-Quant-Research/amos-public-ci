"""Risk-Constrained Kelly paper's original finite-support optimization.

maximize sum_i p_i log(1 + f*R_i)
subject to sum_i p_i (1 + f*R_i)^(-lambda) <= 1, 0<=f<=1.
This is the exact *sample-average mathematical constraint/objective*,
NOT a claim of globally optimal continuous solution or validated return model.
Research-only: estimates historical outcomes, never sends broker orders.
"""
import math
import numpy as np
import pandas as pd


def kelly_grid_solve(outcomes, lam=1.0, n_grid=101):
    x = np.asarray(outcomes, dtype=float)
    if x.ndim != 1 or len(x) < 30 or not np.isfinite(x).all() or lam <= 0:
        return 0.0
    if n_grid < 2:
        raise ValueError("n_grid must be >= 2")
    best_f, best_growth = 0.0, 0.0
    for f in np.linspace(0, 1, n_grid):
        wealth = 1 + f * x
        if np.any(wealth <= 0):
            continue
        moment = float(np.mean(np.power(wealth, -lam)))
        if moment > 1.0 + 1e-10:
            continue
        growth = float(np.mean(np.log(wealth)))
        if growth > best_growth + 1e-12:
            best_f, best_growth = float(f), growth
    return best_f


class SignalEngine:
    def generate(self, data):
        bars = data["XAUUSD"]
        mid = bars["close"].astype(float)
        returns = mid.pct_change().replace([np.inf, -np.inf], np.nan).fillna(0.0)
        # Momentum for decision t is known after bar t; executed on next quote.
        momentum = returns.rolling(5, min_periods=5).sum().fillna(0.0)
        direction = np.sign(momentum)
        # The historical outcome at t uses the prior bar's direction, not future bars.
        realized_policy_return = (direction.shift(1).fillna(0.0) * returns * 100.0)
        target = pd.Series(0.0, index=bars.index)
        for t in range(90, len(bars)):
            side = float(direction.iloc[t])
            if side == 0:
                continue
            history = realized_policy_return.iloc[t-80:t].to_numpy(dtype=float)
            f = kelly_grid_solve(history, lam=1.0, n_grid=51)
            target.iloc[t] = side * f
        return {"XAUUSD": target}
