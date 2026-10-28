"""Run AE Math Watch candidate validation on the bundled real XAUUSD Raw Bid/Ask catalog.

This is a *batch verification loop*, NOT a generative LLM autonomous loop.
It invokes the Vibe-Trading package's Nautilus native driver. No live orders.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import zipfile

EXPECTED_SHA = "56bf3bcfc3221b6cccd9cd64c03425952ebc98baf510e39058b65372772bdf38"
CATALOG_PREFIX = "xauusd-data/.work/vibe-math-xauusd-20260727/data/"
DRIVER = "Vibe-Trading/agent/backtest/engines/nautilus_vibe_driver.py"
HYPOTHESES = (
    ("AE_DDR_PRICE_PROXY", 0.0003, 0.0009),
    ("AE_CONFORMAL_OCE_PRICE_PROXY", 0.0005, 0.0012),
)


def validate_archive(archive):
    if hashlib.sha256(Path(archive).read_bytes()).hexdigest() != EXPECTED_SHA:
        raise ValueError("archive SHA-256 mismatch")
    with zipfile.ZipFile(archive) as z:
        names = z.namelist()
        if DRIVER not in names or not any(n.startswith(CATALOG_PREFIX) and n.endswith(".parquet") for n in names):
            raise ValueError("missing native driver or Raw Bid/Ask catalog")
        for n in names:
            p = Path(n)
            if p.is_absolute() or ".." in p.parts:
                raise ValueError("unsafe ZIP member")
    return True


def extract_native(archive, target):
    target = Path(target).resolve()
    target.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as z:
        selected = [n for n in z.namelist() if n == DRIVER or n.startswith(CATALOG_PREFIX)]
        for name in selected:
            member = z.getinfo(name)
            if member.is_dir():
                continue
            dest = (target / name).resolve()
            if not dest.is_relative_to(target):
                raise ValueError("unsafe archive extraction")
            dest.parent.mkdir(parents=True, exist_ok=True)
            with z.open(member) as src, dest.open("wb") as dst:
                import shutil
                shutil.copyfileobj(src, dst)
    return target / DRIVER, target / "xauusd-data/.work/vibe-math-xauusd-20260727/data"


def signal_source(threshold, cap):
    # Distinct, explicitly named price-drawdown proxies, NOT portfolio DDR or OCE.
    # Signals use completed M1 bars only; native execution uses next QuoteTick.
    return """import numpy as np
import pandas as pd

class SignalEngine:
    def generate(self, data):
        bars = data["XAUUSD"]
        mid = bars["close"].astype(float)
        r = mid.pct_change().fillna(0.0)
        rolling_high = mid.shift(1).rolling(30, min_periods=5).max()
        price_dd = (1.0 - mid / rolling_high).clip(lower=0.0).fillna(0.0)
        momentum = r.shift(1).rolling(5, min_periods=5).sum().fillna(0.0)
        target = pd.Series(np.where(momentum > THRESHOLD, 1.0, np.where(momentum < -THRESHOLD, -1.0, 0.0)), index=bars.index)
        target.loc[price_dd > DD_CAP] = 0.0
        return {"XAUUSD": target}
""".replace("THRESHOLD", repr(threshold)).replace("DD_CAP", repr(cap))


def run(archive, output):
    validate_archive(archive)
    output = Path(output).resolve()
    driver, catalog = extract_native(archive, output / "source")
    from nautilus_trader.persistence.catalog import ParquetDataCatalog
    catalog_instruments = ParquetDataCatalog(str(catalog)).instruments()
    print("CATALOG_INSTRUMENTS", [str(x.id) for x in catalog_instruments], flush=True)
    print("CATALOG_FILES", [str(p.relative_to(catalog)) for p in catalog.rglob("*.parquet")], flush=True)
    results = []
    for index, (candidate, threshold, cap) in enumerate(HYPOTHESES, 1):
        run_dir = output / "runs" / f"{index:02d}_{candidate}"
        (run_dir / "code").mkdir(parents=True, exist_ok=True)
        (run_dir / "artifacts").mkdir(parents=True, exist_ok=True)
        source = signal_source(threshold, cap)
        (run_dir / "code/signal_engine.py").write_text(source, encoding="utf-8")
        config = {
            "codes": ["XAUUSD"], "engine": "nautilus_rawtick",
            "nautilus_rawtick": {
                "catalog_path": str(catalog),
                "lots": 0.01, "trade_units": 1, "initial_cash": 10000,
                "cost_model": {
                    "commission_per_lot_usd": 0.0,
                    "slippage_probability": 0.0,
                    "slippage_points_per_side": 0.0,
                    "margin_rate": 0.005,
                    "max_leverage": 200
                }
            }
        }
        request = run_dir / "artifacts/request.json"
        evidence = run_dir / "artifacts/nautilus_rawtick_evidence.json"
        request.write_text(json.dumps({"config": config, "live_trading": False}, indent=2), encoding="utf-8")
        proc = subprocess.run([sys.executable, str(driver), "--vibe-run-dir", str(run_dir),
                               "--vibe-request", str(request), "--vibe-evidence", str(evidence)],
                              text=True, capture_output=True, timeout=900)
        (run_dir / "artifacts/driver.log").write_text(proc.stdout + "\n--- STDERR ---\n" + proc.stderr, encoding="utf-8")
        item = {"candidate": candidate, "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
                "data_sha256": EXPECTED_SHA, "returncode": proc.returncode, "live_trading": False}
        if proc.returncode == 0 and evidence.exists():
            data = json.loads(evidence.read_text(encoding="utf-8"))
            item["raw_ticks"] = data.get("raw_ticks")
            item["native_fills_reported_by_package"] = data.get("native_fills")
            item["fills_report_rows"] = data.get("diagnostics", {}).get("fills_report_rows")
            item["kpis"] = data.get("kpis")
            item["cost_model"] = data.get("cost_model")
            item["status"] = "MEASURED_RESEARCH_ONLY" if item["fills_report_rows"] and item["raw_ticks"] else "NO_VERIFIED_FILLS"
        else:
            item["status"] = "FAILED"
            item["error_tail"] = (proc.stderr or proc.stdout)[-800:]
        (run_dir / "run_card.json").write_text(json.dumps(item, indent=2, allow_nan=False), encoding="utf-8")
        results.append(item)
    result = {"contract": "amos.vibe.ae-watch.batch.v1", "research_only": True,
              "autonomous_llm_loop_verified": False, "native_run_success_count": sum(x["returncode"] == 0 for x in results),
              "candidates": results}
    (output / "batch_result.json").write_text(json.dumps(result, indent=2, allow_nan=False), encoding="utf-8")
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0 if all(x["returncode"] == 0 for x in results) else 1


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--archive", required=True)
    p.add_argument("--output", required=True)
    a = p.parse_args()
    raise SystemExit(run(a.archive, a.output))
