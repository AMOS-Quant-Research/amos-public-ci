# AMOS Grok Independent Review Contract v1.0

Status: PROPOSED — no Grok GitHub connection or autonomous execution verified.
Owner: AMOS Central. Scope: design/PR review only. No trading or deployment.

## Shared source of truth
- Approved specs and evidence: this repository, referenced by exact commit SHA.
- Central coordination: Sai310421/MQL5_Project Issue #30.
- Do not copy private strategies, credentials, user data, or account details into public repositories.
- All findings must cite exact repository/path/commit or GitHub Run URL; otherwise label UNVERIFIED.

## Responsibility split
- GPT: architecture and acceptance criteria.
- Claude Code: detailed interface contracts and review.
- Grok: independent adversarial design/security/cost review; **proposals only**.
- OpenCode: implementation, tests, repairs in a scoped worktree.
- Dispatch: inventory, dependencies, task handoff.
- GitHub Actions: verifiable CI evidence.
- AMOS Central: approvals and integration.

## Grok input contract (review_request.v1)
```json
{
  "schema_version": "1.0",
  "review_id": "REVIEW-0001",
  "repo": "AMOS-Quant-Research/amos-public-ci",
  "commit_sha": "<40-hex>",
  "issue_url": "https://github.com/Sai310421/MQL5_Project/issues/30",
  "scope_paths": ["docs/"],
  "interfaces": ["Task", "Signal", "Result"],
  "required_tests": ["schema validation", "compatibility tests"],
  "forbidden_changes": ["main push", "merge", "secrets", "live trading", "billing"]
}
```

## Grok output contract (review_result.v1)
```json
{
  "schema_version": "1.0",
  "review_id": "REVIEW-0001",
  "status": "reviewed",
  "findings": [
    {
      "severity": "medium",
      "category": "interface",
      "claim": "Example finding",
      "evidence": {"repo": "owner/repo", "path": "docs/example.md", "commit_sha": "<40-hex>", "line": 10},
      "proposed_fix": "Non-destructive proposal",
      "verification": "Named test or reproducible command"
    }
  ],
  "unverified": ["GitHub write access", "actual model execution"]
}
```

## Mandatory review checklist
1. Files to touch: enumerate exact paths. Unknown paths => request inventory first.
2. Interfaces: inputs/outputs, schema_version, error semantics, backwards compatibility.
3. Done means: named test commands, expected results, logs and CI run links.
4. Forbidden: duplicate reimplementation of CoreAI/Nautilus/T-QUEUE/Risk Governor; changes to secrets, permissions, payments, live order enablement, main push or merge.
5. Verify Runner and quotas from actual GitHub run evidence, not repository names.
6. Distinguish code present / connected / tested / running; do not infer execution from a PR.
7. Any unverified claim must be explicitly marked UNVERIFIED.

## First assignment
Review the existing AMOS component inventory and Task/Signal/Result schemas after they are produced.
Return a prioritized list of contract incompatibilities, duplicate implementations, unconnected adapters, and missing tests.
Produce recommendations only; do not edit code or approve trading.
