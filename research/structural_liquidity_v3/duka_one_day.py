import argparse,csv,datetime as dt,lzma,struct,time,urllib.request
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--date',required=True);p.add_argument('--out',required=True);a=p.parse_args()
day=dt.date.fromisoformat(a.date); rows=[];rec=struct.Struct('>3I2f')
for hour in range(24):
    url=f'https://datafeed.dukascopy.com/datafeed/XAUUSD/{day.year}/{day.month-1:02d}/{day.day:02d}/{hour:02d}h_ticks.bi5'
    for attempt in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=25) as response:raw=response.read()
            data=lzma.decompress(raw)
            for ms,ask,bid,askvol,bidvol in rec.iter_unpack(data):
                ts=dt.datetime(day.year,day.month,day.day,hour,tzinfo=dt.timezone.utc)+dt.timedelta(milliseconds=ms)
                rows.append((ts.isoformat(),bid/1000,ask/1000))
            break
        except urllib.error.HTTPError as e:
            if e.code in (404,204):break
            if attempt==3:raise
            time.sleep(2**attempt)
        except Exception:
            if attempt==3:raise
            time.sleep(2**attempt)
Path(a.out).parent.mkdir(parents=True,exist_ok=True)
with open(a.out,'w',newline='') as f:
    w=csv.writer(f);w.writerow(['time','bid','ask']);w.writerows(sorted(rows))
print('raw_quotes',len(rows))
if not rows:raise SystemExit('No raw quotes downloaded')
