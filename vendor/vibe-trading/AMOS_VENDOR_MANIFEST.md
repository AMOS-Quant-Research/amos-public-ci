# Vibe-Trading source-only vendor (AMOS research)

- Source: user-authorized Google Drive package `XAUUSD_Vibe_Trading_Complete_Package.zip` (file ID `1HY3-1htL8rdWaHC_xSiZjPg6Ap6AEknQ`).
- Archive SHA-256: `56bf3bcfc3221b6cccd9cd64c03425952ebc98baf510e39058b65372772bdf38`.
- Source license: MIT, retained at `vendor/vibe-trading/LICENSE`.
- Verified vendor GitHub Actions run: `40674848012`, completed successfully on 2026-10-28.
- Persisted source files: **2,934**; root includes agent, frontend, desktop, schema code.
- Deliberately excluded: binary assets, font files, Tick data, fixture data, credentials and env files, oversized files. This is **not a complete deployable binary distribution**.
- Original native driver: `agent/backtest/engines/nautilus_vibe_driver.py`.
- Research-only original-paper Kelly sizing patch: `research/vibe_xauusd/patch_native_fractional_sizing.py`; do not modify original driver for research patches.
- Real quote source remains separately SHA-pinned; source repository contains **no user broker keys**.
- The source tree is persisted on Draft PR #46's research branch; no default-branch merge has occurred.
- Never enable broker execution from this research vendor.
