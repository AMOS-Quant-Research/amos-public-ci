"""Fail-closed independent verification of AMOS synthetic AI development loop.

Run with GH_TOKEN and a completed evidence JSON. Never treats worker assertions
as proof; fetches actual GitHub run, PR, commit and central comment metadata.
"""
import json
import os
import sys
import urllib.error
import urllib.request
from urllib.parse import urlparse

CENTRAL_REPO = "AMOS-Quant-Research/-amos-free-runner-test"
CENTRAL_PR = 42


def check_claim(evidence, run, pr, commit, comments):
    """Return (verified, reasons). All inputs are independently fetched records."""
    errors = []
    required = ("issue_url", "runner_repo", "workflow_run_id", "workflow_attempt",
                "model_request_succeeded", "ai_generated_commit_sha",
                "draft_pr_url", "central_report_comment_url", "test_exit_code",
                "changed_paths", "model_name", "artifact_url")
    for field in required:
        if field not in evidence or evidence[field] in (None, "", []):
            errors.append("missing:" + field)
    if errors:
        return False, errors
    if not evidence["issue_url"].startswith("https://github.com/" + evidence["runner_repo"] + "/issues/"):
        errors.append("issue_repo_mismatch")
    if run.get("id") != int(evidence["workflow_run_id"]) or run.get("conclusion") != "success":
        errors.append("run_not_success")
    if str(run.get("run_attempt")) != str(evidence["workflow_attempt"]):
        errors.append("attempt_mismatch")
    if not evidence["model_request_succeeded"] or not evidence.get("model_response_evidence"):
        errors.append("model_not_proven")
    if evidence["test_exit_code"] != 0:
        errors.append("tests_failed")
    if pr.get("draft") is not True or pr.get("html_url") != evidence["draft_pr_url"]:
        errors.append("not_matching_draft_pr")
    sha = evidence["ai_generated_commit_sha"]
    if commit.get("sha") != sha:
        errors.append("commit_missing")
    # Verify PR head is the exact AI-generated commit; ancestor-only is not
    # accepted without an independent compare/history API check.
    if pr.get("head", {}).get("sha") != sha:
        errors.append("pr_head_commit_mismatch")
    if not evidence["changed_paths"] or any(
        path != "agent_result.py" for path in evidence["changed_paths"]
    ):
        errors.append("path_not_allowlisted")
    central_url = evidence["central_report_comment_url"]
    if not any(c.get("html_url") == central_url and
               str(evidence["workflow_run_id"]) in c.get("body", "") and
               sha in c.get("body", "") for c in comments):
        errors.append("central_report_missing")
    if not evidence["artifact_url"].startswith(
        "https://github.com/" + evidence["runner_repo"] + "/actions/runs/" +
        str(evidence["workflow_run_id"]) + "/artifacts/"
    ):
        errors.append("artifact_mismatch")
    return not errors, errors


def github_get(path, token):
    request = urllib.request.Request(
        "https://api.github.com/" + path.lstrip("/"),
        headers={"Authorization": "Bearer " + token,
                 "Accept": "application/vnd.github+json",
                 "X-GitHub-Api-Version": "2022-11-28"},
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.load(response)


def verify_online(evidence, token):
    repo = evidence["runner_repo"]
    run_id = evidence["workflow_run_id"]
    pr_number = int(evidence["draft_pr_url"].rstrip("/").split("/")[-1])
    run = github_get(f"repos/{repo}/actions/runs/{run_id}", token)
    pr = github_get(f"repos/{repo}/pulls/{pr_number}", token)
    commit = github_get(f"repos/{repo}/commits/{evidence['ai_generated_commit_sha']}", token)
    comments = github_get(f"repos/{CENTRAL_REPO}/issues/{CENTRAL_PR}/comments?per_page=100", token)
    return check_claim(evidence, run, pr, commit, comments)


if __name__ == "__main__":
    with open(sys.argv[1], encoding="utf-8") as handle:
        evidence = json.load(handle)
    token = os.environ.get("GH_TOKEN")
    if not token:
        print("BLOCKED:GH_TOKEN_MISSING")
        sys.exit(2)
    try:
        ok, errors = verify_online(evidence, token)
    except (urllib.error.URLError, ValueError, KeyError) as exc:
        print("BLOCKED:INDEPENDENT_GITHUB_LOOKUP:" + type(exc).__name__)
        sys.exit(2)
    print("LOOP_VERIFIED" if ok else "BLOCKED:" + ",".join(errors))
    sys.exit(0 if ok else 1)
