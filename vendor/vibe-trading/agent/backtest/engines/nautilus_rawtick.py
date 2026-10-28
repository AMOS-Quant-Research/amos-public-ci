"""Raw Bid/Ask XAUUSD adapter for Vibe-Trading backtest runs.

This module deliberately does not create a second research loop.  It lets the
existing Vibe ``backtest(run_dir)`` lifecycle delegate execution to a Nautilus
driver, then writes the normal Vibe artifacts and Run Card from measured
evidence.  The driver is supplied as an argv list (never a shell string).
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

EVIDENCE_CONTRACT = "amos.vibe.measured-evidence.v1"


def _fail(message: str) -> None:
    raise ValueError(f"nautilus_rawtick: {message}")


def _require_evidence(payload: Mapping[str, Any]) -> dict[str, Any]:
    if payload.get("contract") != EVIDENCE_CONTRACT:
        _fail("evidence contract mismatch")
    if payload.get("engine") != "NautilusTrader BacktestEngine":
        _fail("NautilusTrader BacktestEngine evidence is required")
    if payload.get("ohlc_resample_used") is not False:
        _fail("Raw Bid/Ask evidence is required; OHLC resampling is forbidden")
    for key in ("raw_ticks", "native_fills"):
        try:
            if int(payload[key]) <= 0:
                _fail(f"{key} must be positive")
        except (KeyError, TypeError, ValueError):
            _fail(f"{key} is required")
    kpis = payload.get("kpis")
    if not isinstance(kpis, Mapping) or not {"PF", "EV", "MaxDD", "MAE", "MFE"}.issubset(kpis):
        _fail("PF, EV, MaxDD, MAE and MFE KPI evidence is required")
    return dict(payload)


def run_nautilus_rawtick(config: Mapping[str, Any], run_dir: Path) -> dict[str, Any]:
    """Execute the configured Nautilus driver and preserve Vibe artifacts.

    ``nautilus_rawtick.driver_command`` must be an argv array.  The driver gets
    the Vibe run directory and must write a measured-evidence JSON document.
    It is responsible for consuming Raw Bid/Ask ticks, applying the explicit
    cost/margin profile, and evaluating ``code/signal_engine.py`` causally.
    """
    if list(config.get("codes") or []) != ["XAUUSD"]:
        _fail("only codes: ['XAUUSD'] is supported")
    spec = config.get("nautilus_rawtick")
    if not isinstance(spec, Mapping):
        _fail("nautilus_rawtick object is required")
    command = spec.get("driver_command")
    if not isinstance(command, list) or not command or not all(isinstance(x, str) and x for x in command):
        _fail("driver_command must be a non-empty argv array")
    if not isinstance(spec.get("cost_model"), Mapping):
        _fail("explicit cost_model is required")
    evidence_path = run_dir / "artifacts" / "nautilus_rawtick_evidence.json"
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    request_path = run_dir / "artifacts" / "nautilus_rawtick_request.json"
    request_path.write_text(json.dumps({"config": dict(config), "live_trading": False}, indent=2), encoding="utf-8")
    result = subprocess.run(
        [*command, "--vibe-run-dir", str(run_dir), "--vibe-request", str(request_path), "--vibe-evidence", str(evidence_path)],
        text=True, capture_output=True, check=False, timeout=int(spec.get("timeout_seconds", 900)),
    )
    (run_dir / "logs").mkdir(parents=True, exist_ok=True)
    (run_dir / "logs" / "nautilus_rawtick_stdout.txt").write_text(result.stdout, encoding="utf-8")
    (run_dir / "logs" / "nautilus_rawtick_stderr.txt").write_text(result.stderr, encoding="utf-8")
    if result.returncode != 0 or not evidence_path.exists():
        _fail(f"driver failed (exit={result.returncode}) or produced no evidence")
    try:
        evidence = _require_evidence(json.loads(evidence_path.read_text(encoding="utf-8")))
    except json.JSONDecodeError as exc:
        _fail(f"invalid evidence JSON: {exc}")
    kpis = evidence["kpis"]
    metrics = {
        "profit_factor": kpis["PF"], "expected_value": kpis["EV"],
        "max_drawdown": kpis["MaxDD"], "mae": kpis["MAE"], "mfe": kpis["MFE"],
        "native_fills": evidence["native_fills"], "raw_ticks": evidence["raw_ticks"],
        "engine": "nautilus_rawtick", "verification_level": "RAW_BIDASK_NAUTILUS",
    }
    pd.DataFrame([metrics]).to_csv(evidence_path.parent / "metrics.csv", index=False)
    trades = evidence.get("trades", [])
    pd.DataFrame(trades if isinstance(trades, list) else []).to_csv(evidence_path.parent / "trades.csv", index=False)
    from backtest.run_card import write_run_card
    write_run_card(run_dir, config, {**metrics, "nautilus_evidence": evidence},
                   data_sources=["XAUUSD Raw Bid/Ask"],
                   strategy_path=run_dir / "code" / "signal_engine.py")
    return metrics
