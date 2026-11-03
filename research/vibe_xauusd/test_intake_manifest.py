"""Offline manifest contract tests; no model calls, network or trading."""
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parent

class IntakeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((ROOT / "intake_manifest.json").read_text(encoding="utf-8"))

    def test_sha256(self):
        self.assertRegex(self.data["source"]["sha256"], r"^[0-9a-f]{64}$")

    def test_archive_identity(self):
        self.assertEqual(self.data["source"]["name"], "XAUUSD_Vibe_Trading_Complete_Package.zip")
        self.assertEqual(self.data["source"]["size_bytes"], 31191962)

    def test_research_only(self):
        self.assertTrue(self.data["research_only"])
        self.assertFalse(self.data["live_trading"])
        self.assertFalse(self.data["continuous_loop_verified"])
        self.assertFalse(self.data["backtest_verified"])

    def test_missing_evidence_must_not_pass(self):
        self.assertEqual(len(self.data["claimed_but_absent_evidence"]), 3)
        self.assertEqual(self.data["next_gate"], "SOURCE_PROVENANCE_AND_NATIVE_FILL_EVIDENCE")

    def test_repo_not_falsely_marked_created(self):
        self.assertFalse(self.data["code_repository"]["created"])

if __name__ == "__main__":
    unittest.main()
