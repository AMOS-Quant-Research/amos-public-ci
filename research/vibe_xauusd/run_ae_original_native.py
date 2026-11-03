"""Native A/B: original risk-constrained Kelly objective+moment versus matched baseline.

Uses pinned original Vibe source and real XAUUSD Bid/Ask QuoteTicks.
No live broker path; evidence records actual native fills and paper constraint.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

from run_ae_watch_native import validate_archive, extract_native
from patch_native_fractional_sizing import patch

HERE = Path(__file__).resolve().parent
VENDORED_DRIVER = HERE.parents[1] / "vendor/vibe-trading/agent/backtest/engines/nautilus_vibe_driver.py"


def baseline_source():
    return """import numpy as np
import pandas as pd
class SignalEngine:
    def generate(self, data):
        mid = data["XAUUSD"]["close"].astype(float)
        returns = mid.pct_change().fillna(0)
        momentum = returns.rolling(5, min_periods=5).sum().fillna(0)
        target = pd.Series(np.sign(momentum), index=mid.index)
        return {"XAUUSD": target}
"""


def run(archive, output):
    validate_archive(archive)
    output = Path(output).resolve()
    _, catalog = extract_native(archive, output / "source")
    from nautilus_trader.persistence.catalog import ParquetDataCatalog
    from nautilus_trader.model.data import QuoteTick
    native = ParquetDataCatalog(str(catalog))
    instruments = native.instruments()
    if not any(x.id.symbol.value.replace("/", "") == "XAUUSD" for x in instruments):
        raise ValueError("XAUUSD instrument missing")
    raw = native.query(data_cls=QuoteTick, identifiers=["XAUUSD.SIM"])
    if len(raw) < 1000:
        raise ValueError("insufficient Raw QuoteTicks")
    previous = -1
    for t in raw:
        if t.ts_event < previous or t.ask_price < t.bid_price:
            raise ValueError("Raw Bid/Ask integrity failure")
        previous = t.ts_event
    patched_driver = output / "driver/nautilus_ae_driver.py"
    patch_sha = patch(VENDORED_DRIVER, patched_driver)
    results = []
    for i, (name, source, sized) in enumerate((
        ("MOMENTUM_BASELINE", baseline_source(), False),
        ("RC_KELLY_ORIGINAL_MOMENT", (HERE / "ae_original_kelly.py").read_text(), True),
    ), 1):
        rd = output / "runs" / f"{i:02d}_{name}"
        (rd / "code").mkdir(parents=True, exist_ok=True)
        (rd / "artifacts").mkdir(parents=True, exist_ok=True)
        (rd / "code/signal_engine.py").write_text(source, encoding="utf-8")
        spec = {
            "codes": ["XAUUSD"], "engine": "nautilus_rawtick",
            "nautilus_rawtick": {
                "catalog_path": str(catalog), "lots": 0.1,
                "trade_units": 10, "initial_cash": 10000,
                "paper_sizing_enabled": sized,
                "cost_model": {
                    "commission_per_lot_usd": 0.0,
                    "slippage_probability": 0.0,
                    "slippage_points_per_side": 0.0,
                    "margin_rate": 0.005,
                    "max_leverage": 200
                }
            }
        }
        req = rd / "artifacts/request.json"
        evidence = rd / "artifacts/native_evidence.json"
        req.write_text(json.dumps({"config": spec, "live_trading": False}, indent=2))
        proc = subprocess.run([sys.executable, str(patched_driver),
                               "--vibe-run-dir", str(rd), "--vibe-request", str(req),
                               "--vibe-evidence", str(evidence)],
                              text=True, capture_output=True, timeout=900)
        (rd / "artifacts/driver.log").write_text(proc.stdout+"\n--- STDERR ---\n"+proc.stderr)
        result = {"name": name, "returncode": proc.returncode,
                  "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
                  "native_driver_sha256": patch_sha,
                  "raw_ticks_preflight": len(raw),
                  "paper_formula": ("E[(1+fR)^(-lambda)]<=1 and max E[log(1+fR)]"
                                    if sized else "NONE_BASELINE"),
                  "historical_estimator": ("80 lagged policy returns, grid f=0..1"
                                            if sized else "M5 MOMENTUM"),
                  "live_trading": False}
        if proc.returncode == 0 and evidence.exists():
            e = json.loads(evidence.read_text())
            result.update({"status": "MEASURED", "native_fills_report_rows": e["diagnostics"]["fills_report_rows"],
                           "native_closed_positions": e["native_fills"],
                           "kpis": e["kpis"], "diagnostics": e["diagnostics"],
                           "cost_model": e["cost_model"]})
            if sized and e["diagnostics"]["fills_report_rows"] == 0:
                result["status"] = "NO_NATIVE_FILLS"
        else:
            result.update({"status": "FAILED", "error_tail": (proc.stderr or proc.stdout)[-1600:]})
        (rd / "run_card.json").write_text(json.dumps(result, indent=2, allow_nan=False))
        results.append(result)
    batch = {"contract": "amos.ae.paper-native.v1",
             "raw_bid_ask": True, "source_archive_sha256": "56bf3bcfc3221b6cccd9cd64c03425952ebc98baf510e39058b65372772bdf38",
             "research_only": True, "paper_equation_in_native_signal": True,
             "costs_calibrated": False, "out_of_sample": False, "results": results}
    (output / "paper_batch_result.json").write_text(json.dumps(batch, indent=2, allow_nan=False))
    print(json.dumps(batch, indent=2, allow_nan=False))
    return 0 if all(x["returncode"] == 0 for x in results) else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--archive", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    raise SystemExit(run(args.archive, args.output))
