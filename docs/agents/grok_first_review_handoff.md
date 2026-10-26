# Grok first review — execution-ready handoff (proposal only)

## Goal
Independently review AMOS component inventory and Task/Signal/Result contracts. Identify missing evidence, duplicate implementations, interface mismatches, security and cost risks. Do not implement or modify code.

## Verified starting point
- Repository: AMOS-Quant-Research/amos-public-ci
- Review source: docs/agents/grok_independent_review_v1.md
- Proposed PR: #40 (draft)
- Central coordination: Sai310421/MQL5_Project Issue #30
- The inventory and contract documents below were NOT found at their proposed default-branch paths during preparation. Do not assume they exist.

## Read-only files to inspect
1. docs/agents/grok_independent_review_v1.md on branch docs/grok-review-contract-20261026
2. docs/architecture/component_inventory.md (if present; otherwise report MISSING)
3. docs/contracts/task_v1.schema.json (if present; otherwise report MISSING)
4. docs/contracts/signal_v1.schema.json (if present; otherwise report MISSING)
5. docs/contracts/result_v1.schema.json (if present; otherwise report MISSING)
6. Existing relevant contract files found by actual repository inventory; cite exact paths.

## Interface
Input: review_request.v1 as specified in grok_independent_review_v1.md; source revision MUST be pinned to an exact commit SHA.
Output: review_result.v1 with finding severity, evidence path/SHA/line, proposed fix, reproducible verification, and explicit unverified items.
Never invent source paths, test commands, run IDs, schemas, or a successful GitHub connection.

## Completion criteria
- [ ] GitHub read access tested and outcome recorded (success/failure, exact path/ref)
- [ ] All five candidate paths checked; missing files identified
- [ ] Existing contracts inventoried by path and SHA, or NOT VERIFIED stated
- [ ] At least one valid review_result.v1 produced (zero findings is allowed if justified)
- [ ] Findings distinguish implemented, integrated, CI-tested, and live-running
- [ ] Proposed OpenCode follow-up tasks name exact files, interfaces, tests, and forbidden changes
- [ ] Evidence and limits recorded; no claimed test PASS without an actual run URL/log

## Forbidden
No main push, merge, new secrets, billing, live order activation, deployment, or changes to CoreAI/Nautilus/T-QUEUE/Risk Governor. No disclosure of private material into this public repo.

## Suggested response for Grok
Review PR #40 against the rules above. First verify your GitHub read access and enumerate real paths. If GitHub cannot be accessed, stop and return ACCESS_NOT_VERIFIED with the exact blocker. Do not replace repository evidence with guesses. Report review_result.v1 and concrete next OpenCode tasks only.
