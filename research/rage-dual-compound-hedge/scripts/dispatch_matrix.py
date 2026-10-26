"""Write the Nautilus cell plan. Does not install Nautilus or read a catalog."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from adapters.nautilus.matrix import PUBLIC_MAX_PARALLEL, build_cells, paired, shard_cells  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--groups", type=int, default=PUBLIC_MAX_PARALLEL)
    args = parser.parse_args()
    cells = build_cells()
    shards = shard_cells(cells, args.groups)
    payload = {
        "live_trading": False,
        "hypothesis": "BLOCKED",
        "public_max_parallel": PUBLIC_MAX_PARALLEL,
        "groups": args.groups,
        "pairs": paired(cells),
        "market_kpi": None,
        "cells": [cell.as_dict() for cell in cells],
        "shards": [[cell.cell_id for cell in shard] for shard in shards],
    }
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
