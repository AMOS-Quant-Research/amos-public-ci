"""Strict AMOS AutoScope trade-export bridge; NOT a Nautilus execution adapter.

Accepts standardized AutoScope-neutral trade records and creates a validated
JSON envelope for ingestion by a Nautilus-side importer. No OHLC proxy data.
"""
import argparse
import csv
import json
from pathlib import Path
from .adapter import normalize_trades

def convert(source, destination):
    source = Path(source)
    if source.suffix.lower() == ".csv":
        with source.open(encoding="utf-8-sig", newline="") as stream:
            rows = list(csv.DictReader(stream))
    elif source.suffix.lower() == ".json":
        data = json.loads(source.read_text(encoding="utf-8"))
        rows = data["trades"] if isinstance(data, dict) else data
    else:
        raise ValueError("input must be CSV or JSON")
    normalized = normalize_trades(rows)
    envelope = {
        "schema_version": "1.0",
        "source": "autoscope-neutral-export",
        "target": "amos-nautilus-research-import",
        "data_type": "trade_history",
        "is_raw_tick": False,
        "execution_verified": False,
        "trades": normalized,
    }
    Path(destination).parent.mkdir(parents=True, exist_ok=True)
    Path(destination).write_text(json.dumps(envelope, indent=2, ensure_ascii=False), encoding="utf-8")
    return len(normalized)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source")
    parser.add_argument("destination")
    args = parser.parse_args()
    print(f"Converted {convert(args.source, args.destination)} trades")

if __name__ == "__main__":
    main()
