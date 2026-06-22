# PROGRESS — n分都市化支援ツール

最終更新: 2026-06-22 / 担当: Claude(Opus 4.8) 設計・指揮 ＋ codex CLI 実装

## 現在地
**M0（環境セットアップ）に着手。** Node.js / codex CLI を導入中。

## マイルストーン状況
| ID | マイルストーン | 状態 |
|----|----------------|------|
| M0a | 環境セットアップ（Node+codex導入, git init, push） | 🔄 進行中 |
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
1. `winget install OpenJS.NodeJS.LTS` → `npm install -g @openai/codex`
2. **ユーザー**：`codex login`（認証）
3. `git init` ＋ `.gitignore` ＋ remote 設定 ＋ 初回 push
4. M0b scaffold を codex に生成させる

## ブロッカー / 要ユーザー対応
- ⏳ `codex login`（OpenAI/ChatGPT 認証）はユーザー実施が必要
- ⏳ 初回 push 時、Git Credential Manager のブラウザ認証をユーザーが完了する必要あり
- ❓ 対象OSM地区名（後で `--place` 指定可）
