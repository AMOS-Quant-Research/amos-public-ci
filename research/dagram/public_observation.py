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
        event_at = event.get("observed_at", captured_at)
        observed = datetime.fromisoformat(str(event_at).replace("Z", "+00:00"))
        if observed.tzinfo is None:
            raise ValueError("SSE observed_at must have timezone")
        publications = list(event.get("publications", []))
        if isinstance(event.get("publication"), dict):
            publications.append(event["publication"])
        for pub in publications:
            if not isinstance(pub, dict):
                continue
            side = pub.get("side")
            if side not in ("LONG", "SHORT"):
                continue
            # hello is a historical snapshot. pub is an observed update,
            # but its network receipt is NOT a verified server issuance time.
            event_type = event.get("event")
            first_seen_update = event_type == "pub"
            rows.append({
                "schema": "amos.dagram.observation.v3",
                "source": "public_sse_update" if first_seen_update else "public_sse_snapshot",
                "event_index": index,
                "event_type": event_type,
                "observed_at": observed.astimezone(timezone.utc).isoformat(),
                "timeframe": pub.get("tf"),
                "revision": pub.get("revision"),
                "plan_id": pub.get("id"),
                "phase": pub.get("phase"),
                "side": side,
                "entry": pub.get("entry"),
                "sl": pub.get("sl"),
                "tp": pub.get("tp"),
                "raw_time_field": pub.get("time"),
                "issued_at": None,
                "issued_at_verified": False,
                "first_seen_update": first_seen_update,
                "backtest_eligible": False,
                "forward_observation_eligible": first_seen_update,
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
