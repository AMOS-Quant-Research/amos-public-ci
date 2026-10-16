# Architecture

`MeshCompiler` と `MeshResolver` が共通抽象化レイヤーです。OptiScalerの「入力 → 互換層 → 出力」という**構成パターンだけ**を、無料クラウドのアダプターへクリーン実装で置き換えます。OptiScalerのコード、DLL、ゲームへの注入処理は一切含めません。

```text
AMOS request (notification / validation / AI / relay)
       -> MeshResolver (capability contract + compatibility matrix)
       -> customer-owned provider adapter
       -> Cloudflare / GitHub Actions / NIM / VM agent / batch GPU

GitHub Actions remains the control plane for versioning, validation, and approved deployment plans.
```

The compiler creates a plan only. A later `apply` command must require an explicit owner approval token and provider-specific least-privilege credentials. This separation prevents an accidental deployment or an unapproved execution change.

## Non-negotiable controls

- Do not store customer root passwords, identity documents, or payment details.
- Do not rely on a free GPU service for continuous execution.
- Treat VM loss as a safe-stop event, not a reason to continue blind.
- Keep execution policy separate from research and strategy logic.
- Require a customer-controlled emergency revoke path.
- A branded AMOS control surface may abstract providers, but must not conceal provider terms, charges, or owner revocation controls.
