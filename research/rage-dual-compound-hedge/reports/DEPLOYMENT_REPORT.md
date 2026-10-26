# AMOS RAGE LAB DEPLOYMENT REPORT

Generated 2026-10-26 from inspected GitHub state and a local unit run.
Fields without an execution artifact are `NOT_VERIFIED`.

```
REPOSITORY: AMOS-Quant-Research/amos-public-ci
BRANCH: research/rage-dual-compound-hedge-20261026
COMMIT_SHA: 8d110a88f2d6014be3b60f6f38cf325ed0129d5a
LAB_DIRECTORY: research/rage-dual-compound-hedge/
CI_RUNNER: ubuntu-latest (GitHub-hosted public runner)
RUNNER_STATUS: PARTIAL
  - Scheduled synthetic queue succeeded: run 40338401862 (2026-10-26T14:18:18Z, 10s)
  - Nautilus smoke is not healthy: run 39579418065 failed 2026-10-21
  - This lab's rage-dch-unit workflow has not produced a run URL yet
RUN_ID: NOT_VERIFIED (rage-dch-unit). Related runs: 40338401862, 39579418065
CI_RESULT: NOT_VERIFIED on GitHub. Local: 28 unittest OK (stdlib only)
DATA_STORAGE: external. Not committed here (public CI policy)
DATA_STORAGE_PATH: Sai310421/xauusd-data catalog/raw_bidask (documented, not enumerated this session); Sai310421/xauusd-duka-feed books/ + Actions cache
DATA_SOURCE: Dukascopy feed documented in Sai310421/xauusd-duka-feed. Exness contract spec NOT_VERIFIED
DATA_LICENSE_STATUS: NOT_VERIFIED
XAUUSD_RAW_TICK_COUNT: NOT_VERIFIED
XAUUSD_DATE_RANGE: NOT_VERIFIED for QuoteTicks. MTF books in duka-sync.json (updated 2026-10-26T14:08:05Z) span 2025-09-01 to 2026-08-31 and are not raw ticks. m1_days_cached=311
USDJPY_RAW_TICK_COUNT: NOT_VERIFIED
EURUSD_RAW_TICK_COUNT: NOT_VERIFIED
GBPUSD_RAW_TICK_COUNT: NOT_VERIFIED
XAGUSD_RAW_TICK_COUNT: NOT_VERIFIED
OPTION_DATA_SOURCE: NOT_VERIFIED
OPTION_DATA_STATUS: NOT_VERIFIED
GC_FUTURES_DATA_STATUS: NOT_VERIFIED
NAUTILUS_VERSION: 2.0.0rc6 (printed by run 39579418065). Not importable in the Grok sandbox this session
NAUTILUS_NATIVE_FILL_COUNT: 0
MAIN_ENGINE_STATUS: IMPLEMENTED_UNPROVEN
RAGE_ENGINE_STATUS: IMPLEMENTED_UNPROVEN
PROTECTIVE_BOOK_STATUS: V1_FORMULA_UNIT_TESTED
RETURN_BOOK_STATUS: STRUCTURAL_ONLY
OOS_WFO_STATUS: BLOCKED (index splitter only)
MONTE_CARLO_STATUS: STRUCTURAL_PAIRED_BLOCKS_ONLY
BLOCKERS:
  - No Raw Bid/Ask catalog execution log for this lab
  - Multi-currency and option histories not ingested
  - Public Nautilus synthetic BT import is broken (nautilus_trader.backtest.models)
  - Monthly 10% hypothesis is not a result
FIXES_APPLIED:
  - New directory only. main tree not overwritten
  - No tick files, secrets, or private EA sources copied
  - Unit workflow capped at 5 minutes, contents: read
NEXT_ACTION: Draft PR. Dispatch rage-dch-unit only. Do not treat MTF books or the broken synthetic Nautilus step as a fill count.
```

Live trading: OFF.
Hypothesis flags: MAIN_10_PERCENT_COMPOUND=BLOCKED, HEDGE_10_PERCENT_COMPOUND=BLOCKED.
