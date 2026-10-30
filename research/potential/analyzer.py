"""AMOS potential preflight: research priority, never performance scoring or orders."""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path

CONTRACT = "amos.potential.preflight.v1"
DIMENSIONS = (
    "thesis_clarity", "causal_mechanism", "data_availability",
    "signal_specification", "execution_feasibility", "cost_testability",
    "risk_specification", "overfit_controls", "confluence_identifiability",
)
WEIGHTS = {
    "thesis_clarity": 1, "causal_mechanism": 2, "data_availability": 2,
    "signal_specification": 2, "execution_feasibility": 2,
    "cost_testability": 2, "risk_specification": 2,
    "overfit_controls": 1, "confluence_identifiability": 1,
}
REQUIRED = ("id", "thesis", "mechanism", "market", "timeframe", "entry",
            "exit", "data", "costs", "risk", "validation")
FORBIDDEN = ("expected_profit", "estimated_win_rate", "projected_pf")

def _present(value):
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return bool(value)
    return value is not None and not isinstance(value, bool)

def _item(source):
    if not isinstance(source, dict):
        raise ValueError("source must be object")
    if not isinstance(source.get("id"), str) or not source["id"].strip():
        raise ValueError("source.id required")
    if any(k in source for k in FORBIDDEN):
        raise ValueError("unsupported speculative performance fields")
    data = source.get("data") if isinstance(source.get("data"), dict) else {}
    costs = source.get("costs") if isinstance(source.get("costs"), dict) else {}
    risk = source.get("risk") if isinstance(source.get("risk"), dict) else {}
    validation = source.get("validation") if isinstance(source.get("validation"), dict) else {}
    signals = source.get("signals") if isinstance(source.get("signals"), list) else []
    checks = {
        "thesis_clarity": _present(source.get("thesis")),
        "causal_mechanism": _present(source.get("mechanism")),
        "data_availability": _present(data.get("source")) and data.get("bid_ask") is True,
        "signal_specification": _present(source.get("entry")) and _present(source.get("exit")),
        "execution_feasibility": _present(source.get("market")) and _present(source.get("timeframe")) and _present(source.get("execution")),
        "cost_testability": all(_present(costs.get(k)) for k in ("spread", "slippage", "commission")),
        "risk_specification": all(_present(risk.get(k)) for k in ("max_loss", "stop_rule")),
        "overfit_controls": all(_present(validation.get(k)) for k in ("oos", "wfo")),
        "confluence_identifiability": bool(signals) and all(isinstance(s, str) and s.strip() for s in signals),
    }
    missing = [k for k in REQUIRED if not _present(source.get(k))]
    missing += [k for k, v in checks.items() if not v]
    missing = sorted(set(missing))
    points = sum(WEIGHTS[k] for k, v in checks.items() if v)
    total = sum(WEIGHTS.values())
    blockers = [k for k in ("data_availability", "signal_specification", "risk_specification") if not checks[k]]
    verdict = "BLOCKED" if blockers else ("READY_FOR_NATIVE_BT" if points == total else "NEEDS_REFINEMENT")
    return {
        "id": source["id"], "checks": checks, "evidence_coverage": {"met_weight": points, "total_weight": total},
        "verdict": verdict, "missing": missing, "blockers": blockers,
        "signals": signals, "confluence": source.get("confluence", []),
        "note": "Research readiness only; no inferred win rate, PF, EV or profitability.",
    }

def analyze(payload):
    if not isinstance(payload, dict) or payload.get("contract") != "amos.potential.input.v1":
        raise ValueError("invalid input contract")
    sources = payload.get("sources")
    if not isinstance(sources, list) or not 1 <= len(sources) <= 100:
        raise ValueError("sources must contain 1..100 entries")
    ids = [s.get("id") for s in sources if isinstance(s, dict)]
    if len(ids) != len(sources) or len(set(ids)) != len(ids):
        raise ValueError("source ids must be unique")
    by_source = [_item(s) for s in sources]
    by_confluence = []
    for pair in payload.get("confluences", []):
        if not isinstance(pair, dict) or not isinstance(pair.get("id"), str):
            raise ValueError("invalid confluence")
        members = pair.get("members")
        if not isinstance(members, list) or len(members) < 2 or len(set(members)) != len(members) or not set(members).issubset(ids):
            raise ValueError("confluence members invalid")
        named = [s for s in sources if s["id"] in members]
        common = set(named[0].get("signals") or [])
        for s in named[1:]:
            common &= set(s.get("signals") or [])
        by_confluence.append({
            "id": pair["id"], "members": members, "shared_signal_labels": sorted(common),
            "simultaneous_execution_interaction": "NOT_MEASURED",
            "correlation": None, "diversification_benefit": None,
            "required_evidence": ["timestamp_aligned_signals", "position_exposure", "native_fill_ledger"],
            "verdict": "NEEDS_EMPIRICAL_INTERACTION_TEST",
        })
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, allow_nan=False)
    return {
        "contract": CONTRACT, "input_sha256": hashlib.sha256(canonical.encode()).hexdigest(),
        "research_only": True, "live_trading": False, "order_permission": "DENIED",
        "score_owner": "NautilusTrader", "native_bt_executed": False,
        "profitability_claim": "NOT_ASSESSED", "by_source": by_source, "by_confluence": by_confluence,
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    result = analyze(payload)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    print("POTENTIAL_PREFLIGHT_OK", len(result["by_source"]), len(result["by_confluence"]))

if __name__ == "__main__":
    main()
