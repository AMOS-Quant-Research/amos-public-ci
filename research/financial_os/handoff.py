"""AMOS Financial OS research handoff: evidence-only integration contract.

No live orders. AI proposals are never treated as validated strategies.
Only measured native backtests may be promoted to the research library.
"""
import argparse
import json
from pathlib import Path

CONTRACT = "amos.financial-os.research-handoff.v1"
REQUIRED = ("strategy_id", "hypothesis", "parameter_set", "dataset_sha256",
            "raw_tick_count", "native_fill_count", "oos_evidence",
            "cost_calibration", "risk_evidence", "reproducibility_evidence")


def evaluate(proposal, evidence):
    missing = [key for key in REQUIRED if not evidence.get(key)]
    if not proposal.get("strategy_id") or proposal.get("strategy_id") != evidence.get("strategy_id"):
        missing.append("strategy_id_match")
    if not isinstance(evidence.get("raw_tick_count"), int) or evidence.get("raw_tick_count", 0) < 1000:
        missing.append("raw_tick_count>=1000")
    if not isinstance(evidence.get("native_fill_count"), int) or evidence.get("native_fill_count", 0) < 1:
        missing.append("native_fill_count>=1")
    for k in ("pf", "win_rate", "max_dd"):
        v = evidence.get(k)
        if not isinstance(v, (int, float)) or isinstance(v, bool) or not __import__("math").isfinite(v):
            missing.append(k)
    if evidence.get("source_kind") != "REAL_SIGNALS_REAL_RAW_TICKS":
        missing.append("real_signal_raw_tick_provenance")
    if evidence.get("synthetic") is not False:
        missing.append("synthetic_false")
    if evidence.get("live_trading") is not False:
        missing.append("live_trading_false")
    return {"contract": CONTRACT, "strategy_id": proposal.get("strategy_id"),
            "status": "RESEARCH_EVIDENCE_READY" if not missing else "BLOCKED",
            "missing_or_invalid": sorted(set(missing)), "live_trading": False,
            "deployment_approved": False, "edge_library_promotion": False,
            "note": "Research evidence readiness only; independent risk approval required."}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--proposal", type=Path, required=True)
    p.add_argument("--evidence", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    result = evaluate(json.loads(a.proposal.read_text()), json.loads(a.evidence.read_text()))
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps(result))
    return 0 if result["status"] == "RESEARCH_EVIDENCE_READY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
