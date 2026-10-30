# AMOS Potential Analyzer — research preflight

**Placement:** immediately after natural-language strategy intake (Vibe-Trading) and before TradingAgents / other research agents.

This module answers **"is the hypothesis sufficiently specified and evidence-ready to spend resources testing?"**, **not** "will it make money?". It is a deterministic research-readiness preflight, not a predictive profitability model.

Run: `python -m research.potential.analyzer --input research/potential/example_input.json --output potential_result.json`.

The nine checks are thesis clarity, causal mechanism, verified Bid/Ask data availability, entry/exit specification, execution feasibility, cost testability, risk specification, OOS/WFO controls, and identifiable confluence signals. Missing required inputs block or request refinement. No strategy is silently rejected for low hypothetical profitability. `by_source` records readiness and missing evidence; `by_confluence` records only shared signal labels and requirements for future empirical interaction testing.

**Boundary:** NautilusTrader is the only performance scorer. Potential is not optimization, performance scoring, or measurement of simultaneous strategy interactions. No execution or order permission. The upstream language model may create structured hypotheses, but it must not supply invented returns or performance statistics. Candidate improvement may reuse this module before actual native BT.
