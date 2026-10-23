"""AutoScope-neutral AMOS trade export; does not require Windows or AutoScope binaries."""
import csv
import json
from pathlib import Path

FIELDS = ("trade_id", "symbol", "side", "entry_time", "exit_time", "entry_price", "exit_price", "quantity", "net_pnl")

def normalize_trades(records):
    output = []
    for row in records:
        missing = [key for key in FIELDS if key not in row]
        if missing:
            raise ValueError("missing fields: " + ", ".join(missing))
        side = str(row["side"]).upper()
        if side not in ("BUY", "SELL"):
            raise ValueError("side must be BUY or SELL")
        item = {key: row[key] for key in FIELDS}
        for key in ("entry_price", "exit_price", "quantity", "net_pnl"):
            item[key] = float(item[key])
        if item["quantity"] <= 0:
            raise ValueError("quantity must be positive")
        item["side"] = side
        output.append(item)
    return output

def export_json(records, destination):
    normalized = normalize_trades(records)
    Path(destination).write_text(json.dumps({"schema_version": "1.0", "trades": normalized}, ensure_ascii=False, indent=2), encoding="utf-8")
    return len(normalized)

def export_csv(records, destination):
    normalized = normalize_trades(records)
    with open(destination, "w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(normalized)
    return len(normalized)
