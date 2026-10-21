"""NautilusTrader real tick ingestion smoke (no synthetic OHLC or trades).

This is a runtime/data smoke, not a strategy performance backtest.
"""
import csv
import json
import sys
from pathlib import Path

def main(src, dest):
    from nautilus_trader.backtest.engine import BacktestEngine
    from nautilus_trader.backtest.config import BacktestEngineConfig
    from nautilus_trader.model.data import QuoteTick
    rows = list(csv.DictReader(Path(src).open(encoding="utf-8")))
    if len(rows) < 100:
        raise RuntimeError("Insufficient real quote ticks")
    previous = None
    for row in rows:
        bid, ask = float(row["bid"]), float(row["ask"])
        if bid <= 0 or ask < bid:
            raise ValueError("Invalid quote")
        from datetime import datetime
        t = datetime.fromisoformat(row["time"])
        if previous and t < previous:
            raise ValueError("Out-of-order timestamps")
        previous = t
    engine = BacktestEngine(config=BacktestEngineConfig())
    result = {
        "status": "RUNTIME_AND_RAW_TICK_INPUT_VALIDATED",
        "engine": type(engine).__name__,
        "quote_tick_type": QuoteTick.__name__,
        "source": "Dukascopy XAUUSD .bi5",
        "real_quote_rows": len(rows),
        "first_timestamp": rows[0]["time"],
        "last_timestamp": rows[-1]["time"],
        "strategy_executed": False,
        "orders_executed": 0,
        "performance_backtest_completed": False,
        "reason": "Instrument registration, QuoteTick conversion, and strategy are not yet wired",
    }
    Path(dest).write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
