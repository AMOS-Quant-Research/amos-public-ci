"""Offline dagram observation -> Vibe SignalEngine adapter. Research only; no orders."""
import json
from pathlib import Path
import pandas as pd

class SignalEngine:
    def __init__(self, observations_path="artifacts/dagram_publications.json"):
        self.path=Path(observations_path)
    def generate(self, bars):
        if set(bars)!={"XAUUSD"}: raise ValueError("XAUUSD only")
        idx=pd.DatetimeIndex(bars["XAUUSD"].index)
        if idx.tz is None or not idx.is_monotonic_increasing or idx.has_duplicates:
            raise ValueError("ordered, unique, timezone-aware M1 bars required")
        idx=idx.tz_convert("UTC")
        if not self.path.is_file(): raise FileNotFoundError(self.path)
        events=json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(events,list): raise ValueError("observations must be an array")
        signals=pd.Series(float("nan"),index=idx)
        previous=None
        for event in events:
            if not isinstance(event,dict) or "issuedAt" not in event:
                raise ValueError("issuedAt required")
            ts=pd.Timestamp(event["issuedAt"])
            if ts.tzinfo is None or (previous is not None and ts<previous):
                raise ValueError("UTC timestamp and chronological observations required")
            previous=ts
            plan=event.get("plan",event)
            if plan is None: side=None
            elif isinstance(plan,dict): side=plan.get("side")
            else: raise ValueError("invalid plan")
            value={None:0.0,"LONG":1.0,"BUY":1.0,"SHORT":-1.0,"SELL":-1.0}.get(side)
            if value is None: raise ValueError("unknown side")
            pos=idx.searchsorted(ts.tz_convert("UTC"),side="right")
            if pos<len(idx): signals.iloc[pos]=value
        return {"XAUUSD":signals.ffill().fillna(0.0)}
