"""Run AMOS independent Overnight Drift through the Raw Bid/Ask Nautilus driver."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

def run(catalog: Path, output: Path, commission_per_lot: float = 0.0) -> dict:
    catalog = Path(catalog).resolve()
    if not catalog.exists():
        raise FileNotFoundError("actual Nautilus ParquetDataCatalog missing")
    if commission_per_lot < 0:
        raise ValueError("negative commission")
    output = Path(output).resolve()
    run_dir = output / "overnight_drift_run"
    code_dir = run_dir / "code"
    artifact_dir = run_dir / "artifacts"
    code_dir.mkdir(parents=True, exist_ok=True)
    artifact_dir.mkdir(parents=True, exist_ok=True)

    strategy_source = Path(__file__).with_name("tradebydata_overnight_drift.py").read_text(encoding="utf-8")
    (code_dir / "signal_engine.py").write_text(strategy_source, encoding="utf-8")
    cost = {
        "commission_per_lot_usd": commission_per_lot,
        "slippage_probability": 0.0,
        "slippage_points_per_side": 0.0,
        "margin_rate": 0.005,
        "max_leverage": 200,
    }
    request = {
        "config": {
            "codes": ["XAUUSD"],
            "engine": "nautilus_rawtick",
            "nautilus_rawtick": {
                "catalog_path": str(catalog),
                "lots": 0.01,
                "trade_units": 1,
                "initial_cash": 10000,
                "cost_model": cost,
            },
        },
        "live_trading": False,
    }
    request_path = artifact_dir / "request.json"
    evidence_path = artifact_dir / "nautilus_rawtick_evidence.json"
    request_path.write_text(json.dumps(request, indent=2), encoding="utf-8")
    driver = Path(__file__).with_name("nautilus_vibe_driver.py")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[2]) + os.pathsep + env.get("PYTHONPATH", "")
    proc = subprocess.run(
        [sys.executable, str(driver), "--vibe-run-dir", str(run_dir),
         "--vibe-request", str(request_path), "--vibe-evidence", str(evidence_path)],
        text=True, capture_output=True, timeout=1200, env=env,
    )
    (artifact_dir / "driver.log").write_text(proc.stdout + "\n--- STDERR ---\n" + proc.stderr, encoding="utf-8")
    if proc.returncode != 0 or not evidence_path.exists():
        raise RuntimeError("NATIVE_BT_FAILED; inspect overnight_drift_run/artifacts/driver.log")
    native = json.loads(evidence_path.read_text(encoding="utf-8"))
    fills = int(native.get("diagnostics", {}).get("fills_report_rows", 0))
    if native.get("engine") != "NautilusTrader BacktestEngine" or native.get("ohlc_resample_used") is not False:
        raise ValueError("invalid native backtest evidence")
    if int(native.get("raw_ticks", 0)) < 1000 or fills < 1:
        raise ValueError("insufficient QuoteTicks or zero native fills")
    result = {
        "contract": "amos.independent-hypothesis.native-research.v1",
        "strategy": "OVERNIGHT_DRIFT_V1",
        "origin": "AMOS independent hypothesis; not Trade By Data code",
        "research_only": True,
        "live_trading": False,
        "order_permission": "DENIED",
        "strategy_sha256": hashlib.sha256(strategy_source.encode()).hexdigest(),
        "raw_ticks": native["raw_ticks"],
        "native_fills_report_rows": fills,
        "kpis": native.get("kpis"),
        "cost_profile_status": "ASSUMPTION_ONLY",
        "native_protective_sl_tp_orders": False,
        "oos_verified": False,
        "wfo_verified": False,
        "monte_carlo_verified": False,
        "evidence_path": str(evidence_path),
    }
    (output / "overnight_drift_native_result.json").write_text(json.dumps(result, indent=2, allow_nan=False), encoding="utf-8")
    return result

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--commission-per-lot", type=float, default=0.0)
    a = ap.parse_args()
    print(json.dumps(run(Path(a.catalog), Path(a.output), a.commission_per_lot)))

if __name__ == "__main__":
    main()
