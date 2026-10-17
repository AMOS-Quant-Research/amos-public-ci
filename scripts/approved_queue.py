#!/usr/bin/env python3
"""Approval-gated, fail-closed dispatcher for the existing public synthetic worker.

This controller does not perform AI edits. It dispatches the existing workflow,
and only chains after independently checking its completed run and receipts.
"""
import json
import os
import re
import subprocess
import sys

REPO = "AMOS-Quant-Research/amos-public-ci"
CENTRAL = "AMOS-Quant-Research/-amos-free-runner-test"
WORKFLOW = "amos-p0-approved-next.yml"
SOURCE_NAME = "AMOS P0 approved synthetic next issue"
DISPATCH_MARKER = "AMOS-QUEUE-DISPATCH:"
MAX_SCAN = 100


def gh(*args):
    proc = subprocess.run(["gh", *args], capture_output=True, text=True, check=False)
    if proc.returncode:
        raise RuntimeError("GitHub request failed: " + " ".join(args[:3]) +
                           " (rc=" + str(proc.returncode) + ")")
    return proc.stdout.strip()


def api(path, paginate=False):
    args = ["api", path]
    if paginate:
        args.append("--paginate")
    raw = gh(*args)
    if not raw:
        return []
    if paginate:
        # gh --paginate emits one JSON array per page.
        out = []
        decoder = json.JSONDecoder()
        while raw.strip():
            obj, used = decoder.raw_decode(raw.lstrip())
            out.extend(obj)
            raw = raw.lstrip()[used:]
        return out
    return json.loads(raw)


def approved(issue):
    labels = {v["name"] for v in issue.get("labels", [])}
    return (issue.get("state") == "open"
            and issue.get("number", 0) >= 17
            and issue.get("number") != 7
            and "amos-approved" in labels
            and "[P0 SYNTHETIC" in issue.get("title", "")
            and "synthetic" in (issue.get("body") or "").lower())


def issue_comments(number):
    return api("repos/" + REPO + "/issues/" + str(number) + "/comments?per_page=100",
               paginate=True)


def already_processed(number, comments, prs):
    if any("AMOS-REPORT-KEY:" in (c.get("body") or "") or
           DISPATCH_MARKER in (c.get("body") or "") for c in comments):
        return True
    prefix = "amos/issue-" + str(number) + "-run-"
    return any((p.get("headRefName") or "").startswith(prefix) for p in prs)


def find_candidate(issues, comments_by_issue, prs):
    for issue in sorted(issues, key=lambda i: i["number"]):
        if approved(issue) and not already_processed(
                issue["number"], comments_by_issue.get(issue["number"], []), prs):
            return issue["number"]
    return None


def receipt_valid(run, issues, comments_by_issue, prs, central_comments):
    """Verify distinct, successful AI work and authenticated central receipt."""
    if run.get("name") != SOURCE_NAME or run.get("conclusion") != "success":
        return False
    run_id = str(run.get("id", ""))
    if not run_id.isdecimal():
        return False
    for issue in issues:
        number = issue["number"]
        if not approved(issue):
            continue
        for comment in comments_by_issue.get(number, []):
            body = comment.get("body") or ""
            key = REPO + ":" + run_id + ":" + str(run.get("run_attempt", 1)) + ":" + str(number)
            if "AMOS-REPORT-KEY: " + key not in body:
                continue
            sha = re.search(r"(?m)^Commit: ([0-9a-f]{40})$", body)
            pr = re.search(r"(?m)^Draft PR: (https://github.com/[^\\s]+/pull/\\d+)$", body)
            if not (sha and pr and "AI model call: True" in body
                    and "Tests exit: 0" in body
                    and "Completion: PARTIAL_AWAITING_CENTRAL_VERIFICATION" in body):
                return False
            # Central receipt must be independently present. A same-repo
            # fallback or manually posted comment is NOT automatic ingestion.
            central = [c for c in central_comments
                       if "AMOS-REPORT-KEY: " + key in (c.get("body") or "")
                       and "Central ingestion: POSTED_AUTOMATIC" in (c.get("body") or "")]
            if not central:
                return False
            matching = [p for p in prs if p.get("url") == pr.group(1)
                        and p.get("isDraft") and p.get("headRefOid") == sha.group(1)]
            return bool(matching)
    return False


def main():
    event_name = os.environ.get("GITHUB_EVENT_NAME", "")
    event = json.loads(open(os.environ["GITHUB_EVENT_PATH"], encoding="utf-8").read())
    issues = api("repos/" + REPO + "/issues?state=open&labels=amos-approved&per_page=100",
                 paginate=True)
    issues = [i for i in issues if "pull_request" not in i][:MAX_SCAN]
    prs = api("repos/" + REPO + "/pulls?state=all&per_page=100", paginate=True)
    prs = [{"url": p.get("html_url"), "headRefName": p.get("head", {}).get("ref"),
            "headRefOid": p.get("head", {}).get("sha"), "isDraft": p.get("draft")}
           for p in prs]
    comments = {i["number"]: issue_comments(i["number"])
                for i in issues if approved(i)}
    if event_name == "workflow_run":
        run = event.get("workflow_run", {})
        # Chain at most one successor from a completed source run.
        # Never chain from this queue-controller workflow itself.
        central_token = os.environ.get("AMOS_CENTRAL_REPORT_TOKEN")
        if not central_token:
            print("BLOCKED_MISSING_CROSS_REPO_TOKEN: no central receipt verification")
            return 0
        central_comments = api("repos/" + CENTRAL + "/issues/42/comments?per_page=100",
                               paginate=True)
        if not receipt_valid(run, issues, comments, prs, central_comments):
            print("BLOCKED_UNVERIFIED_PREDECESSOR: not dispatching next issue")
            return 0
    elif event_name not in {"schedule", "workflow_dispatch"}:
        print("BLOCKED_UNSUPPORTED_EVENT")
        return 0
    # Prevent duplicate dispatch if a source workflow is already running.
    active = api("repos/" + REPO + "/actions/workflows/" + WORKFLOW +
                 "/runs?per_page=30")
    if any(r.get("status") in {"queued", "in_progress", "waiting", "pending"}
           for r in active.get("workflow_runs", [])):
        print("SKIP_WORKER_ALREADY_ACTIVE")
        return 0
    candidate = find_candidate(issues, comments, prs)
    if candidate is None:
        print("QUEUE_EMPTY_OR_UNAPPROVED")
        return 0
    # Dispatch via workflow_dispatch. GITHUB_TOKEN must have Actions:write.
    gh("workflow", "run", WORKFLOW, "-R", REPO, "-f", "issue_number=" + str(candidate))
    gh("api", "repos/" + REPO + "/issues/" + str(candidate) + "/comments",
       "-f", "body=" + DISPATCH_MARKER + " " + str(candidate) +
       " | controller-run=" + os.environ.get("GITHUB_RUN_ID", "unknown"))
    print("DISPATCHED_APPROVED_SYNTHETIC_ISSUE", candidate)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (RuntimeError, ValueError, KeyError) as exc:
        print("BLOCKED_QUEUE_CONTROLLER:", exc, file=sys.stderr)
        sys.exit(1)
