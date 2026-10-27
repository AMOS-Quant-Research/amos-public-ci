"""Non-live execution boundary for external Nautilus raw-tick research drivers."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from .gateway import prepare_research_run
from .math_edge import MathEdgeHypothesis, validate_math_evidence

RESEARCH_CONTRACT = "amos.vibe.research-run.v1"
EVIDENCE_CONTRACT = "amos.vibe.measured-evidence.v1"


def _write_json(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def _evidence_gate(payload: Mapping[str, object], require_math_validation: bool) -> tuple[bool, str]:
    """Reject unmeasured, proxy, or live-capable outputs before risk review."""
    if payload.get("contract") != EVIDENCE_CONTRACT:
        return False, "EVIDENCE_CONTRACT_MISMATCH"
    if payload.get("live_trading") is not False:
        return False, "LIVE_TRADING_MUST_BE_FALSE"
    if payload.get("engine") != "NautilusTrader BacktestEngine":
        return False, "NAUTILUS_ENGINE_EVIDENCE_REQUIRED"
    if payload.get("ohlc_resample_used") is not False:
        return False, "RAW_BIDASK_EVIDENCE_REQUIRED"
    try:
        raw_ticks = int(payload["raw_ticks"])
        fills = int(payload["native_fills"])
    except (KeyError, TypeError, ValueError):
        return False, "RAW_TICKS_AND_NATIVE_FILLS_REQUIRED"
    if raw_ticks <= 0:
        return False, "NO_RAW_TICKS"
    if fills <= 0:
        return False, "NO_NATIVE_FILLS"
    kpis = payload.get("kpis")
    if not isinstance(kpis, Mapping):
        return False, "KPI_OBJECT_REQUIRED"
    required = {"PF", "EV", "MaxDD", "MAE", "MFE"}
    if not required.issubset(kpis):
        return False, "INCOMPLETE_KPI_EVIDENCE"
    if require_math_validation:
        return validate_math_evidence(payload)
    return True, "MEASURED_EVIDENCE_READY_FOR_RISK_REVIEW"


def execute_research_pipeline(
    proposal: Mapping[str, object],
    cost_model: Mapping[str, object],
    ticks: Iterable[Mapping[str, object]],
    lots: object,
    driver_command: Sequence[str],
    work_dir: str | Path,
    min_ticks: int = 1_000,
    math_hypothesis: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Run a configured, external driver and emit an approval *candidate*.

    The driver receives ``--amos-request <path> --amos-evidence <path>`` and
    must write a measured evidence document conforming to ``EVIDENCE_CONTRACT``.
    No subprocess shell is used, and no broker credentials or order endpoint
    can enter this function.
    """
    work = Path(work_dir)
    ticks_list = list(ticks)
    preflight = prepare_research_run(proposal, cost_model, ticks_list, lots, min_ticks=min_ticks)
    math = MathEdgeHypothesis.from_mapping(math_hypothesis) if math_hypothesis is not None else None
    request_path = work / "request.json"
    evidence_path = work / "measured_evidence.json"
    candidate_path = work / "risk_governor_candidate.json"
    base = {
        "contract": RESEARCH_CONTRACT,
        "live_trading": False,
        "proposal": dict(proposal),
        "cost_model": dict(cost_model),
        "lots": str(lots),
        "preflight": preflight.as_dict(),
    }
    if math is not None:
        base["math_edge_hypothesis"] = math.as_dict()
    _write_json(request_path, base)
    if not preflight.accepted:
        candidate = {"contract": "amos.approved-order-candidate.v1", "live_trading": False,
                     "status": "REJECTED", "reason": preflight.reason, "request": str(request_path)}
        _write_json(candidate_path, candidate)
        return candidate
    if not driver_command:
        raise ValueError("driver_command is required")
    command = [*driver_command, "--amos-request", str(request_path), "--amos-evidence", str(evidence_path)]
    process = subprocess.run(command, cwd=work, text=True, capture_output=True, check=False, timeout=900)
    if process.returncode != 0 or not evidence_path.exists():
        candidate = {"contract": "amos.approved-order-candidate.v1", "live_trading": False,
                     "status": "REJECTED", "reason": "DRIVER_FAILED_OR_NO_EVIDENCE",
                     "driver_returncode": process.returncode, "request": str(request_path)}
        _write_json(candidate_path, candidate)
        return candidate
    try:
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        candidate = {"contract": "amos.approved-order-candidate.v1", "live_trading": False,
                     "status": "REJECTED", "reason": f"INVALID_EVIDENCE: {exc}", "request": str(request_path)}
        _write_json(candidate_path, candidate)
        return candidate
    accepted, reason = _evidence_gate(evidence, require_math_validation=math is not None)
    candidate = {
        "contract": "amos.approved-order-candidate.v1",
        "live_trading": False,
        "status": "CANDIDATE_FOR_RISK_GOVERNOR" if accepted else "REJECTED",
        "reason": reason,
        "request": str(request_path),
        "evidence": str(evidence_path),
        "kpis": evidence.get("kpis") if accepted else None,
    }
    _write_json(candidate_path, candidate)
    return candidate
