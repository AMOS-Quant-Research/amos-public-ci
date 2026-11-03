# M1 Fractal State Learner

Research-only module: Raw Bid/Ask ticks → 5-second / 15-second / M1 bars → causal M1-internal-state features → chronological M5 and M15 state forecasts.

It never creates an order, scores profitability, or substitutes OHLC data for a Raw Tick source. Quote-tick count is an activity proxy, not traded volume.

## What is learned

The dependency-free `centroid_v1` learner estimates `down`, `flat`, or `up` for the next completed M5 and M15 window from five completed M1 bars. Each M1 carries return, range, spread, tick count, a causal state encoding, and its fixed path of twelve 5-second plus four 15-second returns. Missing sub-bars are explicit zeroes; they are never fabricated from OHLC.

Kronos remains a separate forecast model. This is the transparent XAUUSD-specific baseline that actual Kronos inference must beat on chronological OOS data.

## Run

```bash
python -m research.kronos_fractal.run --ticks path/to/xauusd_raw_bidask.csv --output artifacts/kronos_fractal/report.json
```

Input requires `timestamp,bid,ask`, strictly increasing UTC timestamps, and `bid <= ask`. The report includes source hash, model, OOS predictions and directional accuracy; it makes no profitability claim.

## Promotion gate

1. Validate a real Dukascopy QuoteTick export.
2. Run distinct chronological OOS regimes.
3. Compare persistence/drift and actual Kronos.
4. Only then hand an approved forecast contract to independently costed Nautilus Raw Tick BT.
