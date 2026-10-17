"""Negative and positive contract tests for independent loop verification."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location(
    "amos_loop_verifier",
    Path(__file__).resolve().parents[1] / "tools" / "amos_loop_verifier.py",
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def fixture():
    sha = "a" * 40
    url = "https://github.com/AMOS-Quant-Research/amos-public-ci"
    e = {
        "issue_url": url + "/issues/6",
        "runner_repo": "AMOS-Quant-Research/amos-public-ci",
        "workflow_run_id": 123,
        "workflow_attempt": 1,
        "model_request_succeeded": True,
        "model_response_evidence": "redacted-model-response-id",
        "model_name": "synthetic-model",
        "ai_generated_commit_sha": sha,
        "draft_pr_url": url + "/pull/9",
        "central_report_comment_url": "https://github.com/AMOS-Quant-Research/-amos-free-runner-test/pull/42#issuecomment-123",
        "test_exit_code": 0,
        "changed_paths": ["agent_result.py"],
        "artifact_url": url + "/actions/runs/123/artifacts/456",
    }
    run = {"id": 123, "conclusion": "success", "run_attempt": 1}
    pr = {"draft": True, "html_url": e["draft_pr_url"], "head": {"sha": sha}}
    commit = {"sha": sha}
    comments = [{"html_url": e["central_report_comment_url"], "body": "123 " + sha}]
    return e, run, pr, commit, comments


class FailClosedVerifierTests(unittest.TestCase):
    def assert_blocked(self, mutation):
        records = list(fixture())
        mutation(records)
        ok, errors = module.check_claim(*records)
        self.assertFalse(ok)
        self.assertTrue(errors)

    def test_valid_contract(self):
        ok, errors = module.check_claim(*fixture())
        self.assertTrue(ok, errors)

    def test_fake_run_id(self):
        self.assert_blocked(lambda x: x[0].update(workflow_run_id=999))

    def test_missing_model_response(self):
        self.assert_blocked(lambda x: x[0].update(model_response_evidence=""))

    def test_non_ai_patch_unproven(self):
        self.assert_blocked(lambda x: x[0].update(model_request_succeeded=False))

    def test_unrelated_commit(self):
        self.assert_blocked(lambda x: x[0].update(ai_generated_commit_sha="b" * 40))

    def test_non_draft_pr(self):
        self.assert_blocked(lambda x: x[2].update(draft=False))

    def test_missing_central_report(self):
        self.assert_blocked(lambda x: x[4].clear())

    def test_failed_tests(self):
        self.assert_blocked(lambda x: x[0].update(test_exit_code=1))

    def test_wrong_artifact(self):
        self.assert_blocked(lambda x: x[0].update(artifact_url="https://invalid/1"))

    def test_unapproved_path(self):
        self.assert_blocked(lambda x: x[0].update(changed_paths=[".github/workflows/live.yml"]))

    def test_duplicate_report_key_not_equivalent(self):
        self.assert_blocked(lambda x: x[0].update(workflow_attempt=2))

    def test_missing_credential_evidence(self):
        self.assert_blocked(lambda x: x[0].pop("model_response_evidence"))


if __name__ == "__main__":
    unittest.main()
