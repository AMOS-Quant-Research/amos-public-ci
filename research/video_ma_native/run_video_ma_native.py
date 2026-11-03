"""Run the two requested MA variants through the established Nautilus raw-tick path."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

SHARED_RESEARCH = Path(__file__).resolve().parents[1] / "vibe_xauusd"
sys.path.insert(0, str(SHARED_RESEARCH))
from run_ae_watch_native import validate_archive, extract_native
from patch_native_fractional_sizing import patch

HERE = Path(__file__).resolve().parent
VENDORED_DRIVER = HERE.parents[1] / "vendor/vibe-trading/agent/backtest/engines/nautilus_vibe_driver.py"


def _sources():
    common = (HERE / "video_ma_cross.py").read_text(encoding="utf-8")
    return (
        ("VIDEO_M5_SMA44_332", common,
         {"timeframe": "M5", "exit_model": "prior_UTC_day_high_low; cross reversal; no re-entry after stop"}),
        ("M1_SMA44_332_RR2_ATR14X2", common + "\nSignalEngine = M1AtrTrailSignalEngine\n",
         {"timeframe": "M1", "exit_model": "prior_UTC_day_high_low; cross reversal; ATR(14)*2 trail only after +2R"}),
    )


def run(archive: str, output: str) -> int:
    validate_archive(archive)
    out = Path(output).resolve()
    _, catalog = extract_native(archive, out / "source")
    patched_driver = out / "driver" / "nautilus_ma_driver.py"
    patched_driver.parent.mkdir(parents=True, exist_ok=True)
    driver_sha = patch(VENDORED_DRIVER, patched_driver)
    results = []
    for num, (name, source, semantics) in enumerate(_sources(), 1):
        root = out / "runs" / f"{num:02d}_{name}"
        (root / "code").mkdir(parents=True, exist_ok=True)
        (root / "artifacts").mkdir(parents=True, exist_ok=True)
        (root / "code" / "signal_engine.py").write_text(source, encoding="utf-8")
        request = {
            "config": {
                "codes": ["XAUUSD"], "engine": "nautilus_rawtick",
                "nautilus_rawtick": {
                    "catalog_path": str(catalog), "lots": 0.1, "trade_units": 10,
                    "initial_cash": 10000, "paper_sizing_enabled": False,
                    "cost_model": {"commission_per_lot_usd": 0.0, "slippage_probability": 0.0,
                                   "slippage_points_per_side": 0.0, "margin_rate": 0.005,
                                   "max_leverage": 200},
                },
            }, "live_trading": False,
        }
        request_path, evidence_path = root / "artifacts/request.json", root / "artifacts/native_evidence.json"
        request_path.write_text(json.dumps(request, indent=2), encoding="utf-8")
        proc = subprocess.run([sys.executable, str(patched_driver), "--vibe-run-dir", str(root),
                               "--vibe-request", str(request_path), "--vibe-evidence", str(evidence_path)],
                              text=True, capture_output=True, timeout=900)
        (root / "artifacts/driver.log").write_text(proc.stdout + "\n--- STDERR ---\n" + proc.stderr, encoding="utf-8")
        result = {"name": name, "status": "FAILED", "returncode": proc.returncode,
                  "signal_sha256": hashlib.sha256(source.encode()).hexdigest(),
                  "native_driver_sha256": driver_sha, "semantics": semantics,
                  "research_only": True, "raw_bid_ask_order_fills": True,
                  "signal_logic_bar_close": True,
                  "stop_trail_order_type": "signal-side state transition; next raw QuoteTick market exit",
                  "costs_calibrated": False, "out_of_sample": False}
        if proc.returncode == 0 and evidence_path.exists():
            evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
            result.update({"status": "MEASURED", "raw_ticks": evidence["raw_ticks"],
                           "native_closed_positions": evidence["native_fills"], "kpis": evidence["kpis"],
                           "diagnostics": evidence["diagnostics"], "cost_model": evidence["cost_model"]})
            if evidence["diagnostics"]["fills_report_rows"] < 1:
                result["status"] = "NO_NATIVE_FILLS"
                result["invalid_reason"] = (
                    "This catalog cannot produce a comparison: neither variant generated a native fill. "
                    "For VIDEO_M5_SMA44_332, require at least 333 completed M5 bars plus a prior trading day."
                )
        else:
            result["error_tail"] = (proc.stderr or proc.stdout)[-1600:]
        (root / "run_card.json").write_text(json.dumps(result, indent=2, allow_nan=False), encoding="utf-8")
        results.append(result)
    batch = {"contract": "amos.video-ma.rawtick.v1", "live_trading": False,
             "variants": results, "same_catalog": True,
             "comparison_valid_only_if_all_measured": all(x["status"] == "MEASURED" for x in results)}
    (out / "ma_comparison.json").write_text(json.dumps(batch, indent=2, allow_nan=False), encoding="utf-8")
    print(json.dumps(batch, indent=2, allow_nan=False))
    return 0 if batch["comparison_valid_only_if_all_measured"] else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    raise SystemExit(run(args.archive, args.output))
