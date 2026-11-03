# AMOS research

| Module | Responsibility | Does not hold |
| --- | --- | --- |
| [potential/](potential/) | Preflight research readiness immediately after natural-language intake; output `by_source` and `by_confluence` | Optimization, performance scoring, simultaneous execution interaction claims, live orders |
| [ai_trader/](ai_trader/) | Research candidate generation and native simulation adapters | Live order permission |
| [kronos_fractal/](kronos_fractal/) | Raw Tick → 5s/15s/M1 internal-state learning → M5/M15 forecast baseline | Orders, PnL claims, CoreAI/Risk Governor changes |

**Boundary:** NautilusTrader is the only performance scorer. Potential decides whether research is worth undertaking, not whether a strategy is profitable.
