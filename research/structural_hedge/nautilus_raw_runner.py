#!/usr/bin/env python3
"""AMOS Structural Hedge: Nautilus QuoteTick hypothesis replay, not live execution."""
import argparse,csv,datetime as dt,json
from pathlib import Path
from collections import deque
from decimal import Decimal
from nautilus_trader.backtest import BacktestEngine
from nautilus_trader.config import BacktestEngineConfig
from nautilus_trader.model import AccountType,AssetClass,Currency,InstrumentId,Money,OmsType,Price,Quantity,QuoteTick,Symbol,Venue
from nautilus_trader.model.instruments import Cfd
from nautilus_trader.trading import Strategy

IID=InstrumentId(Symbol("XAUUSD"),Venue("EXNESS"))
USD=Currency.from_str("USD")
def stamp(s):
    x=dt.datetime.fromisoformat(s.replace("Z","+00:00"))
    if x.tzinfo is None:x=x.replace(tzinfo=dt.timezone.utc)
    return int(x.timestamp()*1e9)
def instrument():
    return Cfd(instrument_id=IID,raw_symbol=Symbol("XAUUSD"),asset_class=AssetClass.COMMODITY,base_currency=None,quote_currency=USD,price_precision=5,size_precision=2,price_increment=Price.from_str("0.00001"),size_increment=Quantity.from_str("0.01"),lot_size=Quantity.from_str("1.00"),margin_init=Decimal("0.0005"),margin_maint=Decimal("0.0005"),ts_event=0,ts_init=0)
class StructuralHedge(Strategy):
    def __init__(self):
        super().__init__()
        self.bars=deque(maxlen=250);self.bar=None;self.minute=None
        self.phase="IDLE";self.direction=0;self.first=0;self.hedge=0;self.second=0
        self.first_ts=0;self.realized=0;self.trades=[];self.peak=1000;self.maxdd=0
        self.quotes=0;self.cycles=0;self.lock_count=0
    def on_start(self):self.subscribe_quotes(IID)
    def closebar(self):
        if self.bar:self.bars.append(self.bar.copy())
    def swings(self,d):
        a=list(self.bars)
        if len(a)<12:return []
        key="l" if d==1 else "h"
        out=[]
        for i in range(len(a)-3,2,-1):
            p=a[i][key]
            around=[a[j][key] for j in (i-2,i-1,i+1,i+2)]
            if (p<min(around) if d==1 else p>max(around)):
                out.append(p)
                if len(out)==5:break
        return out
    def signal(self,d):
        s=self.swings(d)
        if len(s)<3:return False
        b=self.bars[-1];p=s[0]
        return (b["l"]<p and b["c"]>p and b["c"]>b["o"]) if d==1 else (b["h"]>p and b["c"]<p and b["c"]<b["o"])
    def old_fvg(self,d):
        a=list(self.bars)
        if len(a)<5:return False
        b=a[-1]
        for i in range(len(a)-4,2,-1):
            if a[i]["ts"]>=self.first_ts:continue
            if d==1 and a[i-2]["l"]>a[i]["h"]:
                lo,hi=a[i]["h"],a[i-2]["l"]
                if b["h"]>=lo and b["l"]<=hi and b["c"]<b["o"]:return True
            if d==-1 and a[i-2]["h"]<a[i]["l"]:
                lo,hi=a[i-2]["h"],a[i]["l"]
                if b["h"]>=lo and b["l"]<=hi and b["c"]>b["o"]:return True
        return False
    def floating(self,bid,ask):
        d=self.direction
        if self.phase=="IDLE":return 0
        v=d*((bid if d==1 else ask)-self.first)
        if self.phase in ("LOCKED","SECOND"):
            v+=-d*((ask if d==1 else bid)-self.hedge)
        if self.phase in ("SECOND","RUN"):
            v+=d*((bid if d==1 else ask)-self.second)
        return v # 0.01 lot XAUUSD = 1 oz
    def settle(self,bid,ask,ts,reason):
        pnl=self.floating(bid,ask)
        self.realized+=pnl
        self.trades.append({"ts":ts,"pnl":round(pnl,5),"reason":reason})
        self.cycles+=1;self.phase="IDLE";self.direction=0
    def on_quote(self,q):
        self.quotes+=1
        bid=q.bid_price.as_double();ask=q.ask_price.as_double()
        ts=q.ts_event;bucket=ts//(300*1000000000)
        mid=(bid+ask)/2
        if self.minute is None:self.minute=bucket;self.bar={"o":mid,"h":mid,"l":mid,"c":mid,"ts":ts}
        elif bucket!=self.minute:
            self.closebar();self.minute=bucket
            self.bar={"o":mid,"h":mid,"l":mid,"c":mid,"ts":ts}
            self.evaluate(bid,ask,ts)
        else:
            self.bar["h"]=max(self.bar["h"],mid)
            self.bar["l"]=min(self.bar["l"],mid);self.bar["c"]=mid
        equity=1000+self.realized+self.floating(bid,ask)
        self.peak=max(self.peak,equity);self.maxdd=max(self.maxdd,self.peak-equity)
        if self.phase!="IDLE" and (equity<=965 or self.floating(bid,ask)<=-35):
            self.settle(bid,ask,ts,"emergency")
        elif self.phase!="IDLE" and self.floating(bid,ask)>=20:
            self.settle(bid,ask,ts,"target")
    def evaluate(self,bid,ask,ts):
        if len(self.bars)<15:return
        if self.phase=="IDLE":
            d=1 if self.signal(1) else (-1 if self.signal(-1) else 0)
            if d:
                self.direction=d;self.first=ask if d==1 else bid
                self.first_ts=ts;self.phase="FIRST"
        elif self.phase=="FIRST":
            if self.old_fvg(self.direction) and self.floating(bid,ask)>=2:
                self.hedge=bid if self.direction==1 else ask
                self.phase="LOCKED";self.lock_count+=1
        elif self.phase=="LOCKED":
            if self.signal(self.direction) and abs((bid+ask)/2-self.first)>=0.2:
                self.second=ask if self.direction==1 else bid
                self.phase="SECOND"
        elif self.phase=="SECOND":
            b=self.bars[-1]
            confirm=(b["c"]>b["o"]) if self.direction==1 else (b["c"]<b["o"])
            hedge_pnl=-self.direction*((ask if self.direction==1 else bid)-self.hedge)
            if confirm and hedge_pnl>=0:
                self.realized+=hedge_pnl
                self.phase="RUN"
    def export(self):
        vals=[x["pnl"] for x in self.trades];gp=sum(max(0,x) for x in vals);gl=-sum(min(0,x) for x in vals)
        return {"status":"NAUTILUS_QUOTETICK_HYPOTHESIS_REPLAY","quote_ticks":self.quotes,"completed_cycles":self.cycles,"hedges":self.lock_count,"net_closed_usd":round(sum(vals),4),"WR":sum(x>0 for x in vals)/len(vals) if vals else None,"PF":gp/gl if gl else None,"max_floating_equity_dd_usd":round(self.maxdd,4),"open_phase":self.phase,"trades":self.trades,"limitations":["virtual fills at next observed bid/ask; no real orders","no fees/swap/slippage or margin liquidation","IFVG branch not yet implemented","open cycle not liquidated at test end"]}
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--raw-root",required=True);ap.add_argument("--days",type=int,default=7);ap.add_argument("--out",default="structural_hedge_kpi.json");a=ap.parse_args()
    files=sorted(Path(a.raw_root).glob("????-??-??.csv"))[-a.days:]
    if not files:raise SystemExit("NO_REAL_RAW_TICK_FILES")
    engine=BacktestEngine(BacktestEngineConfig(bypass_logging=True,run_analysis=False))
    engine.add_venue(venue=Venue("EXNESS"),oms_type=OmsType.HEDGING,account_type=AccountType.MARGIN,base_currency=USD,starting_balances=[Money.from_str("1000 USD")])
    engine.add_instrument(instrument());strategy=StructuralHedge();engine.add_strategy(strategy)
    count=0
    for file in files:
        ticks=[]
        with file.open(newline="") as f:
            reader=csv.DictReader(f)
            if not {"time","bid","ask"}.issubset(reader.fieldnames or []):raise RuntimeError("RAW_QUOTE_SCHEMA_REQUIRED")
            for row in reader:
                bid=float(row["bid"]);ask=float(row["ask"])
                if bid<=0 or ask<bid:continue
                t=stamp(row["time"])
                ticks.append(QuoteTick(instrument_id=IID,bid_price=Price.from_str(f"{bid:.5f}"),ask_price=Price.from_str(f"{ask:.5f}"),bid_size=Quantity.from_str(f"{max(.01,float(row.get('bid_size') or 1)):.2f}"),ask_size=Quantity.from_str(f"{max(.01,float(row.get('ask_size') or 1)):.2f}"),ts_event=t,ts_init=t))
        if ticks:engine.add_data(ticks);count+=len(ticks)
    engine.run()
    payload=strategy.export();payload["raw_files"]=[x.name for x in files];payload["input_ticks"]=count;payload["ohlc_input_used"]=False
    Path(a.out).write_text(json.dumps(payload,indent=2));print(json.dumps({k:v for k,v in payload.items() if k!="trades"},indent=2))
    engine.dispose()
if __name__=="__main__":main()
