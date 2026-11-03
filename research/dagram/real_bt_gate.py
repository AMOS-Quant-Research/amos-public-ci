"""Real-publication-only profitability gate. No synthetic events, no live trading.

A server-side issuance timestamp and contemporaneous executable QuoteTicks are required
before claiming a historical Nautilus strategy backtest.
"""
import json
from datetime import datetime, timezone
from pathlib import Path


def inspect_evidence(observations, tick_start, tick_end):
    rows = list(observations)
    def parse(value):
        d = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if d.tzinfo is None:
            raise ValueError("timezone-aware timestamps required")
        return d.astimezone(timezone.utc)
    start, end = parse(tick_start), parse(tick_end)
    if start >= end:
        raise ValueError("invalid QuoteTick coverage")
    updates = [r for r in rows if r.get("event_type") == "pub" and r.get("first_seen_update")]
    verified = [r for r in updates if r.get("issued_at_verified") and r.get("issued_at")]
    aligned = [r for r in verified if start <= parse(r["issued_at"]) <= end]
    reason = ("NO_REAL_PUBLICATION_UPDATES" if not updates else
              "ISSUANCE_TIMESTAMPS_UNVERIFIED" if not verified else
              "NO_CONTEMPORANEOUS_RAW_TICKS" if not aligned else
              "READY_FOR_NATIVE_RESEARCH_BT")
    return {"signal_source": "OBSERVED_PUBLIC_SSE_ONLY",
            "live_trading": False, "profitability_verified": False,
            "pf": None, "max_dd": None, "win_rate": None,
            "tick_coverage_start": start.isoformat(),
            "tick_coverage_end": end.isoformat(),
            "public_observations": len(rows), "pub_updates": len(updates),
            "verified_issuance_updates": len(verified),
            "contemporaneous_updates": len(aligned),
            "status": "READY" if aligned else "BLOCKED",
            "reason": reason}


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--observations", required=True)
    p.add_argument("--tick-start", required=True)
    p.add_argument("--tick-end", required=True)
    p.add_argument("--output", required=True)
    a = p.parse_args()
    rows = [json.loads(s) for s in Path(a.observations).read_text().splitlines() if s.strip()]
    result = inspect_evidence(rows, a.tick_start, a.tick_end)
    path = Path(a.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))
