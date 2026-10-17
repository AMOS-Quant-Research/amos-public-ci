#!/usr/bin/env python3
"""Public synthetic issue worker. No private code, credentials, or trading."""
import json
import os
import pathlib
import subprocess
import sys

ISSUE = 7
REPO = "AMOS-Quant-Research/amos-public-ci"
CENTRAL = "AMOS-Quant-Research/-amos-free-runner-test"
FILE = pathlib.Path("tests/test_agent_generated_constant.py")
RUN = os.environ.get("GITHUB_RUN_ID", "")
ATTEMPT = os.environ.get("GITHUB_RUN_ATTEMPT", "1")
KEY = f"{REPO}:{RUN}:{ATTEMPT}:{ISSUE}"

def gh(*args, token=None, check=True):
    env = dict(os.environ)
    if token is not None:
        env["GH_TOKEN"] = token
    p = subprocess.run(["gh", *args], text=True, capture_output=True, env=env)
    if check and p.returncode:
        raise RuntimeError(f"GitHub command failed (rc={p.returncode}): {' '.join(args[:3])}; {p.stderr[:200]}")
    return p.stdout.strip()

def record(**updates):
    p = pathlib.Path("amos-loop-evidence.json")
    d = json.loads(p.read_text()) if p.exists() else {
        "schema_version": "amos.loop.evidence.v1", "issue_url": f"https://github.com/{REPO}/issues/{ISSUE}",
        "runner_repo": REPO, "workflow_run_url": f"https://github.com/{REPO}/actions/runs/{RUN}",
        "workflow_attempt": ATTEMPT, "idempotency_key": KEY, "agent_name": "OpenCode",
        "agent_version": None, "model_provider": "NOT_VERIFIED", "model_name": None,
        "model_request_succeeded": False, "changed_commit_sha": None, "changed_paths": [],
        "test_run_url": None, "test_exit_code": None, "draft_pr_url": None,
        "central_report_comment_url": None, "completion_state": "BLOCKED"
    }
    d.update(updates)
    p.write_text(json.dumps(d, indent=2, sort_keys=True) + "\n")

def issue_gate():
    d = json.loads(gh("issue", "view", str(ISSUE), "-R", REPO, "--json", "number,state,title,body"))
    assert d["number"] == ISSUE and d["state"] == "OPEN"
    assert "[P0 SYNTHETIC" in d["title"]
    assert "tests/test_agent_generated_constant.py" in d["body"]
    record(issue_state="VERIFIED", task_id=f"public-ci-issue-{ISSUE}")

def commit_and_pr():
    assert FILE.is_file() and FILE.stat().st_size > 0, "AI generated file missing"
    subprocess.run(["python3", "-m", "unittest", "discover", "-s", "tests",
                    "-p", "test_agent_generated_constant.py", "-v"], check=True)
    record(test_exit_code=0, test_run_url=f"https://github.com/{REPO}/actions/runs/{RUN}")
    status = subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=all"], text=True)
    # Python unittest creates untracked __pycache__/*.pyc files on runners.
    # These are runtime artifacts, not AI source edits. Ignore ONLY untracked
    # cache files; never ignore tracked edits or other out-of-scope paths.
    paths = [line[3:] for line in status.splitlines()]
    allowed = {str(FILE), "agent_result.py", "agent.log", "amos-loop-evidence.json"}
    def runtime_cache(line):
        path = pathlib.PurePosixPath(line[3:])
        return (line.startswith("?? ") and "__pycache__" in path.parts
                and path.suffix in {".pyc", ".pyo"})
    violations = [line[3:] for line in status.splitlines()
                  if line[3:] not in allowed and not runtime_cache(line)]
    assert not violations, f"Out-of-scope changes: {violations}"
    branch = f"amos/issue-{ISSUE}-run-{RUN}-attempt-{ATTEMPT}"
    subprocess.run(["git", "config", "user.name", "github-actions[bot]"], check=True)
    subprocess.run(["git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com"], check=True)
    subprocess.run(["git", "checkout", "-b", branch], check=True)
    subprocess.run(["git", "add", "--", str(FILE), "agent_result.py"], check=True)
    subprocess.run(["git", "commit", "-m", f"test(ai): Issue #{ISSUE} generated acceptance test"], check=True)
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    record(changed_commit_sha=sha, changed_paths=[str(FILE), "agent_result.py"])
    subprocess.run(["git", "push", "origin", branch], check=True)
    existing = gh("pr", "list", "-R", REPO, "--head", branch, "--json", "url", "--jq", ".[0].url", check=False)
    if not existing:
        gh("pr", "create", "-R", REPO, "--draft", "--base", "main", "--head", branch,
           "--title", f"AI-generated synthetic test for Issue #{ISSUE} (run {RUN})",
           "--body", f"Closes #{ISSUE} only after human review.\\nAI model evidence: Actions run {RUN}.\\nCommit: {sha}\\nTest: python3 -m unittest discover -s tests -p test_agent_generated_constant.py -v (PASS).\\nNo auto-merge.")
    url = gh("pr", "view", branch, "-R", REPO, "--json", "url,isDraft,headRefOid", "--jq", ".url")
    details = json.loads(gh("pr", "view", branch, "-R", REPO, "--json", "url,isDraft,headRefOid"))
    assert details["isDraft"] and details["headRefOid"] == sha
    record(draft_pr_url=url, completion_state="PARTIAL_AWAITING_CENTRAL_VERIFICATION")

def central_report():
    p = pathlib.Path("amos-loop-evidence.json")
    if not p.exists():
        record()
    d = json.loads(p.read_text())
    token = os.environ.get("AMOS_CENTRAL_REPORT_TOKEN", "")
    if not token:
        record(central_report_status="BLOCKED_MISSING_CROSS_REPO_TOKEN")
        return
    prior = json.loads(gh("api", f"repos/{CENTRAL}/issues/42/comments?per_page=100", token=token))
    match = next((x for x in prior if KEY in x.get("body", "")), None)
    if match is None:
        body = (f"AMOS P0 public Issue #{ISSUE} evidence\\nIdempotency: {KEY}\\n"
                f"Run: {d['workflow_run_url']}\\nAI model call: {d['model_request_succeeded']}\\n"
                f"Commit: {d['changed_commit_sha']}\\nDraft PR: {d['draft_pr_url']}\\n"
                f"Tests exit: {d['test_exit_code']}\\nStatus: {d['completion_state']}\\n"
                f"Artifact: {d['workflow_run_url']}#artifacts")
        match = json.loads(gh("api", f"repos/{CENTRAL}/issues/42/comments", "-f", f"body={body}", token=token))
    record(central_report_comment_url=match["html_url"], central_report_status="POSTED")

if __name__ == "__main__":
    try:
        if sys.argv[1] == "issue": issue_gate()
        elif sys.argv[1] == "pr": commit_and_pr()
        elif sys.argv[1] == "report": central_report()
        else: raise ValueError("unknown subcommand")
    except Exception as e:
        record(last_error=f"{type(e).__name__}: {str(e)[:300]}", completion_state="BLOCKED")
        raise
