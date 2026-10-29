"""AMOS horizontal signal research integration (no broker / order execution).

Independent functional implementation informed by *observed* dagram signal
transport and TheOptionSignalHub IL research. NOT a source-code clone.
Unknown outcomes lock the queue; duplicate event IDs are not retried.
"""
import hashlib
import json
import math
import os
from pathlib import Path
from datetime import datetime, timezone

CONTRACT="amos.signal.v1"
SOURCES={"AMOS_AI_TRADER","DAGRAM_OBSERVATION","THEOPTION_SIGNALHUB_RESEARCH"}
ACTIONS={"BUY","SELL","WAIT"}
def normalize(raw, source):
    if source not in SOURCES or not isinstance(raw,dict):
        raise ValueError("untrusted source")
    action=raw.get("action",raw.get("side"))
    action={"LONG":"BUY","SHORT":"SELL","STAY":"WAIT","HOLD":"WAIT"}.get(action,action)
    if action not in ACTIONS:
        raise ValueError("unsupported action")
    symbol=raw.get("symbol","XAUUSD")
    if symbol!="XAUUSD":
        raise ValueError("XAUUSD only")
    # Event time must be explicit and non-future. Observations are not
    # retroactively attributed to an unknown source issuance timestamp.
    observed=raw.get("observed_at_ns")
    if type(observed) is not int or observed<=0:
        raise ValueError("observation timestamp missing")
    evidence=raw.get("evidence_ref")
    if not isinstance(evidence,str) or not evidence.strip():
        raise ValueError("immutable observation evidence ref required")
    signal_id=raw.get("signal_id")
    if not isinstance(signal_id,str) or not signal_id.strip():
        # Same observation and payload -> same idempotency key.
        canonical=json.dumps([source,symbol,action,observed,evidence],
                             sort_keys=True,ensure_ascii=False)
        signal_id=hashlib.sha256(canonical.encode()).hexdigest()
    entry,sl,tp=(raw.get(x) for x in ("entry","sl","tp"))
    if action!="WAIT":
        if not all(type(x) in (int,float) and math.isfinite(x) and x>0 for x in (entry,sl,tp)):
            raise ValueError("entry, SL, TP required for actionable research signal")
        if action=="BUY" and not (sl<entry<tp):
            raise ValueError("invalid BUY price ordering")
        if action=="SELL" and not (tp<entry<sl):
            raise ValueError("invalid SELL price ordering")
    else:
        entry=sl=tp=None
    return {"contract":CONTRACT,"signal_id":signal_id,"source":source,
            "symbol":symbol,"action":action,"observed_at_ns":observed,
            "evidence_ref":evidence,"entry":entry,"sl":sl,"tp":tp,
            "research_only":True,"live_trading":False,"order_permission":"DENIED"}

def research_preflight(signal, snapshot, limits):
    """Mirrors *categories* of observed IL risk guards, not original exact math.

    This is a research-queue admission guard, never a production approval.
    """
    if signal.get("contract")!=CONTRACT or signal.get("order_permission")!="DENIED":
        return "INVALID_SIGNAL"
    if snapshot.get("locked") or snapshot.get("unknown") or snapshot.get("journal_corrupt"):
        return "LOCKED_UNKNOWN_OR_JOURNAL"
    if snapshot.get("busy"):
        return "BUSY"
    if signal["action"]=="WAIT":
        return "NO_TRADE"
    if not snapshot.get("source_verified",False):
        return "SOURCE_UNVERIFIED"
    for field in ("daily_sends","daily_losses","daily_loss_amount","worst_case_next_loss"):
        v=snapshot.get(field)
        if type(v) not in (int,float) or not math.isfinite(v) or v<0:
            return "INVALID_RISK_SNAPSHOT"
    for field in ("max_daily_sends","max_daily_losses","max_daily_loss_amount"):
        v=limits.get(field)
        if type(v) not in (int,float) or not math.isfinite(v) or v<=0:
            return "INVALID_RISK_LIMITS"
    if snapshot["daily_sends"]>=limits["max_daily_sends"]:
        return "DAILY_SEND_LIMIT"
    if snapshot["daily_losses"]>=limits["max_daily_losses"]:
        return "DAILY_LOSS_COUNT_LIMIT"
    if snapshot["daily_loss_amount"]+snapshot["worst_case_next_loss"]>limits["max_daily_loss_amount"]:
        return "DAILY_LOSS_AMOUNT_LIMIT"
    return "RESEARCH_QUEUE_ELIGIBLE"

class ResearchQueue:
    """Local research journal: fail closed; no order dispatch method exists.

    Exclusive creation prevents two concurrent workers claiming the same queue.
    All status changes are journaled with fsync; uncertain states block retries.
    """
    def __init__(self, path):
        self.path=Path(path)
        self.path.parent.mkdir(parents=True,exist_ok=True)
        self.state_path=self.path.with_suffix(self.path.suffix+".state.json")
    def _read(self):
        if not self.state_path.exists():
            if self.path.exists():
                raise RuntimeError("JOURNAL_WITHOUT_STATE_LOCKED")
            return {"locked":False,"ids":[],"pending":[]}
        try:
            state=json.loads(self.state_path.read_text())
            if type(state.get("locked")) is not bool or not isinstance(state.get("ids"),list) or not isinstance(state.get("pending"),list):
                raise ValueError("invalid journal state")
            return state
        except (OSError,ValueError,TypeError) as exc:
            raise RuntimeError("JOURNAL_CORRUPT_LOCKED") from exc
    def _persist(self,state):
        temp=self.state_path.with_suffix(self.state_path.suffix+".tmp")
        try:
            with temp.open("x",encoding="utf-8") as f:
                json.dump(state,f,sort_keys=True,allow_nan=False)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temp,self.state_path)
        finally:
            temp.unlink(missing_ok=True)
    def admit(self,signal,snapshot,limits):
        state=self._read()
        if state["locked"]:
            return {"status":"LOCKED","queued":False}
        if signal["signal_id"] in state["ids"]:
            return {"status":"DUPLICATE","queued":False}
        verdict=research_preflight(signal,snapshot,limits)
        if verdict!="RESEARCH_QUEUE_ELIGIBLE":
            return {"status":verdict,"queued":False}
        # Atomic exclusive lock; single-writer only, refuse concurrent mutation.
        lock=self.state_path.with_suffix(self.state_path.suffix+".writer.lock")
        try:
            fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
        except FileExistsError:
            return {"status":"CONCURRENT_WRITER_LOCKED","queued":False}
        try:
            os.close(fd)
            state=self._read()
            if state["locked"] or signal["signal_id"] in state["ids"]:
                return {"status":"LOCKED_OR_DUPLICATE","queued":False}
            state["ids"].append(signal["signal_id"])
            state["pending"].append(signal)
            # Crash between state and event log is detected and locked on next
            # recovery; no order or external side effect is possible.
            self._persist(state)
            with self.path.open("a",encoding="utf-8") as f:
                f.write(json.dumps({"event":"RESEARCH_QUEUED","signal_id":signal["signal_id"],
                                    "order_permission":"DENIED"},sort_keys=True)+"\n")
                f.flush()
                os.fsync(f.fileno())
            return {"status":"QUEUED_FOR_RESEARCH","queued":True}
        except (OSError,ValueError) as exc:
            raise RuntimeError("JOURNAL_WRITE_FAILED_LOCKED") from exc
        finally:
            lock.unlink(missing_ok=True)
    def mark_unknown(self):
        lock=self.state_path.with_suffix(self.state_path.suffix+".writer.lock")
        try:
            fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
        except FileExistsError:
            raise RuntimeError("CONCURRENT_WRITER_LOCKED")
        try:
            os.close(fd)
            state=self._read()
            state["locked"]=True
            self._persist(state)
        finally:
            lock.unlink(missing_ok=True)
