"""Bridge the existing Nautilus QuoteTick replay into the mentor feature labeller.

The bridge receives in-memory QuoteTicks from the native replay driver. It keeps
the original event nanoseconds and Bid/Ask prices; it never creates OHLC prices
or places an order.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

try:  # Supports both repository-root and mentor_feature_lab-local test runs.
    from research.mentor_feature_lab.mentor_feature_scorer import Quote, score_all
except ModuleNotFoundError:
    from mentor_feature_scorer import Quote, score_all


def _price(value: Any) -> float:
    return float(value.as_double()) if hasattr(value, "as_double") else float(value)


def quotes_from_native_ticks(raw_ticks: Iterable[Any]) -> list[Quote]:
    """Convert native ticks without changing event time or Bid/Ask price."""
    quotes: list[Quote] = []
    previous_ns = -1
    for tick in raw_ticks:
        timestamp_ns = int(tick.ts_event)
        bid, ask = _price(tick.bid_price), _price(tick.ask_price)
        if timestamp_ns <= previous_ns:
            raise ValueError("native QuoteTicks must have strictly increasing ts_event")
        if bid <= 0 or ask < bid:
            raise ValueError("native QuoteTick has crossed or invalid Bid/Ask")
        # pandas.Timestamp preserves Nautilus nanosecond event precision.
        quotes.append(Quote(pd.Timestamp(timestamp_ns, unit="ns", tz="UTC"), bid, ask))
        previous_ns = timestamp_ns
    if not quotes:
        raise ValueError("no native QuoteTicks supplied")
    return quotes


def _signals(path: Path) -> list[dict[str, Any]]:
    try:
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    except json.JSONDecodeError as exc:
        raise ValueError("mentor signals must be valid JSONL") from exc


def label_native_quote_ticks(*, raw_ticks: Iterable[Any], signals_path: Path,
                             labels_path: Path, evidence_path: Path,
                             default_horizon: int) -> dict[str, Any]:
    """Write labels and a receipt proving they used the native replay sequence."""
    if int(default_horizon) <= 0:
        raise ValueError("default_horizon must be positive")
    quotes = quotes_from_native_ticks(raw_ticks)
    signals_path = Path(signals_path)
    signals = _signals(signals_path)
    labels = score_all(quotes, signals, int(default_horizon))

    labels_path = Path(labels_path)
    evidence_path = Path(evidence_path)
    labels_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    labels_bytes = "".join(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n" for row in labels).encode("utf-8")
    labels_path.write_bytes(labels_bytes)
    signal_bytes = signals_path.read_bytes()
    result = {
        "contract": "amos.mentor-feature.native-quotetick.v1",
        "source": "Nautilus QuoteTick replay",
        "live_trading": False,
        "order_permission": "DENIED",
        "ohlc_resample_used": False,
        "raw_ticks": len(quotes),
        "first_ts_event_ns": int(quotes[0].timestamp.value),
        "last_ts_event_ns": int(quotes[-1].timestamp.value),
        "signals": len(signals),
        "labels": len(labels),
        "signals_sha256": hashlib.sha256(signal_bytes).hexdigest(),
        "labels_sha256": hashlib.sha256(labels_bytes).hexdigest(),
        "labels_path": str(labels_path),
        "price_side_rule": {
            "long": "entry Ask; MAE/MFE and terminal exit Bid",
            "short": "entry Bid; MAE/MFE and terminal exit Ask",
        },
    }
    evidence_path.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return result
