"""Public-safe P0 execution probe. No secrets, model calls, or private data."""
import json
import os
from pathlib import Path


def main():
    evidence = {
        "schema_version": "amos.public_loop_probe.v1",
        "task_id": "P0-PUBLIC-PROBE-20261017",
        "issue_url": "https://github.com/AMOS-Quant-Research/-amos-free-runner-test/issues/61",
        "repo": os.getenv("GITHUB_REPOSITORY"),
        "run_id": os.getenv("GITHUB_RUN_ID"),
        "commit_sha": os.getenv("GITHUB_SHA"),
        "runner_started": bool(os.getenv("GITHUB_RUN_ID")),
        "model_request": "NOT_RUN",
        "ai_generated_commit": "NOT_RUN",
        "draft_pr_generated_by_agent": "NOT_RUN",
        "central_auto_ingestion": "NOT_RUN",
        "loop_status": "PARTIAL",
    }
    assert evidence["model_request"] != "VERIFIED"
    Path("amos-loop-evidence.json").write_text(json.dumps(evidence, indent=2) + "\n")
    print("PUBLIC_PROBE_RUN_ID=" + str(evidence["run_id"]))
    print("LOOP_STATUS=PARTIAL")


if __name__ == "__main__":
    main()
