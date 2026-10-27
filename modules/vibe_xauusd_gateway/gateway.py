"""Fail-closed preflight before a caller dispatches a Nautilus raw-tick run."""
from __future__ import annotations

from decimal import Decimal
from typing import Iterable, Mapping

from .contracts import CostModel, RawTick, StrategyProposal, ValidationResult


def prepare_research_run(
    proposal_data: Mapping[str, object],
    cost_data: Mapping[str, object],
    ticks_data: Iterable[Mapping[str, object]],
    lots: object,
    min_ticks: int = 1_000,
) -> ValidationResult:
    """Validate a request without placing orders or invoking a broker.

    The returned acceptance means only *input preflight passed*. It never
    represents a profitable backtest, Nautilus fill, or permission to trade.
    """
    try:
        StrategyProposal.from_mapping(proposal_data)
        cost = CostModel.from_mapping(cost_data)
        lots_decimal = Decimal(str(lots))
        if not lots_decimal.is_finite() or lots_decimal <= 0:
            raise ValueError("lots must be a positive finite number")
        if min_ticks < 1:
            raise ValueError("min_ticks must be at least 1")
        ticks = [RawTick.from_mapping(row) for row in ticks_data]
        if len(ticks) < min_ticks:
            raise ValueError(f"insufficient raw ticks: {len(ticks)} < {min_ticks}")
        for previous, current in zip(ticks, ticks[1:]):
            if current.ts_ns <= previous.ts_ns:
                raise ValueError("tick timestamps must be strictly increasing")
        return ValidationResult(
            accepted=True,
            reason="PREFLIGHT_PASSED_NOT_A_BACKTEST",
            tick_count=len(ticks), first_ts_ns=ticks[0].ts_ns, last_ts_ns=ticks[-1].ts_ns,
            estimated_round_turn_cost_usd=cost.estimated_round_turn_cost(lots_decimal),
            initial_margin_usd=cost.initial_margin(ticks[-1].ask, lots_decimal),
        )
    except (TypeError, ValueError, KeyError) as exc:
        return ValidationResult(False, f"PREFLIGHT_REJECTED: {exc}", 0, None, None, None, None)
