# AMOS AE closed-loop hypothesis research — v1

## Verified pipeline
1. **Source**: pinned MIT Vibe source-only vendor (2,934 files), original native driver retained unchanged.
2. **Raw data**: pinned XAUUSD Dukascopy Bid/Ask QuoteTicks; reject fewer than 1,000 ticks, backward event timestamps or crossed bid/ask.
3. **Checkpoint**: read last persisted `ledger.json` (GitHub Actions cache restore); check `contract=amos.ae.autonomous-ledger.v1`.
4. **Hypothesis generation**: `ai_hypothesis_generator.py` reads past native PF/EV/MaxDD and proposes three new bounded Kelly hypotheses, with JSON schema and duplicate avoidance. Optional NIM LLM produces *parameters only*, never executable code; deterministic metric-guided proposer takes over if key/model unavailable or output invalid. Evidence explicitly states which path ran.
5. **Paper mapping**: `ae_original_kelly.py` implements the finite-sample log-growth objective and negative-moment constraint of risk-constrained Kelly; momentum policy and historical sample estimator are AMOS research mappings, not a claim of a new original paper.
6. **Native experiment**: `autonomous_research_loop.py` converts proposals into strictly allowlisted strategy parameters; original Vibe NautilusTrader driver is patched only in the isolated research output directory for fractional size, then real native fills/KPI are measured on the Raw Bid/Ask source.
7. **Feedback**: each successful run card (including REJECT/HOLD) is atomically added to the ledger; new run proposes new parameters based on updated evidence. Cache + artifact retain reproducibility, and source/data/driver SHA prevent exact duplicates.
8. **No deployment**: live trading, auto-merge, secrets changes and automatic promotion remain disabled. A positive PF is not a PASS without OOS, realistic costs, risk constraints, and robust statistical testing.

## Operational variables
- GitHub Actions secret `NVIDIA_API_KEY` (optional; do not print it).
- GitHub Actions variable `NVIDIA_NIM_MODEL` (optional; must identify a compatible chat-completions model).
- No secret/model: deterministic adaptive research continues, but **LLM inference is not active**.
- Default workflow: `.github/workflows/ae-vibe-unattended-loop.yml`; `workflow_dispatch` and `schedule: 17 */6 * * *`. **GitHub schedule only runs from the repository default branch**. A Draft PR's successful pull-request workflow does not mean cron is enabled.
- Artifacts: `proposed_candidates.json`, `proposed_candidates.evidence.json`, `ledger.json`, `autonomous_summary.json`, native per-candidate `run_card.json` and evidence.
- The six-hour GitHub schedule is a *planned deployment* until the workflow is reviewed and safely installed on default branch. No unconditional automatic merge is authorized.

## Research integrity
- Hypotheses are **Kelly-family parameter hypotheses**, not new published mathematics or a self-discovered theorem.
- Historical performance feedback is an exploration heuristic only; optimizing repeatedly on the same sample introduces multiple-testing/overfitting risk.
- Real spread is present in Bid/Ask, but broker-specific L1 volume is not; commission and slippage are set to zero, and no out-of-sample/WFO/Monte Carlo validation is included. This evidence must remain `HOLD_OOS_AND_COSTS` rather than deployed alpha.
- If the NIM path is not configured, the generator reports `nim_status=not_configured` and `generator=metric_guided_deterministic`. Never describe this as verified LLM hypothesis generation.
- To extend to a genuinely different AE paper formula, create a **new reviewed strategy template with independent unit tests** and explicit source attribution; never let untrusted LLM output execute as Python.
