# amos-public-ci

## Public-safe CI for AMOS

This **public repository** is an additional CI execution lane for generic, synthetic-only tests. It is **not** a mirror of AMOS private source code. Do not copy private trading strategies, model weights, account records, raw market ticks, GitHub secrets, API keys, broker credentials, proprietary prompts or private repository artifacts into it.

- `.github/workflows/amos-public-contract.yml`: isolated short offline stdlib tests; no provider APIs or secrets.
- `ci_contract.py`: whitelisted, synthetic-only evidence format; rejects additional fields, nonzero orders, real-data claims and missing hashes.
- `tests/test_ci_contract.py`: verifies fail-closed contract.
- Output artifact `amos-public-safe-contract` contains only a synthetic fixture and metadata; never treat it as real Nautilus/OOS/WFO/Monte Carlo evidence.

Existing private [AMOS coreAI PR #23](https://github.com/AMOS-Quant-Research/-amos-free-runner-test/pull/23) stays private. Private Actions usage limits cannot be bypassed by publishing sensitive code. Run public-safe tests here and resume private-only CI when its allowed quota or approved runner capacity is available.

**Important:** GitHub-hosted public repository Actions may be free subject to GitHub policies; this does not create extra NVIDIA/Claude/ChatGPT tokens, and does not validate private code automatically.
