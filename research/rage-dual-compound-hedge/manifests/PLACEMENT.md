# Placement

Canonical code location, per the RAGE execution directive v2.0:

```
AMOS-Quant-Research/amos-public-ci
└── research/rage-dual-compound-hedge/
```

This directory is new. It does not replace `modules/`, `scripts/`, `tests/`, or the existing Nautilus smoke workflow.

## What stays out of this repository

`PUBLIC_CI_POLICY.md` forbids private strategy source, account data, secrets, and market tick datasets.

| Asset | Where it already lives | Status in this lab |
|---|---|---|
| Nautilus public install | `.github/workflows/crt-nautilus-public-smoke.yml` | Reused, not copied. Last inspected run `39579418065` printed `nautilus_trader` `2.0.0rc6`, then the synthetic engine step failed (`No module named 'nautilus_trader.backtest.models'`). |
| Raw Bid/Ask catalog | `Sai310421/xauusd-data` (`catalog/raw_bidask`, PR #30) | Not vendored. Native fill count remains 0 until a catalog run is logged. |
| Dukascopy cache / MTF books | `Sai310421/xauusd-duka-feed` `books/duka-sync.json` | MTF bars only. Not a QuoteTick count. |
| Older formula skeleton | `Sai310421/xauusd-data/rage-dual-compound-hedge` and PR #33 | Left in place. This tree is the public-CI copy of the math and gates. |

Live trading is off. OHLC is not a substitute for Raw Bid/Ask fills.
