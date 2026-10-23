"""AMOS v3 isolated raw quote tick event pilot. Experimental virtual fills, NOT real order fills."""
import argparse,csv,json,datetime as dt
from collections import deque
import nautilus_trader
def stamp(s):return dt.datetime.fromisoformat(s.replace('Z','+00:00')).timestamp()
def run(path):
    bars=[];bar=None;bucket=None;phase=0;first=None;hedge=None;second=None;records=[];lock_count=0;maxdd=0;peak=1000.;equity=1000.;ticks=0;hedge_pnl=0.
    lastbid=lastask=0.
    def mark(bid,ask):
        v=equity
        if first is not None:v+=(bid-first)*0.01*100
        if hedge is not None:v+=(hedge-ask)*0.01*100
        if second is not None:v+=(bid-second)*0.01*100
        return v
    def closebar(b):
        nonlocal phase,first,hedge,second,equity,hedge_pnl,lock_count
        bars.append(b)
        if len(bars)<12:return
        recent=bars[-11:-1];lo=min(x['l'] for x in recent);hi=max(x['h'] for x in recent)
        if phase==0 and b['l']<lo and b['c']>b['o']:
            first=b['ask'];phase=1;records.append({'event':'BUY1','ts':b['ts'],'price':first})
        elif phase==1:
            # bullish advance then bearish reversal at completed bar: FVG proxy only, not audited FVG.
            if b['c']>first+1 and b['c']<b['o'] and (b['ask']-first)>0.5:
                hedge=b['bid'];phase=2;lock_count+=1;records.append({'event':'HEDGE','ts':b['ts'],'price':hedge})
        elif phase==2 and b['l']<lo and b['c']>b['o']:
            second=b['ask'];phase=3;records.append({'event':'BUY2','ts':b['ts'],'price':second})
        elif phase==3 and b['c']>b['o'] and b['c']>bars[-2]['h']:
            gain=(hedge-b['ask'])*1.;equity+=gain;hedge_pnl+=gain;hedge=None;phase=4;records.append({'event':'HEDGE_EXIT','ts':b['ts'],'pnl':gain})
        elif phase==4 and b['c']>hi:
            gain=(b['bid']-first)+(b['bid']-second);equity+=gain
            records.append({'event':'CYCLE_EXIT','ts':b['ts'],'pnl':gain});first=second=None;phase=0
    with open(path,newline='') as f:
        for row in csv.DictReader(f):
            ts=stamp(row['time']);bid=float(row['bid']);ask=float(row['ask']);ticks+=1
            lastbid=bid;lastask=ask
            bucket_now=int(ts//300)
            if bucket is None or bucket_now!=bucket:
                if bar:closebar(bar)
                bucket=bucket_now;mid=(bid+ask)/2
                bar={'ts':bucket*300,'o':mid,'h':mid,'l':mid,'c':mid,'bid':bid,'ask':ask}
            else:
                mid=(bid+ask)/2;bar['h']=max(bar['h'],mid);bar['l']=min(bar['l'],mid);bar['c']=mid;bar['bid']=bid;bar['ask']=ask
            v=mark(bid,ask);peak=max(peak,v);maxdd=max(maxdd,peak-v)
    if bar:closebar(bar)
    return {'model':'AMOS_Structural_Liquidity_Adaptive_Hedge_v3_pilot','engine':'NautilusTrader installed and imported; experimental virtual execution, not BacktestEngine orders','nautilus_version':nautilus_trader.__version__,'data':'Dukascopy raw bid ask ticks','raw_ticks':ticks,'bars_m5':len(bars),'hedge_lock_events':lock_count,'closed_cycles':sum(x['event']=='CYCLE_EXIT' for x in records),'realized_equity_proxy_usd':equity,'max_floating_dd_proxy_usd':maxdd,'WR':None,'PF':None,'RF':None,'status':'EXPERIMENTAL_NOT_VALIDATED','events':records}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--csv',required=True);p.add_argument('--out',required=True);a=p.parse_args()
    r=run(a.csv)
    with open(a.out,'w') as f:json.dump(r,f,indent=2)
    print(json.dumps({k:v for k,v in r.items() if k!='events'}))
