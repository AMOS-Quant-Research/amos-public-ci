"""Evidence-only acceptance gate for actual LLM -> native backtest -> feedback.

Does not confuse heuristic generation or mocked model responses with a real
NVIDIA inference. Outputs BLOCKED (exit 0) when credentials are absent,
FAIL (exit 1) on contradictory evidence, PASS only for real linked results.
"""
import argparse
import json
from pathlib import Path


def verify(proposal_path, ledger_path, summary_path):
    p = json.loads(Path(proposal_path).read_text(encoding="utf-8"))
    l = json.loads(Path(ledger_path).read_text(encoding="utf-8"))
    s = json.loads(Path(summary_path).read_text(encoding="utf-8"))
    if p.get("contract") != "amos.ae.proposal-evidence.v1":
        raise ValueError("bad proposal evidence contract")
    if l.get("contract") != "amos.ae.autonomous-ledger.v1":
        raise ValueError("bad native ledger contract")
    if s.get("contract") != "amos.ae.autonomous-run.v1":
        raise ValueError("bad native summary contract")
    if not p.get("llm_hypothesis_generation_verified"):
        return {"verdict": "BLOCKED", "reason": p.get("ai_provider_status", "LLM_NOT_VERIFIED"),
                "llm_generated": 0, "native_proof": False}
    provider = p.get("generator")
    if provider not in ("openrouter_free", "groq_free") or p.get("ai_provider_status") != provider + "_validated_json":
        raise ValueError("LLM evidence contradicts claimed free-provider success")
    candidates = p.get("candidate_parameters", [])[:p.get("llm_generated_candidate_count", 0)]
    new_results = s.get("new_results", [])
    matched = [r for r in new_results if r.get("plan") in candidates
               and r.get("returncode") == 0 and r.get("native_fills", 0) >= 1
               and r.get("live_trading") is False and r.get("candidate_key")]
    if not matched:
        return {"verdict": "BLOCKED", "reason": "FREE_AI_CANDIDATE_HAS_NO_NATIVE_FILL",
                "llm_generated": len(candidates), "native_proof": False}
    ledger_keys = {r.get("candidate_key") for r in l.get("completed", [])}
    if any(r["candidate_key"] not in ledger_keys for r in matched):
        raise ValueError("Native run not persisted in checkpoint")
    return {"verdict": "PASS", "reason": "FREE_AI_TO_NATIVE_LEDGER",
            "llm_generated": len(candidates), "native_proof": True,
            "matched_candidate_keys": [r["candidate_key"] for r in matched]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--proposal", type=Path, required=True)
    ap.add_argument("--ledger", type=Path, required=True)
    ap.add_argument("--summary", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    try:
        result = verify(args.proposal, args.ledger, args.summary)
    except (ValueError, KeyError, TypeError) as exc:
        result = {"verdict": "FAIL", "reason": str(exc), "native_proof": False}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print("AI_NATIVE_PROOF", json.dumps(result))
    if result["verdict"] == "FAIL":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
