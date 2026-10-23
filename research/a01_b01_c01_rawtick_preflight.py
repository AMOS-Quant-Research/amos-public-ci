#!/usr/bin/env python3
"""AMOS A01/B01/C01 Nautilus Raw Tick input preflight. No orders, no fabricated KPIs."""
import argparse, csv, importlib.util, json
from pathlib import Path

def inspect(path):
    p=Path(path)
    result={"path":str(p),"exists":p.is_file(),"rows":0,"bad_quotes":0,"bad_timestamps":0,"bid_ask":False}
    if not p.is_file(): return result
    with p.open(newline="",encoding="utf-8-sig") as f:
        reader=csv.DictReader(f)
        result["columns"]=reader.fieldnames
        if not {"timestamp","bid","ask"}.issubset(set(reader.fieldnames or [])): return result
        result["bid_ask"]=True
        last=""
        for row in reader:
            result["rows"]+=1
            try:
                bid,ask=float(row["bid"]),float(row["ask"])
                if bid<=0 or ask<bid: result["bad_quotes"]+=1
            except (TypeError,ValueError): result["bad_quotes"]+=1
            ts=row.get("timestamp","")
            if not ts or (last and ts<last): result["bad_timestamps"]+=1
            last=ts
    return result

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--ticks",required=True,help="Raw Bid/Ask CSV, not OHLC")
    p.add_argument("--edge-file",default="integrations/amos_9layer/edges/basic.py")
    args=p.parse_args()
    ticks=inspect(args.ticks)
    nt=importlib.util.find_spec("nautilus_trader") is not None
    edge=Path(args.edge_file).is_file()
    ready=nt and edge and ticks["bid_ask"] and ticks["rows"]>0 and ticks["bad_quotes"]==0 and ticks["bad_timestamps"]==0
    print(json.dumps({"nautilus_installed":nt,"edge_present":edge,"ticks":ticks,"ready_for_nautilus_bt":ready},ensure_ascii=False,indent=2))
    return 0 if ready else 2

if __name__=="__main__":
    raise SystemExit(main())
