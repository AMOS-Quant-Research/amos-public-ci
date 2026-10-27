# AMOS Vibe XAUUSD Raw-Tick Gateway

This is an AMOS-owned extension for Vibe-Trading research proposals. It does not
modify Vibe-Trading, send broker orders, invoke MT5, or claim a Nautilus fill.

Its single responsibility is a fail-closed handoff:

`Vibe proposal -> XAUUSD Bid/Ask preflight -> cost/margin estimate -> Nautilus dispatch candidate`

## Contract

`prepare_research_run(proposal, cost_model, ticks, lots)` accepts only:

- `symbol: "XAUUSD"`;
- an explicit `live_trading: false` proposal;
- normalized Bid/Ask ticks with positive, strictly increasing `ts_ns` values;
- `ask >= bid` for every tick;
- explicit commission, adverse slippage, contract size, margin rate and leverage.

An accepted result is **not** a backtest pass, a Native Fill, a profitability
claim, or approval for any live order. The next adapter must turn this input
into the existing Nautilus raw-tick driver and return independently produced
KPI evidence.

## Example

```python
from modules.vibe_xauusd_gateway import prepare_research_run

proposal = {"proposal_id": "vt-001", "symbol": "XAUUSD",
            "strategy_path": "strategies/vt_001.py", "source": "vibe-trading",
            "live_trading": False}
cost = {"symbol": "XAUUSD", "commission_per_lot_usd": "7",
        "slippage_points_per_side": "2", "point_size": "0.01",
        "contract_size": "100", "margin_rate": "0.005", "max_leverage": "2000"}
ticks = [{"ts_ns": 1, "bid": "2300.00", "ask": "2300.05"}] * 1000
# Real input must use strictly increasing timestamps.
result = prepare_research_run(proposal, cost, ticks, lots="0.01")
```
