# AMOS Free Cloud Mesh

顧客名義の無料クラウド群を、GitHubを司令塔として構成・検証・監視するための AMOS 拡張モジュールです。顧客に見せるのはクラウド事業者名ではなく、`AMOS Mesh` の能力（通知、検証、AI分析、実行リレー）です。

> このリポジトリは運用基盤です。投資判断、銘柄推奨、売買シグナル、資金移動、利益保証は行いません。

## 何をするか

1. 顧客ごとの `tenant.json` から構成計画を生成する。
2. GitHub Actions / Cloudflare / NVIDIA NIM / 無料VM / 無料GPU / cTrader Cloud をアダプターとして統一的に扱う。
3. AMOSの機能要求を `MeshResolver` が適切なバックエンドへルーティングする。
4. 各サービスの認証情報は顧客側 Secret Manager または GitHub/Cloudflare の Secret に残す。
5. AMOS は構成、稼働状態、更新、停止ポリシーだけを管理する。

## IB運営向けのVPS不要ランタイム

`ctrader_cloud` は、顧客名義のcTrader Cloud cBotを **VPS不要の常駐先** として扱います。
AMOS は暗号化済みcBotの版管理・運用状態・利用権だけを管理し、顧客は自分の口座で開始・停止・入出金を行います。

- AMOS は顧客のcTraderパスワード、取引PIN、出金権限を保持しません。
- IB報酬は、提携ブローカーの正式なパートナープログラムに限定します。
- 本モジュールは、特定業者への勧誘、個別売買助言、利益保証、資金預かりを自動化しません。
- cTrader Cloudの利用可否とインスタンス上限は、顧客のブローカー条件に従います。

そのため、顧客画面は「AMOS運用環境」のみで完結し、GitHubやVPSを日常的に操作する必要がありません。

## 最初の実行

```bash
python -m amos_mesh plan examples/tenant-demo.json
python -m amos_mesh route examples/tenant-demo.json --capability notification
python -m unittest discover -s tests -v
```

## 重要な境界

- 顧客がアカウント、請求、本人確認、ブローカー口座を所有する。
- AMOS は委任された最小権限だけを使う。
- 本モジュールは無料枠の回避・アカウント共有を目的としない。
- 実行先の空き容量、無料枠、サービス規約、可用性は各提供者に依存する。

## ディレクトリ

- `src/amos_mesh`: Mesh Compiler とプロバイダー抽象化
- `src/amos_mesh/compatibility.py`: 「能力 → バックエンド」互換層
- `examples`: 顧客別構成の例
- `.github/workflows`: 構成検証と計画生成
- `docs`: 導入・権限・運用設計
