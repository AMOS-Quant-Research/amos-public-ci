"""Contract tests for fail-closed approved public synthetic queue."""
import importlib.util
import pathlib
import unittest

spec = importlib.util.spec_from_file_location(
    "approved_queue", pathlib.Path(__file__).resolve().parents[1] /
    "scripts" / "approved_queue.py")
queue = importlib.util.module_from_spec(spec)
spec.loader.exec_module(queue)


def issue(n, label=True, title=True):
    return {"number": n, "state": "open",
            "labels": [{"name": "amos-approved"}] if label else [],
            "title": "[P0 SYNTHETIC NEXT] Safe task" if title else "amos-approved",
            "body": "Public synthetic unittest only"}


class ApprovedQueueTests(unittest.TestCase):
    def test_empty_queue(self):
        self.assertIsNone(queue.find_candidate([], {}, []))

    def test_unapproved_issue_rejected(self):
        self.assertIsNone(queue.find_candidate([issue(25, label=False)], {}, []))

    def test_title_contract_required(self):
        self.assertIsNone(queue.find_candidate([issue(25, title=False)], {}, []))

    def test_issue_seven_rejected(self):
        self.assertIsNone(queue.find_candidate([issue(7)], {}, []))

    def test_prior_receipt_rejected(self):
        self.assertIsNone(queue.find_candidate(
            [issue(25)], {25: [{"body": "AMOS-REPORT-KEY: done"}]}, []))

    def test_prior_dispatch_rejected(self):
        self.assertIsNone(queue.find_candidate(
            [issue(25)], {25: [{"body": "AMOS-QUEUE-DISPATCH: 25"}]}, []))

    def test_existing_draft_pr_rejected(self):
        self.assertIsNone(queue.find_candidate(
            [issue(25)], {}, [{"headRefName": "amos/issue-25-run-123-attempt-1"}]))

    def test_selects_next_distinct_approved(self):
        issues = [issue(26), issue(25)]
        self.assertEqual(queue.find_candidate(issues, {25: [
            {"body": "AMOS-QUEUE-DISPATCH: 25"}]}, []), 26)

    def test_no_chain_on_unverified_run(self):
        self.assertFalse(queue.receipt_valid(
            {"name": queue.SOURCE_NAME, "conclusion": "failure", "id": 100},
            [issue(25)], {}, [], []))

    def test_no_chain_on_fallback_only(self):
        sha = "a" * 40
        key = queue.REPO + ":100:1:25"
        receipt = {"body": (
            "AMOS-REPORT-KEY: " + key + "\nAI model call: True\nCommit: " + sha +
            "\nDraft PR: https://github.com/AMOS-Quant-Research/amos-public-ci/pull/99" +
            "\nTests exit: 0\nCompletion: PARTIAL_AWAITING_CENTRAL_VERIFICATION")}
        run = {"name": queue.SOURCE_NAME, "conclusion": "success", "id": 100,
               "run_attempt": 1}
        prs = [{"url": "https://github.com/AMOS-Quant-Research/amos-public-ci/pull/99",
                "isDraft": True, "headRefOid": sha}]
        self.assertFalse(queue.receipt_valid(run, [issue(25)], {25: [receipt]}, prs, []))

    def test_two_distinct_issue_sequence(self):
        self.assertEqual(queue.find_candidate([issue(25), issue(26)], {}, []), 25)
        self.assertEqual(queue.find_candidate(
            [issue(25), issue(26)], {25: [{"body": "AMOS-QUEUE-DISPATCH: 25"}]},
            []), 26)


if __name__ == "__main__":
    unittest.main()
