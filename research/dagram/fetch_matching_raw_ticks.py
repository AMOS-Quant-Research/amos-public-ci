"""Fetch public Dukascopy XAUUSD bi5 for the UTC date of observed SSE updates.

Research only. Missing hours are never silently treated as zero-tick hours.
No orders, no claim of real-time data availability.
"""
import argparse
import hashlib
import json
import lzma
import struct
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

REC = struct.Struct(">3I2f")
BASE = "https://datafeed.dukascopy.com/datafeed/XAUUSD"


def get_day(day, output, *, fetch=None):
    if day.tzinfo is None:
        raise ValueError("timezone-aware date required")
    day = day.astimezone(timezone.utc).date()
    if fetch is None:
        def fetch(url):
            with urlopen(Request(url, headers={"User-Agent": "AMOS-public-research/1"}), timeout=15) as response:
                return response.read()
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    path = output / f"xauusd-{day.isoformat()}-bidask.csv"
    hours = []
    ticks = 0
    with path.open("w", encoding="utf-8") as f:
        f.write("ts_utc,bid,ask,bid_size,ask_size\n")
        for hour in range(24):
            url = f"{BASE}/{day.year}/{day.month-1:02d}/{day.day:02d}/{hour:02d}h_ticks.bi5"
            try:
                raw = lzma.decompress(fetch(url))
                if len(raw) % REC.size:
                    raise ValueError("incomplete binary record")
                count = 0
                for offset in range(0, len(raw), REC.size):
                    ms, ask, bid, ask_size, bid_size = REC.unpack_from(raw, offset)
                    if ms >= 3600000 or not ask or not bid or ask < bid:
                        raise ValueError("invalid QuoteTick")
                    ts = datetime(day.year, day.month, day.day, hour, tzinfo=timezone.utc).timestamp() + ms / 1000
                    from datetime import datetime as dt
                    f.write(f"{dt.fromtimestamp(ts,timezone.utc).isoformat()},{bid/1000:.5f},{ask/1000:.5f},{bid_size:.6f},{ask_size:.6f}\n")
                    count += 1
                ticks += count
                hours.append({"hour": hour, "status": "OK", "ticks": count})
            except Exception as exc:
                hours.append({"hour": hour, "status": "UNAVAILABLE", "error": type(exc).__name__})
    complete = all(h["status"] == "OK" for h in hours)
    if not complete:
        path.unlink(missing_ok=True)  # prevent partial dataset being mistaken for complete
    result = {"date": str(day), "source": "Dukascopy public historical bi5",
              "complete": complete, "ticks": ticks,
              "status": "COMPLETE" if complete else "BLOCKED_MISSING_HOURS",
              "hours": hours, "live_trading": False,
              "sha256": hashlib.sha256(path.read_bytes()).hexdigest() if complete else None}
    (output / "rawtick_coverage.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--observations", required=True)
    p.add_argument("--output", required=True)
    a = p.parse_args()
    observations = [json.loads(x) for x in Path(a.observations).read_text().splitlines() if x.strip()]
    updates = [x for x in observations if x.get("first_seen_update") and x.get("event_type") == "pub"]
    if not updates:
        out = Path(a.output)
        out.mkdir(parents=True, exist_ok=True)
        (out / "rawtick_coverage.json").write_text(json.dumps({"status": "BLOCKED_NO_REAL_PUB_UPDATES",
           "complete": False, "ticks": 0, "live_trading": False}, indent=2) + "\n")
        print("BLOCKED_NO_REAL_PUB_UPDATES")
        return
    days = sorted(set(datetime.fromisoformat(x["observed_at"]).astimezone(timezone.utc).date() for x in updates))
    for day in days:
        result = get_day(datetime.combine(day, datetime.min.time(), timezone.utc), a.output)
        print(json.dumps({k: v for k, v in result.items() if k != "hours"}))


if __name__ == "__main__":
    main()
