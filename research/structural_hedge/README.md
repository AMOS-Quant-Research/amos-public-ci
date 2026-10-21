# Structural Hedge Nautilus Raw Tick research (Issue #35)

## Verified existing integration
- Data producer: `Sai310421/xauusd-duka-feed/scripts/duka_raw90.py`
- Integrity gate: `Sai310421/xauusd-duka-feed/scripts/raw90_integrity.py`
- Existing Nautilus QuoteTick loader: `Sai310421/xauusd-data`, branch `amos-tripleengine-virtualentry-v2`, path `amos_triple_engine_v2/nautilus_raw90_runner.py`
- Actual schema: `time,bid,ask,bid_size,ask_size`
- Existing workflow: `Sai310421/xauusd-duka-feed/.github/workflows/duka-raw90.yml`

## Distinction
The existing runner evaluates **15 virtual-entry candidates**, not the Structural Hedge hypothesis. Its KPIs must never be reported as Structural Hedge results.

## Required next implementation
1. A standalone Nautilus Strategy with confirmed-bar swing/FVG/IFVG calculations derived from the actual quote tick stream, and execution at the subsequent executable bid/ask.
2. Explicit leg state: first, equal-volume hedge, second, independent hedge close.
3. Account/margin/floating DD, fill events and transaction costs; failure recovery.
4. Raw tick input manifest + no-OHLC assertion + trade log + KPI JSON.
5. Unit tests and a public CI job; no auto-merge.

No WR1–WR5. No synthetic/OHLC proxy. No live orders.
