"""Contract tests for the public-only reporting fallback. No network access."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

WORKER = Path(__file__).resolve().parents[1] / "scripts" / "issue7_worker.py"
spec = importlib.util.spec_from_file_location("issue7_worker", WORKER)
worker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(worker)


class ReportFallbackTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.oldcwd = os.getcwd()
        os.chdir(self.tmp.name)
        Path("amos-loop-evidence.json").write_text(json.dumps({
            "workflow_run_url": "https://github.com/example/actions/runs/1",
            "model_request_succeeded": True,
            "changed_commit_sha": "abcdef",
            "draft_pr_url": "https://github.com/example/pull/15",
            "test_exit_code": 0,
            "completion_state": "READY_FOR_REVIEW",
        }))
        self.calls = []
        self.comment = {"html_url": "https://github.com/example/issues/7#issuecomment-1"}

    def tearDown(self):
        os.chdir(self.oldcwd)
        self.tmp.cleanup()

    def fake_gh(self, *args, token=None, check=True):
        self.calls.append((args, token))
        if args[0] != "api":
            raise AssertionError("Unexpected command")
        if len(args) == 2:
            return json.dumps(getattr(self, "prior", []))
        if len(args) == 4 and args[2] == "-f":
            self.assertIn("AMOS-REPORT-KEY:", args[3])
            return json.dumps(self.comment)
        raise AssertionError(args)

    def test_missing_token_posts_public_receipt_but_not_central(self):
        with patch.dict(os.environ, {"AMOS_CENTRAL_REPORT_TOKEN": ""}), \
             patch.object(worker, "gh", side_effect=self.fake_gh):
            worker.central_report()
        result = json.loads(Path("amos-loop-evidence.json").read_text())
        self.assertEqual(result["public_report_status"], "POSTED")
        self.assertEqual(result["central_report_status"], "BLOCKED_MISSING_CROSS_REPO_TOKEN")
        self.assertNotIn("central_report_comment_url", result)
        self.assertIn("/amos-public-ci/issues/7/comments", self.calls[-1][0][1])

    def test_existing_receipt_is_not_duplicated(self):
        self.prior = [{"body": "AMOS-REPORT-KEY: " + worker.KEY,
                       "html_url": "https://github.com/example/issues/7#existing"}]
        with patch.dict(os.environ, {"AMOS_CENTRAL_REPORT_TOKEN": ""}), \
             patch.object(worker, "gh", side_effect=self.fake_gh):
            worker.central_report()
        self.assertEqual(len(self.calls), 1)

    def test_central_token_posts_to_existing_pr42(self):
        with patch.dict(os.environ, {"AMOS_CENTRAL_REPORT_TOKEN": "placeholder-test-token"}), \
             patch.object(worker, "gh", side_effect=self.fake_gh):
            worker.central_report()
        result = json.loads(Path("amos-loop-evidence.json").read_text())
        self.assertEqual(result["central_report_status"], "POSTED")
        self.assertNotIn("public_report_status", result)
        self.assertIn("/-amos-free-runner-test/issues/42/comments", self.calls[-1][0][1])
        self.assertEqual(self.calls[-1][1], "placeholder-test-token")


if __name__ == "__main__":
    unittest.main()
