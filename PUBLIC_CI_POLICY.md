# AMOS Public CI boundary

This repository is public. Only synthetic tests and explicitly approved open-source infrastructure may be added.

Never copy private AMOS strategy implementations, market tick datasets, account details, secrets, API tokens, `.env` files, or private git history here. PR #46 risk KPI implementation remains private pending review.

This smoke workflow only tests Python execution on a standard public GitHub-hosted runner. It does not verify Nautilus, actual market data, profitability, DD limits, or live trading. CI uses read-only contents permissions, concurrency cancellation and a five-minute job timeout.
