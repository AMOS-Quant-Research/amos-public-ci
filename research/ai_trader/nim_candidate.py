"""NVIDIA NIM parameter proposer for the Raw Tick Nautilus research lane.

NIM can propose bounded parameters only. The shared client records the model
actually called; no fallback output is ever relabelled as a requested model.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path

from scripts import nim_client

ALLOWED = {"period", "rsi_long", "rsi_short", "max_spread_atr"}

def validate(params):
    if not isinstance(params, dict) or set(params) != ALLOWED:
        raise ValueError("NIM parameter fields invalid")
    if type(params["period"]) is not int or not 5 <= params["period"] <= 100:
        raise ValueError("period invalid")
    for name, lower, upper in (("rsi_long", 50, 80), ("rsi_short", 20, 50), ("max_spread_atr", 0.01, 1)):
        value = params[name]
        if type(value) not in (int, float) or not lower <= value <= upper:
            raise ValueError(name + " invalid")
    return params

def _parse_parameters(content):
    content = content.strip()
    fence = chr(96) * 3
    if content.startswith(fence):
        content = content.split("\n", 1)[1].rsplit(fence, 1)[0].strip()
    return validate(json.loads(content))

def generate(chat_fn=None):
    if not os.environ.get("NVIDIA_NIM_API_KEY", "").strip():
        raise RuntimeError("NIM_SECRET_MISSING")
    prompt = (
        "Return ONLY JSON with keys period, rsi_long, rsi_short, max_spread_atr. "
        "Research-only XAUUSD M1 technical indicator parameters. "
        "period integer 5..100, rsi_long 50..80, rsi_short 20..50, "
        "max_spread_atr number 0.01..1. Do not claim profits or give orders."
    )
    result = (chat_fn or nim_client.chat)(
        "fast",
        [{"role": "user", "content": prompt}],
        max_tokens=200,
        timeout=150,
        temperature=0.2,
    )
    parameters = _parse_parameters(result["content"])
    digest = hashlib.sha256(
        json.dumps(result["response"], sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()
    return {
        "source": "NVIDIA_NIM",
        "model": result["model"],
        "requested_model": result["requested_model"],
        "model_fallback": result["switched"],
        "response_sha256": digest,
        "parameters": parameters,
        "research_only": True,
        "live_trading": False,
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = generate()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print("NIM_VALIDATED_CANDIDATE", result["response_sha256"], "model=" + result["model"])

if __name__ == "__main__":
    main()
