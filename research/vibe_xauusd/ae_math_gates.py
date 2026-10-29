"""AE Math Watch mathematical gates, isolated from execution and research loop.

These are mathematical implementations, not validated trading EDGE.
No data/network/LLM dependencies.
"""
import math


def dynamic_ddr_scale(drawdown, cap, lam=1.0):
    """AE candidate: (1-exp(-lam * distance/cap)) / (1-exp(-lam)).

    distance=max(0, cap-drawdown); 1 at DD=0, 0 at DD>=cap.
    """
    if not all(math.isfinite(float(v)) for v in (drawdown, cap, lam)):
        raise ValueError("nonfinite parameter")
    if cap <= 0 or lam <= 0 or drawdown < 0:
        raise ValueError("invalid parameter")
    distance = max(0.0, float(cap) - float(drawdown))
    return max(0.0, min(1.0, -math.expm1(-lam * distance / cap) / -math.expm1(-lam)))


def dd_velocity_guard(dd_velocity, dd_acceleration, lambda_v=0.5, lambda_a=0.5):
    """AE candidate: exp(-lambda_v*[DD velocity]+ -lambda_a*[DD acceleration]+)."""
    values = (dd_velocity, dd_acceleration, lambda_v, lambda_a)
    if not all(math.isfinite(float(v)) for v in values) or min(lambda_v, lambda_a) < 0:
        raise ValueError("invalid guard parameter")
    return math.exp(-lambda_v * max(0.0, dd_velocity) - lambda_a * max(0.0, dd_acceleration))


def risk_constrained_kelly_moment(probabilities, wealth_multipliers, lam):
    """Paper-side RC Kelly constraint: sum p_i * W_i**(-lam) <= 1."""
    if not math.isfinite(lam) or lam <= 0 or len(probabilities) != len(wealth_multipliers) or not probabilities:
        raise ValueError("invalid Kelly inputs")
    if any(not math.isfinite(x) or x < 0 for x in probabilities):
        raise ValueError("invalid probability")
    if any(not math.isfinite(x) or x <= 0 for x in wealth_multipliers):
        raise ValueError("wealth multipliers must be positive")
    if not math.isclose(sum(probabilities), 1.0, abs_tol=1e-9):
        raise ValueError("probabilities must sum to one")
    return sum(p * math.exp(-lam * math.log(w)) for p, w in zip(probabilities, wealth_multipliers))
