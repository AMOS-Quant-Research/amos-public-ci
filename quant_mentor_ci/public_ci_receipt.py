"""Create a public-only CI receipt from actual unittest exit status.

Receipt proves only that public synthetic tests ran, not private strategy parity.
"""
import argparse
import hashlib
import json
from pathlib import Path


def make_receipt(log_path, *, commit, run_id, exit_code):
    log = Path(log_path).read_bytes()
    if len(commit) != 40 or any(c not in "0123456789abcdef" for c in commit.lower()):
        raise ValueError("Expected full Git commit SHA")
    if not run_id or exit_code != 0:
        raise ValueError("Only successful completed test runs may issue receipts")
    text = log.decode("utf-8", errors="replace")
    if "OK" not in text or "Ran " not in text:
        raise ValueError("Passing unittest summary missing")
    return {"schema_version": "1.0", "scope": "PUBLIC_SYNTHETIC_ONLY",
            "source_commit": commit, "github_run_id": str(run_id),
            "test_log_sha256": hashlib.sha256(log).hexdigest(),
            "status": "PUBLIC_TESTS_PASSED",
            "private_source_tested": False,
            "nautilus_raw_tick_verified": False,
            "execution_allowed": False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--exit-code", type=int, required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    receipt = make_receipt(args.log, commit=args.commit, run_id=args.run_id,
                           exit_code=args.exit_code)
    Path(args.out).write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n",
                              encoding="utf-8")


if __name__ == "__main__":
    main()
