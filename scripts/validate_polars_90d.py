"""Validate an existing 90-day quote parquet dataset without substituting OHLC."""
import argparse
import json
from pathlib import Path
import polars as pl
from modules.polars_tick_engine import scan_quotes, quality_report

def validate(paths, start, end):
    frames = [scan_quotes(p) for p in paths]
    lf = pl.concat(frames)
    requested_start = pl.Series([start]).str.to_datetime(time_zone="UTC").item()
    requested_end = pl.Series([end]).str.to_datetime(time_zone="UTC").item()
    lf = lf.filter(pl.col("ts_event").is_between(requested_start, requested_end, closed="both"))
    summary = quality_report(lf)
    bounds = lf.select(
        pl.col("ts_event").min().alias("first"),
        pl.col("ts_event").max().alias("last"),
        (pl.col("spread") < 0).sum().alias("negative_spread"),
        pl.col("spread").min().alias("min_spread"),
        pl.col("spread").max().alias("max_spread"),
    ).collect().row(0, named=True)
    # Distinct UTC calendar dates, including weekends, are not expected to be 90.
    days = lf.select(pl.col("ts_event").dt.date().n_unique().alias("trading_days")).collect().item()
    hourly = lf.group_by_dynamic("ts_event", every="1h").agg(pl.len().alias("ticks")).collect().sort("ts_event")
    gap_hours = []
    if hourly.height > 1:
        intervals = hourly["ts_event"].diff().dt.total_hours().to_list()[1:]
        gap_hours = [int(h) for h in intervals if h is not None and h > 1]
    issues = []
    if summary["rows"] == 0: issues.append("empty")
    if any(summary[k] for k in ("invalid_quotes", "null_timestamps", "duplicate_quotes")): issues.append("quality")
    if bounds["first"] is None or bounds["last"] is None or bounds["first"] > requested_start or bounds["last"] < requested_end:
        issues.append("incomplete_time_coverage")
    if bounds["negative_spread"]: issues.append("negative_spread")
    return {
        "status": "PASS" if not issues else "INVALID",
        "issues": issues, "input_files": [str(p) for p in paths],
        "requested_start_utc": start, "requested_end_utc": end,
        **summary,
        **{k: str(v) if k in ("first", "last") else v for k, v in bounds.items()},
        "trading_days": days, "hourly_buckets_with_ticks": hourly.height,
        "gaps_over_1h_count": len(gap_hours), "largest_hourly_gap_hours": max(gap_hours, default=0),
        "ohlc_resample_used": False,
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--glob", required=True, help="Glob of parquet quote files")
    parser.add_argument("--start", required=True, help="ISO UTC inclusive start")
    parser.add_argument("--end", required=True, help="ISO UTC inclusive end")
    parser.add_argument("--output", default="polars_90d_quality.json")
    args = parser.parse_args()
    paths = sorted(Path().glob(args.glob))
    if not paths:
        raise SystemExit("BLOCKED: no matching quote parquet files")
    result = validate(paths, args.start, args.end)
    Path(args.output).write_text(json.dumps(result, indent=2, default=str))
    print(json.dumps(result, indent=2, default=str))
    if result["status"] != "PASS":
        raise SystemExit(1)
