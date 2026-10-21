"""Double liquidity sweep, causal signal research. No G75 imports.
Input CSV columns: time,bid,ask; time is UTC ISO8601 or epoch milliseconds.
Bars are aggregated from raw bid/ask ticks. Signals only use completed bars.
This is a signal/mark-to-market research prototype, NOT Nautilus executed orders.
"""
import argparse,csv,json,datetime as dt,math
from collections import deque
def timestamp(s):
    try:return float(s)/1000 if float(s)>1e11 else float(s)
    except ValueError:return dt.datetime.fromisoformat(s.replace('Z','+00:00')).timestamp()
def backtest(path,tf=60,lookback=10,confirm=1,rr=2.,max_hold=60,fee=0.0):
    bars=[]; bucket=None; bar=None; signals=[]; pending=None; pos=None; trades=[]
    first=None; second=None; last_ts=None
    def closed(b):
        nonlocal first,second,pending,pos
        bars.append(b)
        if pos:
            side=pos['side']; stop=pos['stop']; target=pos['target']
            stop_hit=b['l']<=stop if side==1 else b['h']>=stop
            tp_hit=b['h']>=target if side==1 else b['l']<=target
            age=len(bars)-pos['index']
            if stop_hit or tp_hit or age>=max_hold:
                exit_price=stop if stop_hit else target if tp_hit else b['c']
                pnl=side*(exit_price-pos['entry'])-fee
                trades.append(dict(**pos,exit=exit_price,pnl=pnl,exit_ts=b['ts'],exit_reason='SL' if stop_hit else 'TP' if tp_hit else 'TIME'))
                pos=None
        if len(bars)<lookback+2:return
        ref=bars[-lookback-1:-1]
        lo=min(x['l'] for x in ref);hi=max(x['h'] for x in ref)
        if pending and pos is None:
            if b['ts']>pending['ts']:
                side=pending['side']; entry=b['o']; stop=pending['stop']
                risk=side*(entry-stop)
                if risk>0:
                    pos=dict(side=side,entry=entry,stop=stop,target=entry+side*rr*risk,index=len(bars),entry_ts=b['ts'],first_ts=pending['first_ts'],second_ts=pending['second_ts'])
                pending=None
        if pos or pending:return
        sweep_side=1 if b['l']<lo else (-1 if b['h']>hi else 0)
        if not sweep_side:return
        extreme=b['l'] if sweep_side==1 else b['h']
        if first is None or first['side']!=sweep_side or len(bars)-first['index']>lookback:
            first=dict(side=sweep_side,extreme=extreme,index=len(bars),ts=b['ts'])
            return
        if (sweep_side==1 and extreme<first['extreme']) or (sweep_side==-1 and extreme>first['extreme']):
            reaction=(b['c']>b['o'] and b['c']>lo) if sweep_side==1 else (b['c']<b['o'] and b['c']<hi)
            if reaction:
                pending=dict(side=sweep_side,stop=extreme,ts=b['ts'],first_ts=first['ts'],second_ts=b['ts'])
                signals.append(dict(first_ts=first['ts'],second_ts=b['ts'],side=sweep_side))
                first=None
            else:first=dict(side=sweep_side,extreme=extreme,index=len(bars),ts=b['ts'])
    with open(path,newline='') as f:
        for row in csv.DictReader(f):
            t=timestamp(row['time']); bid=float(row['bid']);ask=float(row['ask']);mid=(bid+ask)/2
            k=int(t//tf)
            if bucket is None or k!=bucket:
                if bar:closed(bar)
                bucket=k;bar=dict(ts=k*tf,o=mid,h=mid,l=mid,c=mid)
            else:bar['h']=max(bar['h'],mid);bar['l']=min(bar['l'],mid);bar['c']=mid
            last_ts=t
    if bar:closed(bar)
    wins=[x['pnl'] for x in trades if x['pnl']>0];losses=[x['pnl'] for x in trades if x['pnl']<0]
    equity=0;peak=0;dd=0
    for x in trades:
        equity+=x['pnl'];peak=max(peak,equity);dd=max(dd,peak-equity)
    return dict(model='double_liquidity_sweep',execution='signal_proxy_not_nautilus_fills',source='raw_bid_ask_ticks',bars=len(bars),signals=len(signals),trades=len(trades),WR_pct=100*len(wins)/len(trades) if trades else None,PF=sum(wins)/-sum(losses) if losses else None,net_price_units=equity,max_closed_trade_dd_price_units=dd,RR=rr,bar_seconds=tf,lookback=lookback,trades_detail=trades)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--csv',required=True);p.add_argument('--out',required=True);p.add_argument('--tf',type=int,default=60);p.add_argument('--lookback',type=int,default=10);p.add_argument('--rr',type=float,default=2);a=p.parse_args()
    result=backtest(a.csv,a.tf,a.lookback,rr=a.rr)
    with open(a.out,'w') as f:json.dump(result,f,indent=2)
    print(json.dumps({k:v for k,v in result.items() if k!='trades_detail'}))
