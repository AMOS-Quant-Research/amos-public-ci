"""Verified Nautilus ParquetDataCatalog QuoteTick -> research CSV adapter.
Only exports real QuoteTicks; never generates synthetic prices.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path

def export(catalog_path, output, instrument="XAUUSD.SIM"):
    from nautilus_trader.persistence.catalog import ParquetDataCatalog
    from nautilus_trader.model.data import QuoteTick
    cat=ParquetDataCatalog(str(catalog_path))
    ids={str(x.id) for x in cat.instruments()}
    if instrument not in ids:
        raise ValueError("instrument missing from catalog: "+instrument)
    quotes=cat.query(data_cls=QuoteTick, identifiers=[instrument])
    if not quotes or len(quotes)<1000:
        raise ValueError("at least 1000 native QuoteTicks required")
    output=Path(output)
    output.parent.mkdir(parents=True,exist_ok=True)
    tmp=output.with_suffix(output.suffix+".tmp")
    prev=-1
    try:
        with tmp.open("w",newline="") as f:
            writer=csv.writer(f)
            writer.writerow(["ts_event","bid","ask"])
            for q in quotes:
                ts=int(q.ts_event)
                bid=float(q.bid_price)
                ask=float(q.ask_price)
                if ts<=prev or bid<=0 or ask<bid:
                    raise ValueError("nonmonotonic timestamp or crossed/invalid quote")
                writer.writerow([ts,format(bid,".10f"),format(ask,".10f")])
                prev=ts
        tmp.replace(output)
    finally:
        tmp.unlink(missing_ok=True)
    return {"kind":"REAL_XAUUSD_BID_ASK_QUOTETICKS","instrument":instrument,
            "count":len(quotes),"sha256":hashlib.sha256(output.read_bytes()).hexdigest(),
            "source_catalog":str(catalog_path),"live_trading":False}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--catalog",required=True)
    p.add_argument("--output",required=True)
    p.add_argument("--instrument",default="XAUUSD.SIM")
    p.add_argument("--manifest",required=True)
    a=p.parse_args()
    proof=export(a.catalog,a.output,a.instrument)
    Path(a.manifest).write_text(json.dumps(proof,indent=2)+"\n")
    print(json.dumps({"count":proof["count"],"sha256":proof["sha256"]}))
if __name__=="__main__":
    main()
