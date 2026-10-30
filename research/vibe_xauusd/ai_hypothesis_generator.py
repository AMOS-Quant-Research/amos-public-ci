"""AMOS closed-loop AE hypothesis proposer (research-only).

LLM path: free-tier OpenRouter/Groq adapter, JSON parameters only.
Without configured model/key, a deterministic metric-driven search proposes
new, bounded hypotheses. Never execute generated Python or trading orders.
Proposals are NOT paper discoveries or independently validated EDGE.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import random
from free_ai_adapter import propose_free

HERE = Path(__file__).resolve().parent
CONTRACT = "amos.ae.candidate-registry.v1"


def valid(p):
    if not isinstance(p, dict) or set(p) != {"lambda", "momentum", "lookback"}:
        return False
    if type(p["lambda"]) not in (float, int) or type(p["momentum"]) is not int or type(p["lookback"]) is not int:
        return False
    return (math.isfinite(p["lambda"]) and 0.1 <= p["lambda"] <= 5
            and 2 <= p["momentum"] <= 30 and 30 <= p["lookback"] <= 500)


def key(p):
    return (round(float(p["lambda"]), 4), p["momentum"], p["lookback"])


def load_ledger(path):
    if not path.exists():
        return []
    d = json.loads(path.read_text(encoding="utf-8"))
    if d.get("contract") != "amos.ae.autonomous-ledger.v1":
        raise ValueError("unrecognized research ledger")
    return d["completed"]


def existing_registry(path):
    d = json.loads(path.read_text(encoding="utf-8"))
    if d.get("contract") != CONTRACT:
        raise ValueError("unrecognized candidate registry")
    if not all(valid(x) for x in d["candidates"]):
        raise ValueError("invalid committed candidate")
    return d["candidates"]


def rank(completed):
    eligible = []
    for r in completed:
        p, k = r.get("plan"), r.get("kpis") or {}
        if not valid(p) or r.get("returncode") != 0:
            continue
        pf, ev, dd = k.get("PF"), k.get("EV"), k.get("MaxDD")
        if not all(isinstance(v, (int, float)) and math.isfinite(v) for v in (pf, ev, dd)):
            continue
        # Exploration ranking only, NOT an edge qualification metric.
        score = math.log(max(float(pf), 0.01)) + float(ev) / 100 - max(float(dd), 0) / 1000
        eligible.append((score, p))
    return [p for _, p in sorted(eligible, key=lambda x: x[0], reverse=True)]


def heuristic(completed, already, n):
    leaders = rank(completed)
    anchors = leaders[:3] or [{"lambda": 1.0, "momentum": 5, "lookback": 80}]
    seed = int(hashlib.sha256(json.dumps(sorted(map(key, already)), sort_keys=True).encode()).hexdigest()[:16], 16)
    rng = random.Random(seed)
    seen = set(map(key, already))
    proposed = []
    for _ in range(300):
        if len(proposed) >= n:
            break
        a = rng.choice(anchors)
        lam = round(min(5.0, max(0.1, float(a["lambda"]) + rng.choice([-0.75, -0.5, -0.25, 0.25, 0.5, 0.75]))), 4)
        momentum = min(30, max(2, int(a["momentum"]) + rng.choice([-5, -3, -2, -1, 1, 2, 3, 5])))
        lookback = min(500, max(30, int(a["lookback"]) + rng.choice([-40, -20, -10, 10, 20, 40])))
        p = {"lambda": lam, "momentum": momentum, "lookback": lookback}
        if valid(p) and key(p) not in seen:
            seen.add(key(p))
            proposed.append(p)
    return proposed


def propose(ledger_path, registry_path, output_path, count):
    if not 1 <= count <= 10:
        raise ValueError("count must be 1..10")
    completed = load_ledger(ledger_path)
    registry = existing_registry(registry_path)
    already = [x["plan"] for x in completed if valid(x.get("plan"))] + registry
    prompt = ("Research-only. Return JSON object with candidates list of " + str(count) +
              " objects with lambda float [0.1,5], momentum integer [2,30], lookback integer [30,500]. " +
              "Do not repeat existing plans. Historical Native BT: " +
              json.dumps([{"plan": r.get("plan"), "kpis": r.get("kpis")} for r in completed[-25:]], allow_nan=False)[:6500] +
              " Existing: " + json.dumps(list(map(key, already))[-120:]))
    model, status = propose_free(prompt, count, valid, key, already)
    chosen = list(model or [])
    model_candidate_count = len(chosen)
    source = status.split("_validated_json")[0] if chosen else "metric_guided_deterministic"
    if len(chosen) < count:
        chosen += heuristic(completed, already + chosen, count - len(chosen))
    if len(chosen) != count:
        raise RuntimeError("unable to find distinct bounded hypotheses")
    payload = {"contract": CONTRACT, "candidates": chosen}
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, allow_nan=False), encoding="utf-8")
    report = {"contract": "amos.ae.proposal-evidence.v1", "generator": source,
              "llm_generated_candidate_count": model_candidate_count,
              "heuristic_generated_candidate_count": len(chosen) - model_candidate_count,
              "llm_hypothesis_generation_verified": model_candidate_count > 0,
              "nim_status": "not_invoked", "ai_provider_status": status, "candidate_count": len(chosen),
              "historical_native_results": len(completed),
              "historical_feedback_used": bool(rank(completed)),
              "input_ledger_sha256": hashlib.sha256(ledger_path.read_bytes()).hexdigest() if ledger_path.exists() else None,
              "candidate_parameters": chosen,
              "paper_original_math": "RC_KELLY_OBJECTIVE_AND_MOMENT",
              "strategy_mapping": "rolling sample-average Kelly on M5 momentum",
              "out_of_sample": False, "costs_calibrated": False,
              "live_trading": False, "promotion_allowed": False}
    output_path.with_suffix(".evidence.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--ledger", type=Path, required=True)
    p.add_argument("--registry", type=Path, default=HERE / "ae_candidate_registry.json")
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--count", type=int, default=3)
    a = p.parse_args()
    propose(a.ledger, a.registry, a.output, a.count)
