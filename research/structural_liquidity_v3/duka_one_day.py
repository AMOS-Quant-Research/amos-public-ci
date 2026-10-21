import argparse,csv,datetime as dt,lzma,struct,time,urllib.request,urllib.error
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--date',required=True);p.add_argument('--out',required=True);a=p.parse_args()
day=dt.date.fromisoformat(a.date);rows=[];rec=struct.Struct('>3I2f')
hosts=['https://datafeed.dukascopy.com/datafeed','https://www.dukascopy.com/datafeed']
for hour in range(24):
    done=False
    for host in hosts:
        url=f'{host}/XAUUSD/{day.year}/{day.month-1:02d}/{day.day:02d}/{hour:02d}h_ticks.bi5'
        for attempt in range(4):
            try:
                with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0','Accept':'*/*'}),timeout=40) as response:raw=response.read()
                data=lzma.decompress(raw)
                for ms,ask,bid,askvol,bidvol in rec.iter_unpack(data):
                    ts=dt.datetime(day.year,day.month,day.day,hour,tzinfo=dt.timezone.utc)+dt.timedelta(milliseconds=ms)
                    rows.append((ts.isoformat(),bid/1000,ask/1000))
                done=True;break
            except urllib.error.HTTPError as e:
                if e.code in (404,204):done=True;break
                if attempt==3:print(f'HTTP {e.code} {url}',flush=True)
                time.sleep(min(2**attempt,8))
            except Exception as e:
                if attempt==3:print(f'error {e} {url}',flush=True)
                time.sleep(min(2**attempt,8))
        if done:break
    if not done:raise RuntimeError(f'Failed to download hour {hour} after both hosts')
Path(a.out).parent.mkdir(parents=True,exist_ok=True)
with open(a.out,'w',newline='') as f:
    w=csv.writer(f);w.writerow(['time','bid','ask']);w.writerows(sorted(rows))
print('raw_quotes',len(rows))
if not rows:raise SystemExit('No raw quotes downloaded')
