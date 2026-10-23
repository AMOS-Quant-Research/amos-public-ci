"""Consensus is descriptive, not trading advice. No missing engine votes."""
import re
from collections import Counter
def summarize(results):
    votes={}
    for name,result in results.items():
        if result.get("status")!="OK":continue
        report=result.get("report","")
        if not isinstance(report,str):continue
        matches=re.findall(r"\b(?:BUY|SELL|WAIT)\b",report.upper())
        unique=set(matches)
        if len(unique)==1:votes[name]=matches[0]
    counts=Counter(votes.values())
    if not votes:decision="INSUFFICIENT_DATA"
    elif len(counts)==1 and len(votes)==len(results):decision=next(iter(counts))
    else:decision="MIXED"
    return {"decision":decision,"votes":votes,"counts":dict(counts),"participating":len(votes),"total":len(results),"note":"Heuristic text vote; not validated trading signal."}
