"""Convert sanitized public SSE snapshots to causal research observations.

Do not treat plan.time as issuance unless its semantics are independently verified.
A snapshot is not proof of a newly published signal.
"""
import json
from datetime import datetime, timezone
from pathlib import Path


def normalize_public_events(summary, captured_at, output):
    """Preserve observation time and provenance; do not infer publication time."""
    if isinstance(summary, (str, Path)):
        summary = json.loads(Path(summary).read_text(encoding="utf-8"))
    captured = datetime.fromisoformat(captured_at.replace("Z", "+00:00"))
    if captured.tzinfo is None:
        raise ValueError("timezone-aware captured_at required")
    rows = []
    for index, event in enumerate(summary.get("sse_events", [])):
        for pub in event.get("publications", []):
            if not isinstance(pub, dict):
                continue
            side = pub.get("side")
            if side not in ("LONG", "SHORT"):
                continue
            rows.append({
                "schema": "amos.dagram.observation.v2",
                "source": "public_sse_snapshot",
                "event_index": index,
                "event_type": event.get("event"),
                "observed_at": captured.astimezone(timezone.utc).isoformat(),
                "timeframe": pub.get("tf"),
                "revision": pub.get("revision"),
                "side": side,
                "entry": pub.get("entry"),
                "sl": pub.get("sl"),
                "tp": pub.get("tp"),
                "raw_time_field": pub.get("time"),
                "issued_at": None,
                "issued_at_verified": False,
                "backtest_eligible": False,
                "live_trading": False,
            })
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
    return rows


def validate_for_native_bt(rows):
    """Fail closed: snapshot observations cannot become historical entry signals."""
    if not rows:
        return {"eligible": 0, "blocked": 0, "reason": "NO_PUBLIC_PLANS"}
    eligible = sum(bool(r.get("issued_at_verified")) and bool(r.get("backtest_eligible")) for r in rows)
    return {"eligible": eligible, "blocked": len(rows) - eligible,
            "reason": "PUBLICATION_TIME_NOT_VERIFIED" if eligible == 0 else "PARTIAL_VERIFICATION"}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("summary")
    parser.add_argument("--captured-at", required=True)
    parser.add_argument("--output", default="artifacts/dagram/observations.jsonl")
    args = parser.parse_args()
    records = normalize_public_events(args.summary, args.captured_at, args.output)
    print(json.dumps(validate_for_native_bt(records)))
