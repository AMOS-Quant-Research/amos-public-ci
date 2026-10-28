# XAUUSD Vibe-Trading — AMOS research intake

**Status: STAGED / NOT DEPLOYED / NOT AUTONOMOUS.** This directory is the AMOS control-plane intake, **not** a second Vibe-Trading engine or a replacement for existing Nautilus and Raw Tick assets.

## Source and integrity
- Source: Google Drive file ID `1HY3-1htL8rdWaHC_xSiZjPg6Ap6AEknQ`
- Archive: `XAUUSD_Vibe_Trading_Complete_Package.zip` (31,191,962 bytes)
- SHA-256: `56bf3bcfc3221b6cccd9cd64c03425952ebc98baf510e39058b65372772bdf38`
- Archive members: 3,437
- Source upstream as stated in included document: `HKUDS/Vibe-Trading`; license file in ZIP says MIT. Confirm provenance/third-party assets before redistribution.

## Placement decision
- **Proposed standalone code repository**: `AMOS-Quant-Research/amos-vibe-trading` (confirmed **not created** on 2026-10-28; create separately after source/security/license review).
- **This public CI repository**: intake metadata, contract tests, CI evidence, task/result integration; never copy the whole ZIP or credentials here.
- **Raw Bid/Ask data**: reuse existing `Sai310421/xauusd-data` catalog where compatible; do not substitute the repository's documented OHLCV for execution. Keep bundled Parquet out of ordinary Git commits.
- **Execution host**: one explicitly approved research runner/mini PC, initially offline/mock; no live MT5/Exness orders.

## Actual inspected package contents
- `Vibe-Trading/agent/backtest/runner.py`
- `Vibe-Trading/agent/backtest/engines/nautilus_rawtick.py`
- `Vibe-Trading/agent/backtest/engines/nautilus_vibe_driver.py`
- `Vibe-Trading/agent/backtest/engines/xauusd_execution_profile.example.json`
- `xauusd-data/.work/vibe-math-xauusd-20260727/data/quote_tick/...parquet` (one quote-tick Parquet)
- `XAUUSD_Vibe_Trading_Workflow_Package.md`

**Evidence discrepancy:** the included workflow document claims a completed Raw Tick cycle (208,501 ticks, 1 native fill) and references `Vibe-Trading/.work/rawtick-e2e/run_card.md`, `artifacts/nautilus_rawtick_evidence.json`, and `artifacts/metrics.csv`, but **none of those three claimed evidence files exists in this ZIP**. Thus no native fill or KPI is independently verified by this intake. Treat as BLOCKED for evidence-based completion, not as PASS.

## Integration interface
1. Receive approved `Task` from the **existing** AMOS Task Router; do not invent/overwrite its schema.
2. Invoke the existing Vibe backtest lifecycle with `codes: ["XAUUSD"]`, `nautilus_rawtick` driver, explicit costs and catalog snapshot. The adapter contract in the package is `amos.vibe.measured-evidence.v1`.
3. Validate evidence: Raw Bid/Ask; NautilusTrader BacktestEngine; `raw_ticks > 0`; `native_fills > 0`; finite KPI values where required; exact input SHA/catalog ID; broker depth/slippage assumptions disclosed.
4. Produce Vibe Run Card and translate into the **existing** AMOS Result contract only after locating its actual schema and tests.
5. Grok independent audit and CI evidence before accepting a research candidate.

## Acceptance gates
- A. ZIP integrity/layout gate: local preflight, SHA and archive safety.
- B. Source/provenance, dependency, license, secret and binary review.
- C. Real Raw Bid/Ask input integrity and monotonically ordered timestamps.
- D. Measured Nautilus native fill + evidence + KPI from an actual runner (no OHLC execution proxy).
- E. Existing Task/Result contract E2E and failure/timeout handling.
- F. Two consecutive **new** autonomous hypothesis cycles with Run Cards, no repeated replay as a substitute.
- G. OOS/WFO/Monte Carlo, cost assumptions, risk gates before any later operational proposal.

## Forbidden
No unreviewed whole-ZIP upload to a public repo; no 19 MB bundled font redistribution; no secrets; no main push or auto-merge; no live trading; no billed provider calls; no weakening existing Risk Governor or changing frozen gates. Scheduler stays OFF until a model provider and always-on host are independently verified.
