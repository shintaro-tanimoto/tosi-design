# PROGRESS — n分都市化支援ツール

最終更新: 2026-06-22 / 担当: Claude(Opus 4.8) 設計・指揮 ＋ codex CLI 実装

## 現在地
**M0 環境セットアップほぼ完了。** Node v24.17.0 / npm 11.13.0 / codex-cli 0.141.0 導入済。git init・初回コミット・GitHub への push 完了。**残るは codex のログイン（ユーザー認証）のみ。**

## マイルストーン状況
| ID | マイルストーン | 状態 |
|----|----------------|------|
| M0a | 環境セットアップ（Node+codex導入, git init, push） | 🟡 ほぼ完了（codex login 待ち） |
| M0b | プロジェクトscaffold（config・空IF・README・PROGRESS） | ⬜ 未着手 |
| M1 | 機能A(MVP)：到達圏＋重み合成スコアS＋基本地図 | ⬜ 未着手 |
| M2 | 質レイヤ(§6.7)：歩行環境A＋クロノトピーB＋体験指標C＋Q | ⬜ 未着手 |
| M3 | 提案(機能B)＋感度分析＋S×Q散布＋時間帯可視化 | ⬜ 未着手 |
| M4 | (任意) 機能C：Location-Allocation 最適配置 | ⬜ 未着手 |

## 直近の決定事項
- ターゲット＝標準Pythonプロトタイプ（osmnx/networkx/geopandas）。`NetworkBackend` 抽象で後から ArcGIS `.pyt` 化可能に。
- 実装は codex CLI(gpt5.5) に委譲、Claude が仕様化・レビュー・git管理。
- データ＝OSM実地区（osmnx）。対象地区名は未確定（既定：小さめの東京の地区）。
- `reference/`（モレノ著書全文）は著作権配慮で `.gitignore` 除外（公開repoに含めない）。

## 次アクション
1. ✅ Node/codex 導入、git init、初回 push 完了
2. **ユーザー**：`codex login`（認証）← 次はここ
3. ログイン後、M0b scaffold を codex exec で生成させる

## ブロッカー / 要ユーザー対応
- 🔴 **`codex login`（OpenAI/ChatGPT 認証）待ち** — これが済むと codex 実装を開始できる
- ✅ 初回 push の Git Credential Manager 認証は完了（キャッシュ済）
- ❓ 対象OSM地区名（後で `--place` 指定可）
