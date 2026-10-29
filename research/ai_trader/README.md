# AMOS AI Trader: stages 1–6 (research only)
Source UI: user-provided Russell2000_Indicators_Fixed.zip; UI contains **synthetic candles** and placeholder SAR. Do not use its fake OHLC, fake win rates or placeholder SAR for trades.

1. Indicator features: independent RSI, CCI, Williams %R, SMA, ATR. SAR omitted until validated; CCI and RSI require reference cross-check before deployment.
2. Input: actual XAUUSD Bid/Ask QuoteTick CSV with `ts_event,bid,ask`, timestamp in **nanoseconds**, ascending, >=1000 quotes. Completed M1 bars only. Existing Nautilus catalog should be exported using an explicit adapter; this module does not pretend the adapter is already wired.
3. AI: optional NVIDIA_NIM candidate provenance, strict parameter allowlist; no LLM execution or inference is claimed. NIM connectivity must pass independently.
4. Decision: BUY / SELL / WAIT with Entry / SL / TP research suggestions; never an order.
5. Native BT: existing NautilusTrader research runner reused separately. No performance or fills fabricated; no promotion without real native evidence, OOS, cost calibration, risk and reproducibility.
6. CoreAI: JSON research intake envelope. Actual CoreAI endpoint, transport, ACK, Risk Governor integration unverified. Every envelope has NOT_DELIVERED and DENIED.
Example: `python -m research.ai_trader.engine --quotes actual_quotes.csv --output research_intake.json`.
This only works with **real** properly timestamped quote CSV. Do not feed the UI synthetic data.

## Implemented adapters (2026-10-29)
- `catalog_adapter.py`: loads existing Nautilus `ParquetDataCatalog` XAUUSD.SIM QuoteTicks, verifies timestamps and spread, exports CSV and SHA256 provenance. Requires a real catalog and Nautilus installed.
- `nim_candidate.py`: optional NVIDIA NIM request with strict parameter allowlist; fails closed if secret is absent. NIM connectivity not yet successful.
- `pipeline.py`: chains real catalog export -> validated NIM parameters (optional) -> completed M1 bar decision -> CoreAI research intake JSON. It does **not** call Native BT or transmit to CoreAI.
- `python -m research.ai_trader.pipeline --catalog /actual/catalog/path --output /tmp/amos-ai-trader`
- Add `--use-nim` only with a working `NVIDIA_NIM_API_KEY`.
- `--native-evidence` accepts research evidence metadata, but does not cryptographically verify fills or substitute for an actual native backtest. Do not interpret a READY flag as validated edge or delivery.
- CI only runs deterministic unit tests. No real catalog path, CoreAI endpoint or API credential is available in this workflow.
