# Potential preflight contract v1

Input: JSON object with `contract: amos.potential.input.v1`, `sources` (1..100 unique id strategy objects), optional `confluences` (id and >=2 valid member ids). See example_input.json.

Output: `amos.potential.preflight.v1` with immutable `input_sha256`, `by_source`, `by_confluence`, `research_only=true`, `live_trading=false`, `order_permission=DENIED`, `native_bt_executed=false`, `score_owner=NautilusTrader`.

Nine deterministic completeness/evidence checks (boolean) with explicitly disclosed weights; weighted coverage is **not** probability of success. Verdicts: BLOCKED (critical data/entry-risk gaps), NEEDS_REFINEMENT (noncritical gaps), READY_FOR_NATIVE_BT (all nine checks satisfied). READY means **eligible for expensive testing**, not deployable.

Confluence is descriptive only: shared labels do not establish synergy or correlation. Actual cross-strategy effects require timestamp-aligned signals, position exposure, and native fill ledger. Unknown numeric outcomes must remain null.

Required strategy fields: id, thesis, mechanism, market, timeframe, entry, exit, data, costs, risk, validation. Execution and signals are also needed for complete readiness. No external calls or file execution of supplied strategies. Invalid contract/duplicate ids/invalid pairs fail closed.

Future research (not implemented): real lightweight tick opportunity scan, measured spread/slippage sensitivity, time-aligned overlap/correlation, calibrated probabilistic potential estimation. None may be called measured until supported by actual artifacts.
