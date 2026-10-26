# AMOS OpenCode fallback protocol v1.0

Status: PROPOSED. OpenCode error details and replacement agent runtime are not yet verified.
Date: 2026-10-26 JST.

## Objective
Continue safe, reviewable AMOS development when OpenCode errors and Dispatch (= Claude Code) has exhausted its token budget. GPT prepares narrow patches and tests; GitHub Actions verifies where a trusted, working runner exists; Grok Build remains independent auditor. Do not claim that a replacement agent is running until proven.

## Role map
- GPT: spec, patch preparation, tests where accessible, PR creation, acceptance.
- Dispatch = Claude Code: one actor, currently unavailable.
- OpenCode: unavailable until error diagnosed.
- Grok Build: independent audit only, no automatic promotion to implementation authority.
- GitHub Actions: CI evidence; availability determined per repo and run, not by name.

## Work contract (required per task)
1. Exact repository, base commit SHA, branch, file paths allowed.
2. Interface: schema, inputs/outputs, error semantics, backward compatibility.
3. Acceptance: runnable test commands, expected assertions, CI run URL, artifacts.
4. Forbidden: main direct push, unapproved merge, secret changes, live trading, billing, production deploy, approved contract replacement.
5. Recovery: if a file/runner/dependency is absent, record BLOCKED with evidence and isolate a minimal alternative.

## Fallback execution path
1. Inspect current issue, source files, active PRs, and run evidence.
2. Create scoped feature branch from the verified base.
3. Make only permitted changes; preserve existing CoreAI, Nautilus, T-QUEUE and Risk Governor.
4. Validate syntax/schema locally when possible; CI run on trusted available runner.
5. Save test logs, SHA, workflow URL, failures, and deviations.
6. Request independent Grok review. Keep PR draft until tests and acceptance evidence exist.
7. Return task status PASS / CONDITIONAL / FAIL / BLOCKED; never infer a PASS from a successful commit.

## First recovery task: OpenCode failure classification
Input: exact OpenCode error text or failing GitHub Actions run URL.
Classify: auth/credits, API model, rate limit, workflow dispatch, GitHub permission, runner quota, dependency/install, test failure, PR write conflict.
Output: root cause with supporting log lines; minimal safe fix and regression test.
Do not regenerate keys, disable safeguards, or repeatedly retry paid calls.

## Minimal E2E test (no live trading)
Task JSON -> validation -> mock worker -> Result JSON -> artifact -> GitHub CI status.
Existing contracts take precedence; no new incompatible schemas without an adapter and migration tests.

## Exit criteria
- [ ] Error evidence captured, category and root cause documented
- [ ] Existing task/signal/result contracts checked for compatibility
- [ ] One scoped implementation PR created
- [ ] Actual CI run logs and tests recorded (or BLOCKED with precise reason)
- [ ] Grok review result recorded
- [ ] Main remains unchanged, live trading remains OFF
