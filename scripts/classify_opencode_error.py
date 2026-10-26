"""Classify OpenCode errors offline without logging credentials or changing settings."""

import argparse
import json
import re
import sys

HTTP_STATUS = re.compile(
    r"\b(?:HTTP[/\d.]*\s*|→\s*|status(?:\s+code)?\s*[:=]?\s*)(401|403|404|408|429|500|502|503|504)\b"
    r"|\b(401|403|404|408|429|500|502|503|504)\s+(?:forbidden|unauthorized|not found|too many requests|gateway timeout|bad gateway|service unavailable)\b",
    re.I,
)


def classify(message: str) -> dict:
    """Return a diagnostic category, never an unverified root-cause claim."""
    if not isinstance(message, str):
        raise TypeError("message must be a string")
    match = HTTP_STATUS.search(message)
    status = next((v for v in match.groups() if v), "") if match else ""
    lower = message.lower()
    if status in {"401", "403"}:
        category = "access_denied"
        next_check = "Identify the component returning the status; compare auth and proxy logs without disabling authentication."
    elif status == "429" or "rate limit" in lower or "quota exceeded" in lower:
        category = "rate_or_quota"
        next_check = "Check quotas and retry-after; do not retry paid requests automatically."
    elif "runner" in lower and any(s in lower for s in ("not found", "offline", "queued")):
        category = "runner_unavailable"
        next_check = "Check workflow run, runner labels, repository permissions and quota."
    elif status in {"500", "502", "503", "504"}:
        category = "upstream_failure"
        next_check = "Inspect server/proxy logs and status before retrying."
    elif "model not found" in lower or (status == "404" and "model" in lower):
        category = "model_unavailable"
        next_check = "Check model ID and provider availability."
    elif "permission denied" in lower or "resource not accessible by integration" in lower:
        category = "github_permission"
        next_check = "Check app permissions and workflow token scope."
    elif any(s in lower for s in ("connection refused", "dns", "timed out", "timeout")) or status in {"408", "404"}:
        category = "connectivity_or_endpoint"
        next_check = "Check endpoint, route, port, server process and logs."
    else:
        category = "unclassified"
        next_check = "Capture redacted client and server logs; do not infer a root cause."
    return {"category": category, "http_status": status or "unknown", "root_cause_verified": False, "next_check": next_check}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--message", help="Error text, without credentials")
    args = parser.parse_args()
    message = args.message if args.message is not None else sys.stdin.read(32768)
    print(json.dumps(classify(message), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
