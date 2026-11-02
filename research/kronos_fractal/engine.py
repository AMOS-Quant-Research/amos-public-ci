"""Causal M1-structure learner.

This module learns from completed Raw Bid/Ask ticks only and predicts the state
of the next M5/M15 window from the internal structure of completed M1 bars.
"""
from __future__ import annotations
import csv, hashlib, json, math
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

PHASES = ("drive", "pullback", "compression", "expansion", "exhaustion")
CLASSES = ("down", "flat", "up")

@dataclass(frozen=True)
class Tick:
    ts: datetime
    bid: float
    ask: float

def parse_ticks(path: str | Path) -> list[Tick]:
    ticks, previous = [], None
    with Path(path).open(newline="") as fh:
        for row in csv.DictReader(fh):
            raw = row.get("timestamp") or row.get("ts") or row.get("time")
            if not raw: raise ValueError("missing timestamp column")
            ts = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if ts.tzinfo is None: raise ValueError("timestamp must include UTC offset")
            ts = ts.astimezone(timezone.utc)
            bid, ask = float(row["bid"]), float(row["ask"])
            if bid > ask: raise ValueError("invalid quote: bid exceeds ask")
            if previous and ts <= previous: raise ValueError("timestamps must be strictly monotonic")
            ticks.append(Tick(ts, bid, ask)); previous = ts
    if not ticks: raise ValueError("no ticks")
    return ticks

def _floor(ts: datetime, seconds: int) -> datetime:
    epoch = int(ts.timestamp())
    return datetime.fromtimestamp(epoch - epoch % seconds, tz=timezone.utc)

def bars(ticks: list[Tick], seconds: int) -> list[dict]:
    grouped: dict[datetime, list[Tick]] = defaultdict(list)
    for tick in ticks: grouped[_floor(tick.ts, seconds)].append(tick)
    out = []
    for start in sorted(grouped):
        group = grouped[start]; mids = [(x.bid + x.ask) / 2 for x in group]; spreads = [x.ask - x.bid for x in group]
        out.append({"start": start.isoformat(), "open": mids[0], "high": max(mids), "low": min(mids), "close": mids[-1],
                    "tick_count": len(group), "spread_mean": sum(spreads) / len(spreads), "spread_max": max(spreads)})
    return out

def _phase(bar: dict) -> str:
    body, width = abs(bar["close"] - bar["open"]), bar["high"] - bar["low"]
    if width == 0 or body / width < .22: return "compression"
    if body / width > .80: return "expansion"
    if bar["tick_count"] <= 2: return "exhaustion"
    return "drive" if bar["close"] >= bar["open"] else "pullback"

def _attach_microstructure(m1: list[dict], five: list[dict], fifteen: list[dict]) -> list[dict]:
    five_by_start, fifteen_by_start = ({x["start"]: x for x in bars_} for bars_ in (five, fifteen))
    for bar in m1:
        start, base = datetime.fromisoformat(bar["start"]), max(bar["open"], 1e-9)
        for name, table, step in (("micro_5s_path", five_by_start, 5), ("micro_15s_path", fifteen_by_start, 15)):
            bar[name] = []
            for offset in range(0, 60, step):
                child = table.get(datetime.fromtimestamp(start.timestamp() + offset, tz=timezone.utc).isoformat())
                bar[name].append((child["close"] - child["open"]) / base if child else 0.0)
    return m1

def _vector(history: list[dict]) -> list[float]:
    base, vec = max(history[-1]["close"], 1e-9), []
    for bar in history:
        vec += [(bar["close"] - bar["open"]) / base, (bar["high"] - bar["low"]) / base,
                bar["spread_mean"] / base, math.log1p(bar["tick_count"])]
        vec += [1.0 if _phase(bar) == phase else 0.0 for phase in PHASES]
        vec += bar.get("micro_5s_path", [0.0] * 12) + bar.get("micro_15s_path", [0.0] * 4)
    return vec

def make_examples(m1: list[dict], horizon_minutes: int = 5, lookback: int = 5, deadband_bps: float = 1.0) -> list[dict]:
    examples = []
    for i in range(lookback - 1, len(m1) - horizon_minutes):
        start, end = m1[i]["close"], m1[i + horizon_minutes]["close"]; bps = (end - start) / start * 10000
        label = "up" if bps > deadband_bps else "down" if bps < -deadband_bps else "flat"
        examples.append({"input_end": m1[i]["start"], "horizon_minutes": horizon_minutes,
                         "features": _vector(m1[i - lookback + 1:i + 1]), "label": label, "realized_bps": bps})
    return examples

def fit_centroid(examples: list[dict]) -> dict:
    if not examples: raise ValueError("no training examples")
    dimension, grouped = len(examples[0]["features"]), {label: [] for label in CLASSES}
    for item in examples: grouped[item["label"]].append(item["features"])
    centroids = {label: ([sum(row[j] for row in rows) / len(rows) for j in range(dimension)] if rows else None)
                 for label, rows in grouped.items()}
    return {"model_type": "centroid_v1", "classes": CLASSES, "priors": {x: len(grouped[x]) / len(examples) for x in CLASSES}, "centroids": centroids}

def predict(model: dict, features: list[float]) -> dict:
    scores = {label: (-sum((a-b)**2 for a, b in zip(features, point)) if point else -1e99)
              for label, point in model["centroids"].items()}
    winner, ordered = max(scores, key=scores.get), sorted(scores.values())
    scale = max(1e-9, ordered[-1] - ordered[0]); confidence = 1 / (1 + math.exp(-(ordered[-1] - ordered[-2]) / scale * 4))
    return {"state": winner, "confidence": round(confidence, 6), "scores": scores}

def tick_hash(ticks: list[Tick]) -> str:
    return hashlib.sha256("\n".join(f"{x.ts.isoformat()},{x.bid:.10f},{x.ask:.10f}" for x in ticks).encode()).hexdigest()

def train_and_evaluate(ticks: list[Tick], train_ratio: float = .70) -> dict:
    five, fifteen, m1 = bars(ticks, 5), bars(ticks, 15), bars(ticks, 60)
    m1 = _attach_microstructure(m1, five, fifteen)
    if len(m1) < 30: raise ValueError("need at least 30 completed M1 bars")
    output = {"bar_counts": {"5s": len(five), "15s": len(fifteen), "1m": len(m1)}, "forecasts": {},
              "data_sha256": tick_hash(ticks), "live_trading": False}
    for horizon in (5, 15):
        examples = make_examples(m1, horizon); cut = max(1, int(len(examples) * train_ratio)); model = fit_centroid(examples[:cut]); test = examples[cut:]
        predictions = [{**{"input_end": x["input_end"], "realized_bps": x["realized_bps"]}, **predict(model, x["features"]), "actual": x["label"]} for x in test]
        output["forecasts"][f"M{horizon}"] = {"model": model, "oos_samples": len(predictions),
          "directional_accuracy": sum(x["state"] == x["actual"] for x in predictions) / len(predictions) if predictions else None, "predictions": predictions}
    return output

def save_report(result: dict, output: str | Path) -> Path:
    path = Path(output); path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n"); return path
