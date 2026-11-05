# AMOS / AE Math EDGE Dictionary (research-only)

This is the **consolidated, reviewable index** for Math EDGE research intake. It does **not** assert that a paper equation is a profitable strategy or that a GitHub Issue constitutes a tested implementation.

## Where things live

| Layer | Source of truth | Meaning |
| --- | --- | --- |
| Literature / provenance | [AMOS GitHub Issues](https://github.com/AMOS-Quant-Research/amos-public-ci/issues?q=is%3Aissue+%22Math+EDGE%22) | Paper title, exact ORIGINAL math, assumptions, AE_DERIVED idea and blockers |
| Consolidated research index | [dictionary.json](./dictionary.json) | Machine-readable snapshot of **seven** confirmed Issues (#49, #57, #61, #62, #64, #65, #69) |
| Vibe execution candidate registry | `research/vibe_xauusd/ae_candidate_registry.json` on [PR #46](https://github.com/AMOS-Quant-Research/amos-public-ci/pull/46) | Separate Kelly parameter triples, **not** the Math EDGE Dictionary |
| Evidence | Actual Native CI Run URL, immutable SHA and persisted results | Required for any tested/promoted status; none is claimed for the seven paper methods here |

**Snapshot date:** 2026-11-05. This is a **manually curated snapshot**, not a live Issue synchronization or automated discovery service. Other historical proposals discussed outside these six verified Issues have **not** been silently imported.

## Research inventory

| ID | Issue | Method | Current decision | Principal blocker |
| --- | --- | --- | --- | --- |
| AE-MATH-0049 | [#49](https://github.com/AMOS-Quant-Research/amos-public-ci/issues/49) | Ratcheting/reset dividend control | HOLD | Multi-period equity/withdrawal and reset-friction inputs |
| AE-MATH-0057 | [#57](https://github.com/AMOS-Quant-Research/amos-public-ci/issues/57) | Wiener–Hopf causal filter | HOLD | Execution impact and cost kernel |
| AE-MATH-0061 | [#61](https://github.com/AMOS-Quant-Research/amos-public-ci/issues/61) | Regime-switching dividend barrier | HOLD | Multi-regime capital/ruin histories |
| AE-MATH-0062 | [#62](https://github.com/AMOS-Quant-Research/amos-public-ci/issues/62) | Regime-weighted conformal VaR | HOLD | Multi-regime OOS tail-risk calibration |
| AE-MATH-0064 | [#64](https://github.com/AMOS-Quant-Research/amos-public-ci/issues/64) | Queue-sensitive passive market impact | HOLD | Real LOB messages / anticipation term |
| AE-MATH-0065 | [#65](https://github.com/AMOS-Quant-Research/amos-public-ci/issues/65) | Finite-action diffusion control | HOLD | Exact theorem-to-lot mapping |
| AE-MATH-0069 | [#69](https://github.com/AMOS-Quant-Research/amos-public-ci/issues/69) | Cross-strategy signal collision | HOLD | Multi-strategy aligned intents, positions and multi-asset OOS |

## Meaning of evidence fields

- **ORIGINAL** is the mathematical equation or model *reported by the source Issue*; the index is not a claim of independently reproduced proofs.
- **AE_DERIVED** is an application hypothesis, not a source theorem or an approved order rule.
- **DISCOVERED / HOLD / BLOCKED** is a research classification. It is not a backtest pass.
- `native_run_id: null`, `native_fill_count: null`, `pf: null` mean **no native evidence for that specific paper formula**. Existing Kelly native fills must not be attached to these entries.
- The current one-day XAUUSD Bid/Ask catalog, synthetic L1 executable sizes and zero commission/slippage cannot establish realistic OOS profitability.
- The unattended Vibe cron is **BLOCKED_DEFAULT_BRANCH**, not running merely because a workflow file exists in PR #46.

## Controlled promotion workflow

1. Add or update the **source Issue** with primary paper reference, equation numbering, originality boundary, assumptions and failure modes.
2. Update `dictionary.json` on a **scoped research branch**. Keep the source ORIGINAL equation separate from AE_DERIVED application code. Validate the index with `python research/math_edge_dictionary/validate_dictionary.py`.
3. When independent inputs exist, create a separate source-faithful strategy adapter with tests; pin source SHA, data SHA and unique candidate/formula hash. Do not rerun identical candidate/data hashes.
4. Verify actual NautilusTrader native fills, finite PF/EV/DD and persisted artifacts. Add realistic commission/slippage and OOS/WFO/Monte Carlo before any promotion.
5. Record **REJECT / HOLD / PASS** with evidence and reviewer approval. Risk Governor remains authoritative. No live orders, secrets, main writes or automatic merge.

**Scope:** This PR introduces only a research index and an offline schema validator. It does **not** modify PR #46, any trading engine, scheduled workflow or risk limit.
