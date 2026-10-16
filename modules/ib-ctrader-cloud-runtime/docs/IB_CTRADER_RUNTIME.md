# AMOS IB Runtime Blueprint

## Purpose

This is a subscription runtime layer for a formally approved introducing-broker or partner operation. It is separate from the AMOS research factory and does not change the operator's internal GitHub workflow.

## Customer journey

1. The customer opens and owns their broker and cTrader accounts.
2. The customer installs the protected AMOS cBot and chooses an account, symbol, and risk preset.
3. The customer starts the cTrader Cloud instance. The instance, not a VPS, is the persistent runtime.
4. AMOS Console displays entitlement, installed version, runtime health, and support notices.
5. The customer can stop the instance and revoke AMOS access at any time.

## Operator boundaries

AMOS may publish a versioned cBot, display generic operating information, and provide technical support. It must not hold customer credentials, accept deposits, operate withdrawals, promise returns, or take discretionary control of a customer account.

## Revenue separation

| Channel | What is charged for | Owner |
| --- | --- | --- |
| Broker partner agreement | Approved referral / partner remuneration | Broker → operator |
| AMOS subscription | Software access, cBot delivery, health view, version updates, support | Customer → operator |

Subscription records must not be represented as payment for personalised trade recommendations. Launch jurisdiction, broker contract, marketing copy, and customer agreement require professional compliance review.

## Required AMOS Console states

- `NOT_CONNECTED`: no customer-owned account or runtime has been linked.
- `READY_TO_START`: cBot installed; customer must start the Cloud instance.
- `RUNNING`: runtime reports an active state.
- `STOPPED_BY_OWNER`: customer stopped the instance.
- `BROKER_UNAVAILABLE`: cTrader Cloud is unavailable for the selected broker/account.
- `SUPPORT_REQUIRED`: AMOS detects a stale version or non-trading technical error.

## Non-goals

- No hidden account sharing or free-tier circumvention.
- No trade-copying, managed-account operation, or custody.
- No claim that cTrader Cloud is a general-purpose VPS.
