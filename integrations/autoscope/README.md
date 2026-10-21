# AMOS ↔ AutoScope 1.01 integration (experimental)

This folder provides a **portable trade-data interchange adapter**, not the proprietary AutoScope application. It preserves the existing Nautilus engine and AMOS CI.

## Current scope
- Normalizes completed trades to a stable JSON/CSV schema.
- Validates side, quantity and required columns.
- Runs on Ubuntu with Python standard library only.
- No Windows binaries, bundled Python runtime, or source distribution included.

## Next connection gates
1. Confirm AutoScope redistribution rights and native import schema.
2. Implement actual AutoScope import/export bridge and fixture parity tests.
3. Validate AutoScope on Windows runner and compare statistics with Nautilus.
4. Confirm real Raw Tick, WFO, and Monte Carlo separately.

**Passing this adapter CI does not prove AutoScope itself runs or that Nautilus integration is complete.**
