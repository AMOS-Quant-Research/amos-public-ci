"""Executable-side MAE/MFE labeller for mentor-defined trade features.

This is deliberately a research component: it never submits an order.  It
replays sorted Bid/Ask quotes and scores a virtual long at Ask / short at Bid.
The resulting rows can be used both for an audit table and supervised learning.
"""
from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable


@dataclass(frozen=True)
class Quote:
    timestamp: datetime
    bid: float
    ask: float


def parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def read_quotes(path: Path) -> list[Quote]:
    with path.open(newline="", encoding="utf-8") as handle:
        quotes = [
            Quote(parse_timestamp(row["timestamp"]), float(row["bid"]), float(row["ask"]))
            for row in csv.DictReader(handle)
        ]
    if any(q.ask < q.bid for q in quotes):
        raise ValueError("invalid quote: ask must be >= bid")
    if any(b.timestamp <= a.timestamp for a, b in zip(quotes, quotes[1:])):
        raise ValueError("quotes must have strictly increasing timestamps")
    return quotes


def feature_columns(signal: dict[str, Any]) -> dict[str, Any]:
    reserved = {"timestamp", "side", "signal_id", "symbol", "horizon_seconds"}
    return {key: value for key, value in signal.items() if key not in reserved}


def quote_at_or_after(quotes: list[Quote], timestamp: datetime) -> int:
    lo, hi = 0, len(quotes)
    while lo < hi:
        mid = (lo + hi) // 2
        if quotes[mid].timestamp < timestamp:
            lo = mid + 1
        else:
            hi = mid
    return lo


def score_signal(quotes: list[Quote], signal: dict[str, Any], default_horizon: int) -> dict[str, Any]:
    side = signal["side"].lower()
    if side not in {"long", "short"}:
        raise ValueError("side must be long or short")
    started_at = parse_timestamp(signal["timestamp"])
    start_index = quote_at_or_after(quotes, started_at)
    horizon = int(signal.get("horizon_seconds", default_horizon))
    if start_index >= len(quotes):
        raise ValueError("signal is after final quote")
    ends_at = quotes[start_index].timestamp + timedelta(seconds=horizon)
    window = [q for q in quotes[start_index:] if q.timestamp <= ends_at]
    if not window:
        raise ValueError("no quotes available for signal")

    entry = window[0].ask if side == "long" else window[0].bid
    # Values are executable-side P/L. Therefore the quoted spread is included.
    if side == "long":
        pnl_path = [q.bid - entry for q in window]
    else:
        pnl_path = [entry - q.ask for q in window]
    mfe = max(pnl_path)
    mae = max(0.0, -min(pnl_path))
    exit_pnl = pnl_path[-1]
    max_index = pnl_path.index(mfe)
    min_index = pnl_path.index(min(pnl_path))
    target = float(signal.get("target_price_distance", 0.0))
    stopped = float(signal.get("stop_price_distance", 0.0))
    target_hit = target > 0 and mfe >= target
    stop_hit = stopped > 0 and mae >= stopped
    return {
        "signal_id": signal.get("signal_id", f"{started_at.isoformat()}-{side}"),
        "symbol": signal.get("symbol", "XAUUSD"),
        "timestamp": window[0].timestamp.isoformat(),
        "side": side,
        "horizon_seconds": horizon,
        "entry_executable_price": entry,
        "exit_executable_price": window[-1].bid if side == "long" else window[-1].ask,
        "entry_spread": window[0].ask - window[0].bid,
        "mae_price": mae,
        "mfe_price": mfe,
        "exit_pnl_price": exit_pnl,
        "mfe_to_mae": None if mae == 0 else mfe / mae,
        "seconds_to_mfe": (window[max_index].timestamp - window[0].timestamp).total_seconds(),
        "seconds_to_mae": (window[min_index].timestamp - window[0].timestamp).total_seconds(),
        "target_hit": target_hit,
        "stop_hit": stop_hit,
        "label_positive": bool(target_hit) if target > 0 else exit_pnl > 0,
        "feature_values": feature_columns(signal),
    }


def score_all(quotes: list[Quote], signals: Iterable[dict[str, Any]], default_horizon: int) -> list[dict[str, Any]]:
    return [score_signal(quotes, signal, default_horizon) for signal in signals]


def main() -> None:
    parser = argparse.ArgumentParser(description="Score mentor features against executable Bid/Ask quotes")
    parser.add_argument("--quotes", required=True, type=Path, help="CSV: timestamp,bid,ask")
    parser.add_argument("--signals", required=True, type=Path, help="JSONL: timestamp,side plus mentor features")
    parser.add_argument("--output", required=True, type=Path, help="labelled JSONL output")
    parser.add_argument("--horizon-seconds", type=int, default=1800)
    args = parser.parse_args()
    signals = [json.loads(line) for line in args.signals.read_text(encoding="utf-8").splitlines() if line.strip()]
    labels = score_all(read_quotes(args.quotes), signals, args.horizon_seconds)
    args.output.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in labels), encoding="utf-8")


if __name__ == "__main__":
    main()
