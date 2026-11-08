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


## Nautilus QuoteTick integration

The native replay driver can now send the **same in-memory QuoteTick sequence**
to this labeller. It does not route through OHLC prices, does not submit a live
order, and records a SHA-256 provenance receipt next to the labels.

```bash
PYTHONPATH=. python -m research.ai_trader.native_run \
  --catalog /actual/catalog/path \
  --output /tmp/mentor-native-run \
  --mentor-signals /path/mentor_signals.jsonl \
  --mentor-horizon-seconds 1800
```

On a successful native replay, the output directory contains:

- `native_run/artifacts/mentor_feature_labels.jsonl`
- `native_run/artifacts/mentor_feature_label_evidence.json`
- `native_run/artifacts/nautilus_rawtick_evidence.json`
- `native_research_result.json`

The final result refuses to claim the connection when the labeller's Raw Tick
count differs from the native replay evidence. A successful native replay and
its artifacts are still required before claiming any run result.
