# Mentor feature MAE/MFE lab

Research-only feature labeller. It opens a virtual **long at Ask / closes at Bid** and a virtual **short at Bid / closes at Ask**, so MAE, MFE, and terminal P/L contain the quoted spread.

## Inputs

- `quotes.csv`: `timestamp,bid,ask` in strictly increasing UTC ISO-8601 order.
- `signals.jsonl`: one JSON object per mentor-feature event. Required: `timestamp`, `side`. All other fields are retained in `feature_values`.

Example signal:

```json
{"signal_id":"ny-sweep-001","timestamp":"2026-01-01T13:30:00Z","symbol":"XAUUSD","side":"long","sweep":true,"mss":"bullish","fvg_distance_atr":0.21,"session":"NY","target_price_distance":4.0,"stop_price_distance":2.0}
```

## Run

```bash
PYTHONPATH=. python mentor_feature_scorer.py --quotes quotes.csv --signals signals.jsonl --output labels.jsonl --horizon-seconds 1800
PYTHONPATH=. python -m unittest discover -s tests -v
```

`labels.jsonl` is the auditable training dataset. No order is submitted. The next integration step is to emit the same rows from the verified Nautilus QuoteTick replay driver and compare both outputs before using a model or an EA.
