"""Public synthetic train-only WFO and fail-closed result-envelope contract.

Not a Nautilus run, not an independent certification of private source.
"""
import hashlib
import json
import math

from public_research_contract import trade_metrics, bootstrap_dd_p95


def walk_forward(candidates, *, train_size, test_size, starting_equity=1000.0):
    if not isinstance(candidates, dict) or len(candidates) < 2:
        raise ValueError("Need at least two candidates")
    names = sorted(candidates)
    first = candidates[names[0]]
    if train_size < 2 or test_size < 1 or len(first) < train_size + test_size:
        raise ValueError("Insufficient history")
    # Explicit per-observation timestamps, identical across all candidates.
    timeline = [x["timestamp"] for x in first]
    if len(set(timeline)) != len(timeline) or timeline != sorted(timeline):
        raise ValueError("Nonunique or unsorted timestamps")
    for name in names:
        rows = candidates[name]
        if len(rows) != len(timeline) or [x["timestamp"] for x in rows] != timeline:
            raise ValueError("Candidate market timestamps mismatch")
        if any(not isinstance(x.get("net_pnl"), (int, float)) or
               isinstance(x.get("net_pnl"), bool) or
               not math.isfinite(x["net_pnl"]) for x in rows):
            raise ValueError("Nonfinite net PnL")
    folds, oos_pnl = [], []
    for start in range(0, len(timeline) - train_size - test_size + 1, test_size):
        train_end = start + train_size
        test_end = train_end + test_size
        train_scores = {name: sum(x["net_pnl"] for x in candidates[name][start:train_end])
                        for name in names}
        # Deterministic tie-break, using TRAIN only; OOS cannot affect selection.
        winner = min(names, key=lambda n: (-train_scores[n], n))
        tested = [x["net_pnl"] for x in candidates[winner][train_end:test_end]]
        oos_pnl.extend(tested)
        folds.append({"parameter": winner, "train": [start, train_end],
                      "test": [train_end, test_end],
                      "oos": trade_metrics(tested, starting_equity)})
    return {"folds": folds, "oos": trade_metrics(oos_pnl, starting_equity),
            "monte_carlo_dd_p95_pct": bootstrap_dd_p95(oos_pnl, seed=42),
            "validation": "SYNTHETIC_CONTRACT_ONLY",
            "execution_allowed": False, "virtual_entry_enabled": False}


def public_result_envelope(result, *, source_commit):
    """Provenance label for public tests only. Not a cryptographic attestation."""
    if not isinstance(source_commit, str) or len(source_commit) != 40 or any(
            ch not in "0123456789abcdef" for ch in source_commit.lower()):
        raise ValueError("Full Git commit SHA required")
    if result.get("validation") != "SYNTHETIC_CONTRACT_ONLY":
        raise ValueError("Only synthetic contract results supported")
    payload = json.dumps(result, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return {"source_commit": source_commit, "result_sha256": hashlib.sha256(payload.encode()).hexdigest(),
            "validation": "SYNTHETIC_CONTRACT_ONLY", "engine_verified": False,
            "execution_allowed": False, "virtual_entry_enabled": False}
