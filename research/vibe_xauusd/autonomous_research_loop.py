"""Unattended, checkpointed AE-paper candidate research loop.

Uses original Kelly paper objective/constraint with *new* parameter hypotheses.
Runs actual Vibe NautilusTrader BacktestEngine on immutable Raw Bid/Ask.
Rule-based adaptive proposals, NOT an LLM-generated literature review.
No live trading; no promotion; no simulated success.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from run_ae_watch_native import validate_archive, extract_native
from patch_native_fractional_sizing import patch
from run_ae_original_native import HERE, VENDORED_DRIVER

PLANS = [
    {"lambda": 1.0, "momentum": 5, "lookback": 80},
    {"lambda": 2.0, "momentum": 8, "lookback": 80},
    {"lambda": 0.5, "momentum": 3, "lookback": 120},
    {"lambda": 1.5, "momentum": 8, "lookback": 120},
    {"lambda": 3.0, "momentum": 5, "lookback": 60},
    {"lambda": 0.75, "momentum": 3, "lookback": 60},
]


def render(plan):
    s = (HERE / "ae_original_kelly.py").read_text(encoding="utf-8")
    replacements = [
        ("returns.rolling(5, min_periods=5)", f"returns.rolling({plan['momentum']}, min_periods={plan['momentum']})"),
        ("range(90, len(bars))", f"range({max(90, plan['lookback']+10)}, len(bars))"),
        ("iloc[t-80:t]", f"iloc[t-{plan['lookback']}:t]"),
        ("lam=1.0, n_grid=51", f"lam={plan['lambda']!r}, n_grid=51"),
    ]
    for old, new in replacements:
        if s.count(old) != 1:
            raise ValueError(f"paper source drift: {old}")
        s = s.replace(old, new, 1)
    return s


def read_ledger(path):
    if not path.exists():
        return {"contract": "amos.ae.autonomous-ledger.v1", "completed": []}
    d = json.loads(path.read_text(encoding="utf-8"))
    if d.get("contract") != "amos.ae.autonomous-ledger.v1":
        raise ValueError("unknown ledger contract")
    return d


def atomic_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, allow_nan=False), encoding="utf-8")
    tmp.replace(path)


def run(archive, output, ledger_path, cycles):
    validate_archive(archive)
    output = Path(output).resolve()
    ledger_path = Path(ledger_path).resolve()
    ledger = read_ledger(ledger_path)
    _, catalog = extract_native(archive, output / "source")
    from nautilus_trader.persistence.catalog import ParquetDataCatalog
    from nautilus_trader.model.data import QuoteTick
    cat = ParquetDataCatalog(str(catalog))
    if not any(x.id.symbol.value.replace("/", "") == "XAUUSD" for x in cat.instruments()):
        raise ValueError("XAUUSD instrument missing")
    raw = cat.query(data_cls=QuoteTick, identifiers=["XAUUSD.SIM"])
    if len(raw) < 1000:
        raise ValueError("insufficient raw quote ticks")
    last_ts = -1
    for t in raw:
        if t.ts_event < last_ts or t.ask_price < t.bid_price:
            raise ValueError("invalid raw quote")
        last_ts = t.ts_event
    driver = output / "driver/nautilus_ae_driver.py"
    driver_sha = patch(VENDORED_DRIVER, driver)
    completed_keys = {x["candidate_key"] for x in ledger["completed"]}
    new_results = []
    for plan in PLANS:
        source = render(plan)
        source_sha = hashlib.sha256(source.encode()).hexdigest()
        candidate_key = hashlib.sha256((source_sha + driver_sha + "56bf3bcfc3221b6cccd9cd64c03425952ebc98baf510e39058b65372772bdf38").encode()).hexdigest()
        if candidate_key in completed_keys:
            continue
        if len(new_results) >= cycles:
            break
        number = len(ledger["completed"])+1
        rd = output / "runs" / f"{number:03d}_{candidate_key[:12]}"
        (rd / "code").mkdir(parents=True, exist_ok=True)
        (rd / "artifacts").mkdir(parents=True, exist_ok=True)
        (rd / "code/signal_engine.py").write_text(source, encoding="utf-8")
        config = {"codes": ["XAUUSD"], "engine": "nautilus_rawtick",
                  "nautilus_rawtick": {
                      "catalog_path": str(catalog), "lots": 0.1, "trade_units": 10,
                      "initial_cash": 10000, "paper_sizing_enabled": True,
                      "cost_model": {"commission_per_lot_usd": 0.0,
                                     "slippage_probability": 0.0,
                                     "slippage_points_per_side": 0.0,
                                     "margin_rate": 0.005, "max_leverage": 200}}}
        req = rd / "artifacts/request.json"
        ev = rd / "artifacts/native_evidence.json"
        req.write_text(json.dumps({"config": config, "live_trading": False}, indent=2))
        p = subprocess.run([sys.executable, str(driver),
                            "--vibe-run-dir", str(rd), "--vibe-request", str(req),
                            "--vibe-evidence", str(ev)],
                           capture_output=True, text=True, timeout=900)
        (rd / "artifacts/driver.log").write_text(p.stdout+"\n--- STDERR ---\n"+p.stderr)
        result = {"candidate_key": candidate_key, "plan": plan,
                  "source_sha256": source_sha, "driver_sha256": driver_sha,
                  "returncode": p.returncode, "raw_ticks": len(raw),
                  "paper_original_constraint": "E[(1+fR)^(-lambda)]<=1",
                  "paper_original_objective": "max E[log(1+fR)]",
                  "live_trading": False, "costs_calibrated": False,
                  "out_of_sample": False}
        if p.returncode == 0 and ev.exists():
            evidence = json.loads(ev.read_text())
            result["kpis"] = evidence.get("kpis")
            result["native_fills"] = evidence.get("diagnostics", {}).get("fills_report_rows", 0)
            result["fractional_orders"] = evidence.get("diagnostics", {}).get("fractional_size_orders", 0)
            pf = result["kpis"].get("PF") if result["kpis"] else None
            ev_mean = result["kpis"].get("EV") if result["kpis"] else None
            result["verdict"] = ("REJECT" if pf is not None and ev_mean is not None and (pf < 1 or ev_mean < 0)
                                 else "HOLD_OOS_AND_COSTS")
            if result["native_fills"] == 0:
                result["verdict"] = "NO_NATIVE_FILLS"
        else:
            result["verdict"] = "EXECUTION_FAILED"
            result["error_tail"] = (p.stderr or p.stdout)[-1000:]
        (rd / "run_card.json").write_text(json.dumps(result, indent=2, allow_nan=False))
        if p.returncode != 0:
            atomic_write(output / "last_failure.json", result)
            raise RuntimeError(f"Native failure in {candidate_key[:12]}: {result.get('error_tail')}")
        ledger["completed"].append(result)
        completed_keys.add(candidate_key)
        atomic_write(ledger_path, ledger)
        new_results.append(result)
        print("AUTONOMOUS_CYCLE", len(new_results), "CANDIDATE", candidate_key[:12],
              "VERDICT", result["verdict"], "NATIVE_FILLS", result["native_fills"], flush=True)
    summary = {"contract": "amos.ae.autonomous-run.v1",
               "new_cycles": len(new_results), "total_completed": len(ledger["completed"]),
               "exhausted": len(ledger["completed"]) >= len(PLANS),
               "research_only": True, "llm_hypothesis_generation_verified": False,
               "ledger_path": str(ledger_path),
               "new_results": new_results}
    atomic_write(output / "autonomous_summary.json", summary)
    print(json.dumps(summary, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--archive", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--ledger", required=True)
    p.add_argument("--cycles", type=int, default=3)
    a=p.parse_args()
    if not 1<=a.cycles<=6: raise ValueError("cycles must be 1..6")
    raise SystemExit(run(a.archive, a.output, a.ledger, a.cycles))
