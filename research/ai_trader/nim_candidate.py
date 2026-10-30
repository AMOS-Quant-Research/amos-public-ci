"""NVIDIA NIM parameter proposer, strictly bounded, research-only.
No fallback candidate is ever labeled as NIM-generated.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import urllib.request

ALLOWED={"period","rsi_long","rsi_short","max_spread_atr"}
def validate(params):
    if not isinstance(params,dict) or set(params)!=ALLOWED:
        raise ValueError("NIM parameter fields invalid")
    if type(params["period"]) is not int or not 5<=params["period"]<=100:
        raise ValueError("period invalid")
    for name,lo,hi in (("rsi_long",50,80),("rsi_short",20,50),("max_spread_atr",0.01,1)):
        x=params[name]
        if type(x) not in (int,float) or not lo<=x<=hi:
            raise ValueError(name+" invalid")
    return params

def generate(request_fn=None):
    token=os.environ.get("NVIDIA_NIM_API_KEY","").strip()
    if not token:
        raise RuntimeError("NIM_SECRET_MISSING")
    model=os.environ.get("NVIDIA_NIM_MODEL") or os.environ.get("NIM_MODEL") or "nvidia/nemotron-3.5-bolt-e4b"
    prompt=('Return ONLY JSON with keys period, rsi_long, rsi_short, max_spread_atr. '
            'Research-only XAUUSD M1 technical indicator parameters. '
            'period integer 5..100, rsi_long 50..80, rsi_short 20..50, '
            'max_spread_atr number 0.01..1. Do not claim profits or give orders.')
    body={"model":model,"messages":[{"role":"user","content":prompt}],
          "temperature":0.2,"max_tokens":150}
    request=urllib.request.Request("https://integrate.api.nvidia.com/v1/chat/completions",
        data=json.dumps(body).encode(),method="POST",
        headers={"Authorization":"Bearer "+token,"Content-Type":"application/json"})
    with (request_fn or urllib.request.urlopen)(request,timeout=150) as response:
        raw=json.load(response)
    content=raw["choices"][0]["message"]["content"].strip()
    if content.startswith("```"):
        content=content.split("\n",1)[1].rsplit("```",1)[0].strip()
    params=validate(json.loads(content))
    digest=hashlib.sha256(json.dumps(raw,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    return {"source":"NVIDIA_NIM","model":model,"response_sha256":digest,
            "parameters":params,"research_only":True,"live_trading":False}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",required=True,type=Path)
    a=p.parse_args()
    result=generate()
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    print("NIM_VALIDATED_CANDIDATE",result["response_sha256"])
if __name__=="__main__":
    main()
