"""Run independent AMOS M1 signals on the reused Nautilus native QuoteTick engine.

Requires an existing XAUUSD ParquetDataCatalog. No synthetic fallback.
Orders are native simulation only. Driver exits when signal becomes WAIT/reverses;
suggested SL/TP are NOT native protective orders and are not tested here.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

from research.ai_trader.nim_candidate import generate,validate

SOURCE='''"""AMOS M1 research strategy: causal closed-bar features; no live execution."""
import pandas as pd
from research.ai_trader.engine import decide

PARAMS = __PARAMS__
class SignalEngine:
    def generate(self,data):
        bars=data["XAUUSD"]
        period=PARAMS["period"]
        values=[]
        for i in range(len(bars)):
            if i<period+1:
                values.append(0.0)
                continue
            window=bars.iloc[max(0,i-period-2):i+1]
            if len(window)<period+2:
                values.append(0.0)
                continue
            inputs=[]
            for stamp,row in window.iterrows():
                inputs.append({"minute":int(pd.Timestamp(stamp).value//60_000_000_000),
                               "open":float(row["open"]),"high":float(row["high"]),
                               "low":float(row["low"]),"close":float(row["close"]),
                               "bid":float(row["bid"]),"ask":float(row["ask"])})
            action=decide(inputs,PARAMS)["action"]
            values.append(1.0 if action=="BUY" else -1.0 if action=="SELL" else 0.0)
        return {"XAUUSD":pd.Series(values,index=bars.index)}
'''

DEFAULT={"period":21,"rsi_long":55,"rsi_short":45,"max_spread_atr":0.3}
def run(catalog,out,*,nim=False,params=None,commission_per_lot=0.0):
    catalog=Path(catalog).resolve()
    if not catalog.exists():
        raise FileNotFoundError("actual Nautilus ParquetDataCatalog missing")
    if nim and params is not None:
        raise ValueError("choose NIM OR supplied parameters")
    if commission_per_lot<0:
        raise ValueError("negative commission")
    out=Path(out).resolve()
    out.mkdir(parents=True,exist_ok=True)
    candidate=generate() if nim else None
    p=validate(candidate["parameters"] if candidate else (params or DEFAULT))
    rundir=out/"native_run"
    (rundir/"code").mkdir(parents=True,exist_ok=True)
    (rundir/"artifacts").mkdir(parents=True,exist_ok=True)
    source=SOURCE.replace("__PARAMS__",repr(p))
    (rundir/"code/signal_engine.py").write_text(source,encoding="utf-8")
    cost={"commission_per_lot_usd":commission_per_lot,"slippage_probability":0.0,
          "slippage_points_per_side":0.0,"margin_rate":0.005,"max_leverage":200}
    config={"codes":["XAUUSD"],"engine":"nautilus_rawtick",
            "nautilus_rawtick":{"catalog_path":str(catalog),"lots":0.01,
                                 "trade_units":1,"initial_cash":10000,
                                 "cost_model":cost}}
    request=rundir/"artifacts/request.json"
    evidence=rundir/"artifacts/nautilus_rawtick_evidence.json"
    request.write_text(json.dumps({"config":config,"live_trading":False},indent=2))
    driver=Path(__file__).resolve().with_name("nautilus_vibe_driver.py")
    env=os.environ.copy()
    root=Path(__file__).resolve().parents[2]
    env["PYTHONPATH"]=str(root)+os.pathsep+env.get("PYTHONPATH","")
    args=[sys.executable,str(driver),"--vibe-run-dir",str(rundir),
          "--vibe-request",str(request),"--vibe-evidence",str(evidence)]
    proc=subprocess.run(args,text=True,capture_output=True,timeout=1200,env=env)
    (rundir/"artifacts/driver.log").write_text(proc.stdout+"\n--- STDERR ---\n"+proc.stderr)
    if proc.returncode!=0 or not evidence.exists():
        raise RuntimeError("NATIVE_BT_FAILED; inspect native_run/artifacts/driver.log")
    native=json.loads(evidence.read_text())
    if native.get("engine")!="NautilusTrader BacktestEngine" or native.get("ohlc_resample_used") is not False:
        raise ValueError("invalid native backtest evidence")
    if int(native.get("raw_ticks",0))<1000:
        raise ValueError("insufficient actual QuoteTicks")
    fills=int(native.get("diagnostics",{}).get("fills_report_rows",0))
    if fills<1:
        raise ValueError("native simulation returned zero fills")
    result={"contract":"amos.ai-trader.native-research.v1","research_only":True,
            "live_trading":False,"order_permission":"DENIED",
            "candidate_source":"NVIDIA_NIM" if candidate else "DETERMINISTIC_BASELINE",
            "candidate":candidate,"parameters":p,
            "strategy_sha256":hashlib.sha256(source.encode()).hexdigest(),
            "native_fills_report_rows":fills,"raw_ticks":native["raw_ticks"],
            "kpis":native.get("kpis"),"cost_profile_status":"ASSUMPTION_ONLY",
            "native_protective_sl_tp_orders":False,
            "oos_verified":False,"wfo_verified":False,"monte_carlo_verified":False,
            "coreai_acknowledged":False,
            "evidence_path":str(evidence)}
    (out/"native_research_result.json").write_text(json.dumps(result,indent=2,allow_nan=False))
    return result

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--catalog",required=True)
    ap.add_argument("--output",required=True)
    ap.add_argument("--nim",action="store_true")
    ap.add_argument("--commission-per-lot",type=float,default=0.0)
    a=ap.parse_args()
    r=run(a.catalog,a.output,nim=a.nim,commission_per_lot=a.commission_per_lot)
    print(json.dumps({"raw_ticks":r["raw_ticks"],"fills":r["native_fills_report_rows"],
                      "candidate_source":r["candidate_source"],"research_only":True}))
if __name__=="__main__":main()
