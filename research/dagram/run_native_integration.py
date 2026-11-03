"""End-to-end wiring test on REAL XAUUSD Bid/Ask ticks with SYNTHETIC dagram events.
This is NOT a dagram strategy backtest or evidence of signal accuracy/profitability.
No live orders; reuse the existing Vibe-Trading Nautilus native driver from the archive.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

ARCHIVE_SHA256 = "56bf3bcfc3221b6cccd9cd64c03425952ebc98baf510e39058b65372772bdf38"
DRIVER = "Vibe-Trading/agent/backtest/engines/nautilus_vibe_driver.py"
CATALOG = "xauusd-data/.work/vibe-math-xauusd-20260727/data/"
BRIDGE = Path(__file__).with_name("vibe_signal_bridge.py")

def extract(archive: Path, target: Path):
    if hashlib.sha256(archive.read_bytes()).hexdigest() != ARCHIVE_SHA256:
        raise ValueError("source archive SHA-256 mismatch")
    with zipfile.ZipFile(archive) as z:
        names = z.namelist()
        if DRIVER not in names or not any(n.startswith(CATALOG) and n.endswith(".parquet") for n in names):
            raise ValueError("source archive missing driver or native QuoteTick catalog")
        for n in names:
            p = Path(n)
            if p.is_absolute() or ".." in p.parts:
                raise ValueError("unsafe ZIP member")
        for n in names:
            if n == DRIVER or n.startswith(CATALOG):
                if n.endswith("/"): continue
                dest = target / n
                dest.parent.mkdir(parents=True, exist_ok=True)
                with z.open(n) as src, dest.open("wb") as dst:
                    shutil.copyfileobj(src, dst)
    return target / DRIVER, target / "xauusd-data/.work/vibe-math-xauusd-20260727"

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--archive", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    run_dir = output / "run"
    (run_dir / "code").mkdir(parents=True, exist_ok=True)
    (run_dir / "artifacts").mkdir(parents=True, exist_ok=True)
    result_path = output / "result.json"
    result = {"contract":"amos.dagram.vibe.native-integration.v1",
              "live_trading":False,"signal_source":"SYNTHETIC_FIXTURE_NOT_DAGRAM",
              "dagram_algorithm_extracted":False,"status":"NOT_RUN"}
    try:
        driver, catalog = extract(args.archive, output / "source")
        from nautilus_trader.persistence.catalog import ParquetDataCatalog
        from nautilus_trader.model.data import QuoteTick
        c = ParquetDataCatalog(str(catalog))
        ticks = c.query(data_cls=QuoteTick, identifiers=["XAUUSD.SIM"])
        if len(ticks) < 1000: raise ValueError("Raw QuoteTicks <1000")
        last = -1
        for t in ticks:
            if t.ts_event < last or t.ask_price < t.bid_price:
                raise ValueError("invalid Raw Tick timestamp or spread")
            last = t.ts_event
        result["input_raw_ticks"] = len(ticks)
        result["input_preflight"] = "PASS"
        # Synthetic test-only events deliberately exercise LONG -> SHORT -> FLAT.
        # Timestamps fall within the bundled 2026-07-27 quote catalog.
        fixture = [
            {"issuedAt":"2026-07-27T00:30:00Z","side":"LONG"},
            {"issuedAt":"2026-07-27T00:45:00Z","side":"SHORT"},
            {"issuedAt":"2026-07-27T01:00:00Z","plan":None}
        ]
        observations = run_dir / "artifacts/synthetic_observations.json"
        observations.write_text(json.dumps(fixture,indent=2),encoding="utf-8")
        shutil.copyfile(BRIDGE, run_dir / "code/signal_engine.py")
        config = {"codes":["XAUUSD"],"engine":"nautilus_rawtick",
                  "nautilus_rawtick":{"catalog_path":str(catalog),"lots":0.01,
                    "trade_units":1,"initial_cash":10000,
                    "cost_model":{"commission_per_lot_usd":0.0,
                      "slippage_probability":0.0,"slippage_points_per_side":0.0,
                      "margin_rate":0.005,"max_leverage":200}}}
        request = run_dir / "artifacts/request.json"
        evidence = run_dir / "artifacts/nautilus_rawtick_evidence.json"
        request.write_text(json.dumps({"config":config,"live_trading":False},indent=2))
        env = dict(os.environ,AMOS_DAGRAM_OBSERVATIONS=str(observations))
        cmd = [sys.executable,str(driver),"--vibe-run-dir",str(run_dir),
               "--vibe-request",str(request),"--vibe-evidence",str(evidence)]
        proc = subprocess.run(cmd,env=env,text=True,capture_output=True,timeout=900)
        (output/"driver_stdout.log").write_text(proc.stdout)
        (output/"driver_stderr.log").write_text(proc.stderr)
        result["driver_exit_code"] = proc.returncode
        if proc.returncode != 0 or not evidence.is_file():
            raise RuntimeError("native driver failed; inspect uploaded driver logs")
        measured = json.loads(evidence.read_text())
        result["native_fills_report_rows"] = measured.get("diagnostics",{}).get("fills_report_rows",0)
        result["matched_signal_bars"] = measured.get("diagnostics",{}).get("matched_signal_bars",0)
        result["orders_submitted"] = measured.get("diagnostics",{}).get("orders_submitted",0)
        result["driver_raw_ticks"] = measured.get("raw_ticks")
        result["execution_profile_status"] = measured.get("cost_model",{}).get("execution_profile_status")
        if result["native_fills_report_rows"] < 1 or result["orders_submitted"] < 1 or result["matched_signal_bars"] < 1:
            raise ValueError("native fills, submitted orders, or matched bars missing")
        result["status"] = "PASS_SYNTHETIC_SIGNALS_REAL_RAW_TICK_EXECUTION"
        result["profitability_verified"] = False
    except Exception as exc:
        result["status"] = "FAILED"
        result["error"] = str(exc)
    result_path.write_text(json.dumps(result,indent=2,allow_nan=False))
    print(json.dumps(result,indent=2,allow_nan=False),flush=True)
    return 0 if result["status"].startswith("PASS_") else 1

if __name__=="__main__":
    raise SystemExit(main())
