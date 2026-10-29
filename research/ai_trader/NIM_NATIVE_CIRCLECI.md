# AMOS NVIDIA -> Nautilus native XAUUSD research pipeline

## Existing assets reused
- Original Vibe/Nautilus native driver from earlier verified research branch, with bid/ask M1 features added and fill count corrected.
- Previously verified public Drive research archive: ID `1HY3-1htL8rdWaHC_xSiZjPg6Ap6AEknQ`, SHA256 `56bf3bcfc3221b6cccd9cd64c03425952ebc98baf510e39058b65372772bdf38`.
- Existing NVIDIA NIM chat API candidate adapter with strict parameter allowlist.
- No GitHub Actions runner is used by the CircleCI pipeline.

## Invocation
```bash
python -m pip install 'nautilus_trader==1.230.0' pandas numpy pyarrow gdown
python -m gdown 'https://drive.google.com/uc?id=1HY3-1htL8rdWaHC_xSiZjPg6Ap6AEknQ' -O /tmp/amos-original.zip
python -m research.ai_trader.archive_catalog --archive /tmp/amos-original.zip --target /tmp/amos-catalog --manifest /tmp/amos-catalog.json
export NVIDIA_NIM_API_KEY='<set securely in runtime, not source>'
python -m research.ai_trader.native_run --catalog /tmp/amos-catalog/xauusd-data/.work/vibe-math-xauusd-20260727 --output /tmp/amos-native --nim
```

The CircleCI configuration runs these stages when this GitHub repo is connected as a CircleCI project with the NIM secret present. **GitHub commits alone do not establish CircleCI project linkage or credentials.**

## Hard limits / safety
- Strategy signals calculated from historical closed M1 bars; actual execution simulated on next real Bid/Ask QuoteTick in Nautilus BacktestEngine.
- This is a **target position direction** strategy. Suggested Entry/SL/TP from the UI engine are **not submitted as native protective orders** by this adapter. Do not claim the native BT validated the original SL/TP strategy.
- Cost model defaults are uncalibrated; no validated OOS/WFO/MC, MAE/MFE or production readiness.
- `native_research_result.json` is written only after the driver exits successfully, proves actual native QuoteTick input and at least one native fill report row. No dummy evidence accepted.
- No broker order submission, CoreAI receiver ACK or live trading. Risk Governor remains a separate non-bypassed boundary.
- `NVIDIA_NIM_API_KEY` is not available to this chat runtime. An actual NIM completion requires a runner that has the secret; CircleCI connectivity must be checked independently.
- Until an actual CircleCI run provides model response, quote catalog, native fills, and saved artifacts, the end-to-end result is **UNVERIFIED**, regardless of code completion.
