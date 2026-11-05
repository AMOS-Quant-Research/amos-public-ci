#!/usr/bin/env python3
"""Offline validation of the research-only AE Math EDGE Dictionary. No network or trading."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FILE = ROOT / "dictionary.json"


def validate(doc: dict) -> None:
    assert doc["contract"] == "amos.ae.math-edge-dictionary.v1"
    assert doc["governance"]["live_trading"] is False
    assert doc["governance"]["main_modified"] is False
    assert doc["governance"]["auto_merge"] is False
    assert doc["baseline"]["new_native_runs_for_dictionary"] == 0
    assert doc["baseline"]["unattended_cron"] == (
        "BLOCKED_DEFAULT_BRANCH until reviewed workflow merge; not active"
    )

    records = doc["records"]
    assert isinstance(records, list) and records, "empty dictionary"
    ids, issues, papers = set(), set(), set()
    for row in records:
        rid = row["id"]
        issue = row["issue"]
        paper = row["paper"]["arxiv"]
        assert rid not in ids and issue not in issues and paper not in papers, "duplicate"
        ids.add(rid)
        issues.add(issue)
        papers.add(paper)
        assert rid == f"AE-MATH-{issue:04d}", "ID / issue mismatch"
        assert row["issue_url"] == (
            f"https://github.com/AMOS-Quant-Research/amos-public-ci/issues/{issue}"
        )
        assert row["paper"]["url"] == f"https://arxiv.org/abs/{paper}"
        assert row["source_class"] == "ORIGINAL_AND_AE_DERIVED_SEPARATE"
        assert row["original"]["model"] and row["original"]["novelty"]
        assert row["ae_derived"]["mapping"] and row["ae_derived"]["failure_modes"]
        assert row["next_gate"] and row["blockers"]
        evidence = row["evidence"]
        assert evidence["decision"] == row["status"]
        assert row["status"] in {"HOLD", "REJECT", "PASS"}
        if row["status"] == "PASS":
            assert evidence["source_math_independently_reproduced"] is True
            assert evidence["ae_strategy_implemented"] is True
            assert evidence["native_run_id"] is not None
            assert isinstance(evidence["native_fill_count"], int)
            assert evidence["native_fill_count"] >= 1
            for key in ("pf", "ev", "max_dd"):
                assert isinstance(evidence[key], (int, float))
            assert evidence["oos_verified"] and evidence["cost_calibrated"]
        else:
            # Missing native evidence is acceptable for HOLD or REJECT;
            # do not fabricate zeros or attach unrelated Kelly runs.
            if evidence["native_run_id"] is None:
                assert evidence["native_fill_count"] is None
                assert evidence["pf"] is None
                assert evidence["ev"] is None
                assert evidence["max_dd"] is None


if __name__ == "__main__":
    try:
        validate(json.loads(FILE.read_text(encoding="utf-8")))
    except (AssertionError, KeyError, TypeError, ValueError) as exc:
        print(f"INVALID Math EDGE Dictionary: {exc}", file=sys.stderr)
        sys.exit(1)
    print("PASS: research dictionary structural and evidence-boundary checks")
