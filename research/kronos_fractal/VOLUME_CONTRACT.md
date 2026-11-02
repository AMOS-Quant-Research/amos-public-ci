# Asset-Class Volume Contract

Kronos remains an independent OHLCV forecaster. The Fractal learner may consume the same canonical volume fields, but never changes their meaning.

## Canonical fields

| Field | Equities / exchange-traded instruments | FX / CFD quote feeds |
| --- | --- | --- |
| `volume` | Mandatory venue-reported executed trade volume for the bar. Preserve its native unit and venue. | `null` unless an authoritative executed-volume feed is supplied. |
| `quote_tick_count` | Optional quote/update activity count; never replaces `volume`. | Count of validated Bid/Ask quote updates in the bar; activity proxy only. |
| `real_volume_available` | `true` when the reported venue volume is present and complete. | Normally `false`. |
| `volume_semantics` | `exchange_executed` | `quote_activity_proxy` or `unavailable` |

## Equity features

When `volume_semantics=exchange_executed`, both Kronos and the independent Fractal learner receive the same completed-bar OHLCV series. The Fractal feature contract additionally derives only causal values:

- relative volume against completed prior bars;
- volume acceleration and abnormal-volume score;
- range / volume and return / volume price-impact measures;
- volume confirmation or non-confirmation of breakouts, continuations and reversals;
- session-normalized dollar volume when currency and share units are known.

VWAP, volume profile, CVD, delta and aggressor imbalance require their respective trade-level inputs. They are not inferred from OHLCV alone.

## Safety

Volume is never silently substituted across asset classes. Missing volume remains missing. Prediction validation remains separate from trading evaluation; any execution claim requires the existing instrument-specific Raw Tick / trade data route.
