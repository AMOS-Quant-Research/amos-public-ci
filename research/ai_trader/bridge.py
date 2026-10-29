"""Adapters for existing AMOS M1 decision and public dagram observations.

No live order or broker transport. Research Queue admission requires an
explicit verified observation record and a separate risk snapshot.
"""
from research.ai_trader.signal_hub import normalize,ResearchQueue

def from_amos_ai_trader(signal, observed_at_ns, evidence_ref):
    if signal.get("contract")!="amos.ai-trader.research-signal.v1" or signal.get("live_trading") is not False:
        raise ValueError("invalid AMOS research signal")
    return normalize({"action":signal["action"],"symbol":signal["symbol"],
                      "entry":signal["entry"],"sl":signal["sl"],"tp":signal["tp"],
                      "observed_at_ns":observed_at_ns,"evidence_ref":evidence_ref},
                     "AMOS_AI_TRADER")

def from_dagram_observation(observation):
    if observation.get("kind") not in ("pub","public_sse_pub"):
        raise ValueError("snapshot/hello is not a newly issued signal")
    if not observation.get("source_observed",False):
        raise ValueError("not an observed SSE pub update")
    # Dagram updates may not publish entry/SL/TP; missing prices are BLOCKED
    # instead of guessed. This is intentionally conservative.
    return normalize({"action":observation.get("side",observation.get("action")),
                      "symbol":observation.get("symbol","XAUUSD"),
                      "entry":observation.get("entry"),"sl":observation.get("sl"),
                      "tp":observation.get("tp"),
                      "observed_at_ns":observation.get("observed_at_ns"),
                      "evidence_ref":observation.get("evidence_ref"),
                      "signal_id":observation.get("signal_id")},"DAGRAM_OBSERVATION")

def from_signalhub_research(signal):
    # Original C# IL proves several guard categories; it does not prove
    # the source produces valid XAUUSD research signals. Provenance mandatory.
    if signal.get("origin")!="INDEPENDENT_RESEARCH":
        raise ValueError("reverse engineered executable is not a signal source")
    return normalize(signal,"THEOPTION_SIGNALHUB_RESEARCH")
