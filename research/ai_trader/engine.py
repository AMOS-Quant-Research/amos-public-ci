"""AMOS independent XAUUSD M1 research decision engine (no order execution).

Consumes verified historical bid/ask QuoteTick exports, not UI demo candles.
The Russell2000_Indicators_Fixed.zip is a synthetic UI reference ONLY; SAR
there is explicitly a placeholder. This module independently calculates
closed-bar RSI, CCI, WPR, SMA and a volatility stop from real bid/ask data.
"""
import argparse
import csv
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

CONTRACT = "amos.ai-trader.research-signal.v1"

def read_quotes(path):
    rows = []
    with Path(path).open(newline="") as f:
        reader = csv.DictReader(f)
        if not {"ts_event", "bid", "ask"} <= set(reader.fieldnames or []):
            raise ValueError("expected ts_event,bid,ask CSV")
        prev = -1
        for r in reader:
            ts = int(r["ts_event"])
            bid, ask = float(r["bid"]), float(r["ask"])
            if ts <= prev or not all(map(math.isfinite, (bid, ask))) or bid <= 0 or ask < bid:
                raise ValueError("invalid/unsorted raw quote")
            rows.append((ts, bid, ask))
            prev = ts
    if len(rows) < 1000:
        raise ValueError("at least 1000 real quote ticks required")
    return rows

def minute_bars(rows):
    bars = []
    bucket = None
    for ts, bid, ask in rows:
        minute = ts // 60_000_000_000  # Nautilus ts_event nanoseconds
        mid = (bid + ask) / 2
        if bucket is None or minute != bucket:
            if bars:
                bars[-1]["closed"] = True
            bars.append({"minute": minute, "open": mid, "high": mid, "low": mid,
                         "close": mid, "bid": bid, "ask": ask, "ticks": 0, "closed": False})
            bucket = minute
        b = bars[-1]
        b["high"] = max(b["high"], mid)
        b["low"] = min(b["low"], mid)
        b["close"] = mid
        b["bid"], b["ask"] = bid, ask
        b["ticks"] += 1
    return [b for b in bars if b["closed"]]  # never use an unfinished candle

def features(bars, period=21):
    if type(period) is not int or not 5 <= period <= 100:
        raise ValueError("invalid period")
    if len(bars) < period + 2:
        raise ValueError("insufficient completed M1 bars")
    closes = [b["close"] for b in bars]
    tail = closes[-period:]
    diffs = [closes[i] - closes[i-1] for i in range(len(closes)-period, len(closes))]
    gains = sum(max(d, 0) for d in diffs) / period
    losses = sum(max(-d, 0) for d in diffs) / period
    rsi = 100 * gains / (gains + losses) if gains + losses else 50.0
    typical = [(b["high"] + b["low"] + b["close"]) / 3 for b in bars[-period:]]
    tp_mean = sum(typical) / period
    md = sum(abs(x - tp_mean) for x in typical) / period
    cci = (typical[-1] - tp_mean) / (.015 * md) if md else 0.0
    hh = max(b["high"] for b in bars[-period:])
    ll = min(b["low"] for b in bars[-period:])
    wpr = -100 * (hh - closes[-1]) / (hh - ll) if hh > ll else -50.0
    sma = sum(tail) / period
    true_ranges = [max(b["high"]-b["low"], abs(b["high"]-bars[i-1]["close"]),
                       abs(b["low"]-bars[i-1]["close"]))
                   for i,b in enumerate(bars) if i > 0]
    atr = sum(true_ranges[-period:]) / period
    return {"rsi": rsi, "cci": cci, "wpr": wpr, "sma": sma, "atr": atr}

def decide(bars, params=None):
    p = params or {"period": 21, "rsi_long": 55, "rsi_short": 45, "max_spread_atr": .3}
    if set(p) != {"period", "rsi_long", "rsi_short", "max_spread_atr"}:
        raise ValueError("candidate parameter allowlist mismatch")
    period = p["period"]
    if type(period) is not int or not 5 <= period <= 100:
        raise ValueError("invalid period")
    if not 50 <= p["rsi_long"] <= 80 or not 20 <= p["rsi_short"] <= 50:
        raise ValueError("invalid RSI threshold")
    if not 0 < p["max_spread_atr"] <= 1:
        raise ValueError("invalid spread bound")
    f = features(bars, period)
    b = bars[-1]
    spread = b["ask"] - b["bid"]
    direction = "WAIT"
    if f["atr"] > 0 and spread <= f["atr"] * p["max_spread_atr"]:
        if b["close"] > f["sma"] and f["rsi"] >= p["rsi_long"] and f["cci"] > 0 and f["wpr"] > -50:
            direction = "BUY"
        elif b["close"] < f["sma"] and f["rsi"] <= p["rsi_short"] and f["cci"] < 0 and f["wpr"] < -50:
            direction = "SELL"
    entry = b["ask"] if direction == "BUY" else b["bid"] if direction == "SELL" else None
    stop_distance = 1.5 * f["atr"] if direction != "WAIT" else None
    sl = entry - stop_distance if direction == "BUY" else entry + stop_distance if direction == "SELL" else None
    tp = entry + 2 * stop_distance if direction == "BUY" else entry - 2 * stop_distance if direction == "SELL" else None
    return {"contract": CONTRACT, "symbol": "XAUUSD", "timeframe": "M1",
            "closed_bar_minute": b["minute"], "action": direction, "entry": entry,
            "sl": sl, "tp": tp, "features": f, "spread": spread,
            "parameters": p, "signal_is_order": False, "live_trading": False}

def intake(signal, provenance, native_evidence=None, ai_candidate=None):
    """Stages 3/5/6: AI proposals are untrusted, native evidence required.
    This prepares a CoreAI research envelope; does NOT claim actual delivery.
    """
    if signal.get("contract") != CONTRACT:
        raise ValueError("unknown signal contract")
    if provenance.get("kind") != "REAL_XAUUSD_BID_ASK_QUOTETICKS":
        raise ValueError("raw tick provenance required")
    if not provenance.get("sha256") or provenance.get("count", 0) < 1000:
        raise ValueError("insufficient raw tick provenance")
    if ai_candidate is not None:
        if ai_candidate.get("source") != "NVIDIA_NIM" or not ai_candidate.get("model") or not ai_candidate.get("response_sha256"):
            raise ValueError("AI candidate lacks verifiable NIM provenance")
        # Candidate must have been validated by decide(); never trust LLM order instructions.
        if ai_candidate.get("parameters") != signal["parameters"]:
            raise ValueError("AI parameters differ from evaluated signal")
    native_ok = bool(native_evidence and native_evidence.get("native_fills", 0) >= 1
                     and native_evidence.get("oos_verified") is True
                     and native_evidence.get("costs_calibrated") is True
                     and native_evidence.get("risk_verified") is True
                     and native_evidence.get("reproducible") is True)
    return {"contract": "amos.coreai.research-intake.v1", "signal": signal,
            "raw_tick_provenance": provenance, "ai_candidate": ai_candidate,
            "native_evidence": native_evidence,
            "status": "RESEARCH_READY_FOR_COREAI" if native_ok else "BLOCKED_PENDING_NATIVE_OOS_COST_RISK",
            "delivery_status": "NOT_DELIVERED", "coreai_acknowledged": False,
            "risk_governor_approved": False, "order_permission": "DENIED",
            "live_trading": False}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--quotes", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--params", type=Path)
    p.add_argument("--native-evidence", type=Path)
    p.add_argument("--ai-candidate", type=Path)
    a = p.parse_args()
    rows = read_quotes(a.quotes)
    bars = minute_bars(rows)
    if len(bars) < 24:
        raise ValueError("insufficient completed M1 bars")
    params = json.loads(a.params.read_text()) if a.params else None
    signal = decide(bars, params)
    provenance = {"kind": "REAL_XAUUSD_BID_ASK_QUOTETICKS",
                  "sha256": hashlib.sha256(a.quotes.read_bytes()).hexdigest(), "count": len(rows)}
    evidence = json.loads(a.native_evidence.read_text()) if a.native_evidence else None
    ai = json.loads(a.ai_candidate.read_text()) if a.ai_candidate else None
    output = intake(signal, provenance, evidence, ai)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(output, ensure_ascii=False, indent=2, allow_nan=False)+"\n")
    print(json.dumps({"status": output["status"], "action": signal["action"],
                      "delivery_status": output["delivery_status"]}))
if __name__ == "__main__":
    main()
