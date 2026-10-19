"""Public-safe AMOS CI evidence contract.

This module validates a synthetic-only public CI handoff. It does NOT
fetch private repos, broker accounts, market data or secrets.
"""
from __future__ import annotations
import hashlib,json,re
from pathlib import Path

SCHEMA="amos.public_ci.synthetic.v1"
ALLOWED_KEYS={"schema","suite","source","tests_passed","tests_failed","orders_sent","artifact_sha256"}
SUITES={"stdlib_smoke","quota_router_contract","raw_tick_schema_contract"}
HEX64=re.compile(r"^[0-9a-f]{64}$")

def sha256_file(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for block in iter(lambda:f.read(1024*1024),b""):
            h.update(block)
    return h.hexdigest()

def validate(record):
    if not isinstance(record,dict) or set(record)!=ALLOWED_KEYS:
        raise ValueError("unexpected keys: only public synthetic CI metadata is allowed")
    if record["schema"]!=SCHEMA or record["suite"] not in SUITES:
        raise ValueError("unsupported schema or suite")
    if record["source"]!="PUBLIC_SYNTHETIC_ONLY":
        raise ValueError("private source or real market data not allowed")
    if type(record["tests_passed"]) is not int or record["tests_passed"]<1:
        raise ValueError("positive passed count required")
    if type(record["tests_failed"]) is not int or record["tests_failed"]!=0:
        raise ValueError("tests must pass")
    if type(record["orders_sent"]) is not int or record["orders_sent"]!=0:
        raise ValueError("no trading or orders in public CI")
    if not isinstance(record["artifact_sha256"],str) or not HEX64.fullmatch(record["artifact_sha256"]):
        raise ValueError("artifact hash invalid")
    return {"schema":SCHEMA,"status":"PUBLIC_SYNTHETIC_TEST_PASS",
            "financial_edge_verified":False,"private_code_tested":False,
            "real_data_verified":False,"broker_connected":False}

def emit(suite,fixture,out):
    source=Path(fixture)
    result={"schema":SCHEMA,"suite":suite,"source":"PUBLIC_SYNTHETIC_ONLY",
            "tests_passed":1,"tests_failed":0,"orders_sent":0,
            "artifact_sha256":sha256_file(source)}
    validate(result)
    p=Path(out);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    return result

if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--suite",choices=sorted(SUITES),default="stdlib_smoke")
    p.add_argument("--fixture",required=True)
    p.add_argument("--out",required=True)
    a=p.parse_args()
    print(json.dumps(emit(a.suite,a.fixture,a.out)))
