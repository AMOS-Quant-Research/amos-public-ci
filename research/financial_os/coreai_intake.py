"""Evidence-only Nautilus research -> AMOS CoreAI intake package.

This creates a verifiable, non-executable handoff artifact. It does not assert
CoreAI received anything, nor authorize orders. Fail closed on missing proof.
"""
import argparse
import hashlib
import json
from pathlib import Path
from research.financial_os.handoff import evaluate

def build(proposal, evidence):
    decision = evaluate(proposal, evidence)
    payload = {
        "contract": "amos.coreai.research-intake.v1",
        "strategy_id": proposal.get("strategy_id"),
        "research_decision": decision,
        "provenance": {
            "dataset_sha256": evidence.get("dataset_sha256"),
            "source_kind": evidence.get("source_kind"),
            "native_fill_count": evidence.get("native_fill_count"),
            "raw_tick_count": evidence.get("raw_tick_count"),
        },
        "metrics": {k: evidence.get(k) for k in ("pf", "win_rate", "max_dd")},
        "delivery_status": "NOT_DELIVERED",
        "coreai_acknowledged": False,
        "coreai_connector_verified": False,
        "live_trading": False,
        "order_permission": "DENIED",
        "risk_governor_approval": False,
    }
    if decision["status"] != "RESEARCH_EVIDENCE_READY":
        payload["intake_status"] = "BLOCKED"
        payload["metrics"] = {"pf": None, "win_rate": None, "max_dd": None}
    else:
        payload["intake_status"] = "READY_FOR_COREAI_INTAKE"
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()
    payload["content_sha256"] = hashlib.sha256(canonical).hexdigest()
    return payload

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--proposal", required=True, type=Path)
    p.add_argument("--evidence", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    a = p.parse_args()
    payload = build(json.loads(a.proposal.read_text()), json.loads(a.evidence.read_text()))
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False)+"\n")
    print(json.dumps({"intake_status":payload["intake_status"],"delivery_status":payload["delivery_status"],
                      "content_sha256":payload["content_sha256"]}))
    return 0 if payload["intake_status"] == "READY_FOR_COREAI_INTAKE" else 2

if __name__ == "__main__":
    raise SystemExit(main())
