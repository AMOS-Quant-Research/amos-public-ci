"""Versioned, dependency-free contracts for the AMOS Vibe XAUUSD gateway."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal
from typing import Any, Mapping


CONTRACT_VERSION = "amos.vibe.xauusd.v1"


def _decimal(value: Any, name: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except Exception as exc:  # pragma: no cover - defensive boundary
        raise ValueError(f"{name} must be decimal-compatible") from exc
    if not result.is_finite():
        raise ValueError(f"{name} must be finite")
    return result


@dataclass(frozen=True)
class RawTick:
    """A normalized XAUUSD L1 quote. ``ts_ns`` is Unix nanoseconds."""

    ts_ns: int
    bid: Decimal
    ask: Decimal
    bid_size: Decimal = Decimal("0")
    ask_size: Decimal = Decimal("0")

    @classmethod
    def from_mapping(cls, row: Mapping[str, Any]) -> "RawTick":
        try:
            ts_ns = int(row["ts_ns"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("tick ts_ns must be an integer") from exc
        if ts_ns <= 0:
            raise ValueError("tick ts_ns must be positive")
        bid = _decimal(row.get("bid"), "bid")
        ask = _decimal(row.get("ask"), "ask")
        bid_size = _decimal(row.get("bid_size", 0), "bid_size")
        ask_size = _decimal(row.get("ask_size", 0), "ask_size")
        if bid <= 0 or ask <= 0:
            raise ValueError("bid and ask must be positive")
        if ask < bid:
            raise ValueError("ask must be greater than or equal to bid")
        if bid_size < 0 or ask_size < 0:
            raise ValueError("quote sizes must be non-negative")
        return cls(ts_ns=ts_ns, bid=bid, ask=ask, bid_size=bid_size, ask_size=ask_size)


@dataclass(frozen=True)
class CostModel:
    """Conservative, explicit cost assumptions; all values are per round-turn lot."""

    symbol: str
    commission_per_lot_usd: Decimal
    slippage_points_per_side: Decimal
    point_size: Decimal
    contract_size: Decimal
    margin_rate: Decimal
    max_leverage: Decimal
    swap_long_usd_per_lot_day: Decimal = Decimal("0")
    swap_short_usd_per_lot_day: Decimal = Decimal("0")

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "CostModel":
        fields = {key: _decimal(data.get(key), key) for key in (
            "commission_per_lot_usd", "slippage_points_per_side", "point_size",
            "contract_size", "margin_rate", "max_leverage")}
        optional = {key: _decimal(data.get(key, 0), key) for key in
                    ("swap_long_usd_per_lot_day", "swap_short_usd_per_lot_day")}
        symbol = str(data.get("symbol", ""))
        if symbol != "XAUUSD":
            raise ValueError("only XAUUSD is accepted by this gateway")
        if fields["point_size"] <= 0 or fields["contract_size"] <= 0:
            raise ValueError("point_size and contract_size must be positive")
        if fields["margin_rate"] <= 0 or fields["margin_rate"] > 1:
            raise ValueError("margin_rate must be in (0, 1]")
        if fields["max_leverage"] < 1:
            raise ValueError("max_leverage must be at least 1")
        if fields["commission_per_lot_usd"] < 0 or fields["slippage_points_per_side"] < 0:
            raise ValueError("commission and slippage cannot be negative")
        return cls(symbol=symbol, **fields, **optional)

    def estimated_round_turn_cost(self, lots: Decimal) -> Decimal:
        """Commission plus both-side adverse slippage, excluding observed spread."""
        lots = _decimal(lots, "lots")
        if lots <= 0:
            raise ValueError("lots must be positive")
        return (self.commission_per_lot_usd * lots +
                Decimal("2") * self.slippage_points_per_side * self.point_size *
                self.contract_size * lots)

    def initial_margin(self, reference_price: Decimal, lots: Decimal) -> Decimal:
        price = _decimal(reference_price, "reference_price")
        lots = _decimal(lots, "lots")
        if price <= 0 or lots <= 0:
            raise ValueError("reference_price and lots must be positive")
        return price * self.contract_size * lots * self.margin_rate


@dataclass(frozen=True)
class StrategyProposal:
    """Narrow, declarative proposal accepted from Vibe-Trading."""

    proposal_id: str
    symbol: str
    strategy_path: str
    source: str
    live_trading: bool = False

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "StrategyProposal":
        proposal = cls(
            proposal_id=str(data.get("proposal_id", "")),
            symbol=str(data.get("symbol", "")),
            strategy_path=str(data.get("strategy_path", "")),
            source=str(data.get("source", "")),
            live_trading=bool(data.get("live_trading", False)),
        )
        if not proposal.proposal_id or not proposal.strategy_path or not proposal.source:
            raise ValueError("proposal_id, strategy_path and source are required")
        if proposal.symbol != "XAUUSD":
            raise ValueError("proposal symbol must be XAUUSD")
        if proposal.live_trading:
            raise ValueError("live_trading must be false")
        return proposal


@dataclass(frozen=True)
class ValidationResult:
    accepted: bool
    reason: str
    tick_count: int
    first_ts_ns: int | None
    last_ts_ns: int | None
    estimated_round_turn_cost_usd: Decimal | None
    initial_margin_usd: Decimal | None

    def as_dict(self) -> dict[str, Any]:
        result = asdict(self)
        for name in ("estimated_round_turn_cost_usd", "initial_margin_usd"):
            if result[name] is not None:
                result[name] = str(result[name])
        return result
