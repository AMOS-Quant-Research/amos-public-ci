"""Join finished cells. This is not a fourth backtest.

Issue #42 asks for one evaluation after MAIN, RAGE, and MULTI have each
run. A transfer from MAIN to RAGE is not income. A blocked cell keeps the
scenario blocked. Ten percent is never turned into PASS here.
"""

from __future__ import annotations

from rage_dch.compound_accounting import geometric_growth, simultaneous_loss_rate

REQUIRED_BOOKS = ("MAIN", "RAGE", "MULTI")


def evaluate(rows: list[dict]) -> dict:
    if any(row.get("transfer_booked_as_profit") for row in rows):
        return {
            "status": "FAIL",
            "reason": "capital transfer or premium booked as profit",
            "market_kpi": None,
            "ten_percent": "NOT_A_PASS",
        }
    grouped: dict[str, list[dict]] = {}
    for row in rows:
        grouped.setdefault(row["scenario_id"], []).append(row)
    scenarios = []
    for scenario_id, group in sorted(grouped.items()):
        books = {row["book"] for row in group}
        missing = [book for book in REQUIRED_BOOKS if book not in books]
        measured = not missing and all(row.get("status") == "MEASURED" for row in group)
        entry = {
            "scenario_id": scenario_id,
            "books": sorted(books),
            "missing": missing,
            "market_kpi": None,
            "ten_percent": "NOT_A_PASS",
        }
        if not measured:
            entry["status"] = "BLOCKED"
            entry["reason"] = "missing book or cell not measured"
            scenarios.append(entry)
            continue
        series = {row["book"]: list(row["monthly_net"]) for row in group}
        if len({len(values) for values in series.values()}) != 1:
            entry["status"] = "FAIL"
            entry["reason"] = "monthly series are not aligned"
            scenarios.append(entry)
            continue
        entry["status"] = "CONDITIONAL"
        entry["reason"] = "joined measured series; target not accepted as pass"
        entry["geometric"] = {book: geometric_growth(values) for book, values in series.items()}
        entry["simultaneous_loss_rate"] = simultaneous_loss_rate(series["MAIN"], series["RAGE"])
        scenarios.append(entry)
    if any(item["status"] == "FAIL" for item in scenarios):
        status = "FAIL"
    elif scenarios and all(item["status"] == "CONDITIONAL" for item in scenarios):
        status = "CONDITIONAL"
    else:
        status = "BLOCKED"
    return {
        "status": status,
        "market_kpi": None,
        "ten_percent": "NOT_A_PASS",
        "parallel_cap_status": "NOT_VERIFIED",
        "scenarios": scenarios,
    }
