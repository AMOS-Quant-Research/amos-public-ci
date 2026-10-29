# AI-generated AE hypothesis loop — evidence boundary (2026-10-29)

## What is actually running
- Existing original Risk-Constrained Kelly Native BT: real XAUUSD Dukascopy Raw Bid/Ask; NautilusTrader 1.230.0.
- Original MIT Vibe source-only tree (2,934 files) is durably committed to this **research branch**, not merged into main.
- `ai_hypothesis_generator.py` uses the prior ledger's measured PF/EV/DD to rank candidates and proposes new bounded `lambda/momentum/lookback` parameters. Generated parameters are validated as JSON and passed to the native research loop; no AI-generated Python is executed.
- A successful prior loop run #40679168373 produced 3 distinct parameter hypotheses and 3 Native BTs with actual fill evidence.
- `generator=metric_guided_deterministic`, `nim_status=not_configured` in that run. **No external LLM inference was demonstrated.** It is an autonomous *algorithmic* hypothesis loop, not an LLM hypothesis-generation loop.
- The generator now supports both `NVIDIA_NIM_API_KEY` and `NVIDIA_API_KEY` secret aliases and independently records `llm_generated_candidate_count`, `heuristic_generated_candidate_count`, and `llm_hypothesis_generation_verified`. Mocked NVIDIA chat response and no-credential fallback are unit-tested. Mock success is not real NVIDIA inference.
- Model is configured through `NVIDIA_NIM_MODEL` GitHub Actions variable, not a hard-coded model. Secrets are never printed.
- Existing scheduled cron cannot activate until the workflow is reviewed and placed on default branch. Do not merge this 2,934-file PR solely to activate cron.
- AE Math Paper Watch's scheduled report and native strategy parameter search are different: paper **discovery and formalization** remain unverified as automated steps. The existing LLM prompt is only about **parameters of one paper equation**.

## Next acceptance tests (not yet met)
1. Prove real NVIDIA NIM request succeeds using a configured approved GitHub secret and model variable, and evidence says `nim_validated_json` with `llm_generated_candidate_count>=1`.
2. In the **same** run, confirm LLM-proposed candidate SHA, Native fill rows >=1, finite PF/EV/DD, and ledger checkpoint.
3. Run a second **unattended** execution, verify fresh distinct candidate hashes and feedback from the prior actual Native results.
4. Add independent OOS/WFO/MC and calibrated commission/slippage before considering any trading promotion.
5. For genuinely new paper hypotheses, require a separately reviewed mathematical expression, citation, test vectors, and safe typed adapter; do not pretend new lambda/momentum parameters constitute a new paper.
6. Use a minimal standalone reviewed workflow on default branch for scheduled research only after review; retain LIVE OFF.

No paid service enabled; no broker orders; no main merge.


## Verified existing Worker route (source inspection)
- Existing implementation: `Sai310421/MQL5_Project/telegram-command-center/src/worker.js` on main.
- `POST /api/ai` exists but **requires Telegram Mini App initData authorization**; it is NOT a service-to-service API for GitHub Actions.
- `GET /health` only returns a static service status; it does NOT call NVIDIA NIM. Worker deployment/health success cannot prove current NIM inference.
- `askAI` does call NVIDIA NIM using `NVIDIA_NIM_API_KEY` and defaults to `nvidia/nemotron-3-super-120b-a12b`, but returns human-readable error strings for HTTP failures and missing key. The existing `/api/ai` output is conversational text, not validated research candidate JSON.
- Therefore do NOT point the Native BT job at `/health`, and do NOT attempt to bypass Telegram authentication to call `/api/ai`. The research loop needs either an authorized machine-to-machine route with its own narrowly scoped credential or the same NIM credential scoped to its repository; neither route is currently demonstrated end-to-end.
- Prior NIM probe workflow failure in `amos-public-ci` is not evidence that the deployed Worker is down.
