"""Causal XAUUSD QuoteTick time matching; diagnostics only, never place orders."""
import json
from datetime import datetime, timezone
from pathlib import Path


def utc_ns(value):
    ts = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if ts.tzinfo is None:
        raise ValueError("UTC offset required")
    return int(ts.timestamp() * 1_000_000_000)


def match_observations(observations, quote_ticks):
    """Use first bid/ask quote strictly AFTER receipt of public pub update."""
    from bisect import bisect_right
    ticks = list(quote_ticks)
    if any(ticks[i].ts_event > ticks[i + 1].ts_event for i in range(len(ticks) - 1)):
        raise ValueError("unordered QuoteTicks")
    stamps = [int(t.ts_event) for t in ticks]
    results = []
    for row in observations:
        result = {"event_index": row.get("event_index"),
                  "timeframe": row.get("timeframe"),
                  "observed_at": row.get("observed_at"),
                  "status": "BLOCKED"}
        if not row.get("first_seen_update") or row.get("event_type") != "pub":
            result["reason"] = "NOT_A_NEW_PUBLICATION_UPDATE"
        else:
            pos = bisect_right(stamps, utc_ns(row["observed_at"]))
            if pos == len(ticks):
                result["reason"] = "NO_LATER_QUOTE_TICK"
            else:
                t = ticks[pos]
                if t.ask_price < t.bid_price:
                    raise ValueError("crossed bid/ask quote")
                result.update(status="MATCHED_FORWARD_ONLY",
                              quote_ts_ns=int(t.ts_event),
                              bid=str(t.bid_price), ask=str(t.ask_price),
                              reason="SERVER_ISSUANCE_UNVERIFIED_NO_HISTORICAL_BT")
        results.append(result)
    return results


def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--catalog", required=True)
    p.add_argument("--observations", required=True)
    p.add_argument("--instrument", default="XAUUSD.SIM")
    p.add_argument("--output", required=True)
    a = p.parse_args()
    from nautilus_trader.persistence.catalog import ParquetDataCatalog
    from nautilus_trader.model.data import QuoteTick
    catalog = ParquetDataCatalog(a.catalog)
    ticks = catalog.query(data_cls=QuoteTick, identifiers=[a.instrument])
    observations = [json.loads(line) for line in Path(a.observations).read_text().splitlines() if line.strip()]
    results = match_observations(observations, ticks)
    out = {"live_trading": False, "profitability_verified": False,
           "input_quote_ticks": len(ticks), "input_observations": len(observations),
           "matched_forward_only": sum(x["status"] == "MATCHED_FORWARD_ONLY" for x in results),
           "results": results}
    Path(a.output).parent.mkdir(parents=True, exist_ok=True)
    Path(a.output).write_text(json.dumps(out, indent=2))
    print(json.dumps({k: v for k, v in out.items() if k != "results"}))


if __name__ == "__main__":
    main()
