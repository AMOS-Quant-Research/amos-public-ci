# AMOS horizontal integration — evidence ledger

## Verified status as of 2026-10-29
- GitHub CI unit tests for the AI Trader code passed; **real XAUUSD native BT for this new model is NOT verified**.
- NVIDIA NIM workflow currently fails; a failed workflow with no jobs does not prove why. Do not claim working inference.
- CoreAI receiver endpoint and Risk Governor production contract are unverified; research envelopes say NOT_DELIVERED / DENIED.
- Dagram: public SSE `/relay/stream` and BUY/SELL/STAY UI observed in prior research. No proof that the full private signal algorithm or issuance timestamp can be recovered.
- TheOptionSignalHub: static C# IL analysis decoded 195 methods, 48,330 bytes, 15,409 instructions. Observed `RiskSnapshot.Block` guard categories: daily sends, consecutive losses, prospective daily loss. `OrderEngine.CheckRisk` stops on violation; `ResolveUnknown` requires explicit resolution. This is **not** a faithful C# source recreation or verified live behavior.

## Integration contracts
`research/ai_trader/bridge.py` normalizes independent AMOS AI Trader signals, new public Dagram SSE observations and explicitly marked independent SignalHub research signals to `amos.signal.v1`. Missing prices, unknown observation time, hello/snapshot data or missing evidence fail closed.

`research/ai_trader/signal_hub.py` provides independent preflight risk checks, signal ID deduplication, journal-backed research queue, and unknown-state lock. These are AMOS safety controls informed by analysis, **not** claimed byte-for-byte replicas. No broker, API order submission or MT5 transport.

## Target pipeline
dagram observations + independent AI Trader -> common signal contract -> research-only risk preflight -> research queue -> existing NautilusTrader Raw QuoteTick native BT -> PF/EV/DD/MAE/MFE -> OOS/WFO/Monte Carlo -> AMOS Research DB -> CoreAI research intake.

**Not yet connected:** the research queue consumer to NautilusTrader driver, results to a durable Research DB, real native backtest of this model, CoreAI ACK, MT5 DEMO. Research Queue is not a production order queue. No actual execution permission.

## Evidence requirements before any success claim
1. Immutable real XAUUSD QuoteTick catalog, instrument and SHA.
2. Candidate parameters and timestamp-causal signals; no future bars.
3. Actual Nautilus native fills and recorded cost assumptions.
4. OOS/WFO/MC and calibrated costs, reproducibility.
5. CoreAI ACK and separate Risk Governor review.
6. MT5 DEMO integration tested separately. Live OFF.
