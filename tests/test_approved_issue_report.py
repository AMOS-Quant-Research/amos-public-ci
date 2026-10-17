"""Dual-report regression tests: source receipt is always retained."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

WORKER = Path(__file__).resolve().parents[1] / "scripts" / "approved_issue_worker.py"
with patch.dict(os.environ, {"AMOS_ISSUE_NUMBER": "25"}):
    spec = importlib.util.spec_from_file_location("approved_issue_worker", WORKER)
    worker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(worker)


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.cwd = os.getcwd()
        os.chdir(self.temp.name)
        Path("amos-loop-evidence.json").write_text(json.dumps({
            "workflow_run_url": "https://github.com/example/actions/runs/1",
            "model_request_succeeded": True,
            "changed_commit_sha": "a" * 40,
            "draft_pr_url": "https://github.com/example/pull/25",
            "test_exit_code": 0,
            "completion_state": "PARTIAL_AWAITING_CENTRAL_VERIFICATION",
        }))
        self.calls = []

    def tearDown(self):
        os.chdir(self.cwd)
        self.temp.cleanup()

    def fake_gh(self, *args, token=None, check=True):
        self.calls.append((args, token))
        if len(args) == 2:
            return "[]"
        if len(args) == 4 and args[2] == "-f":
            return json.dumps({"html_url": "https://github.com/example/issues/25#comment"})
        raise AssertionError(args)

    def test_without_token_source_only(self):
        with patch.dict(os.environ, {"AMOS_CENTRAL_REPORT_TOKEN": ""}), \
             patch.object(worker, "gh", side_effect=self.fake_gh):
            worker.central_report()
        d = json.loads(Path("amos-loop-evidence.json").read_text())
        self.assertEqual(d["public_report_status"], "POSTED")
        self.assertEqual(d["central_report_status"], "BLOCKED_MISSING_CROSS_REPO_TOKEN")
        self.assertEqual(len(self.calls), 2)
        self.assertTrue(all(token is None for _, token in self.calls))

    def test_with_token_source_and_central(self):
        with patch.dict(os.environ, {"AMOS_CENTRAL_REPORT_TOKEN": "placeholder-test-token"}), \
             patch.object(worker, "gh", side_effect=self.fake_gh):
            worker.central_report()
        d = json.loads(Path("amos-loop-evidence.json").read_text())
        self.assertEqual(d["public_report_status"], "POSTED")
        self.assertEqual(d["central_report_status"], "POSTED")
        self.assertEqual(len(self.calls), 4)
        self.assertTrue(all(token is None for _, token in self.calls[:2]))
        self.assertTrue(all(token == "placeholder-test-token" for _, token in self.calls[2:]))
        self.assertIn("POSTED_AUTOMATIC", self.calls[-1][0][-1])

if __name__ == "__main__":
    unittest.main()
