"""End-to-end research data handoff: Nautilus catalog -> AI candidate -> M1 -> CoreAI JSON.

Does not execute Nautilus BT or deliver to CoreAI. Native evidence is optional
and blocked unless independently supplied and verified.
"""
import argparse
import json
from pathlib import Path
from research.ai_trader.catalog_adapter import export
from research.ai_trader.engine import read_quotes, minute_bars, decide, intake
from research.ai_trader.nim_candidate import generate

def run(catalog, out, use_nim=False, native_evidence=None):
    out=Path(out)
    out.mkdir(parents=True,exist_ok=True)
    proof=export(catalog,out/"real_quotes.csv")
    ai=generate() if use_nim else None
    rows=read_quotes(out/"real_quotes.csv")
    bars=minute_bars(rows)
    signal=decide(bars,ai["parameters"] if ai else None)
    envelope=intake(signal,proof,native_evidence,ai)
    (out/"catalog_provenance.json").write_text(json.dumps(proof,indent=2)+"\n")
    if ai:
        (out/"nim_candidate.json").write_text(json.dumps(ai,indent=2)+"\n")
    (out/"coreai_intake.json").write_text(json.dumps(envelope,indent=2,allow_nan=False)+"\n")
    return envelope

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--catalog",required=True)
    p.add_argument("--output",required=True)
    p.add_argument("--use-nim",action="store_true")
    p.add_argument("--native-evidence",type=Path)
    a=p.parse_args()
    ev=json.loads(a.native_evidence.read_text()) if a.native_evidence else None
    result=run(a.catalog,a.output,a.use_nim,ev)
    print(json.dumps({"status":result["status"],"delivery_status":result["delivery_status"],
                      "action":result["signal"]["action"],"order_permission":result["order_permission"]}))
if __name__=="__main__":main()
