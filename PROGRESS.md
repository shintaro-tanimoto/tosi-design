# PROGRESS — n分都市化支援ツール

最終更新: 2026-06-22 / 担当: Claude(Opus 4.8) 設計・指揮 ＋ codex CLI 実装

## 現在地
**WSL へ移行（理由：Windows ネイティブでは codex がサンドボックス制約で書込不可）。** 詳細は `HANDOVER_WSL.md`。
Windows 側で環境構築・git init・GitHub push 済。WSL(Ubuntu-22.04) は git/python3/node v20/codex 導入済・**ChatGPT ログイン済**で実装準備完了。次は WSL に clone して M0b scaffold を codex 実行。

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

## 次アクション（WSL 側）
1. `cd ~ && git clone https://github.com/shintaro-tanimoto/tosi-design.git`
2. push 用 credential.helper 設定（Windows GCM 流用 or PAT）— `HANDOVER_WSL.md` 参照
3. `codex exec -C ~/tosi-design -s workspace-write - < /tmp/m0b_prompt.md` で scaffold 生成
4. diff レビュー → `pytest` → commit/push → M1 へ

## 学び / 決定
- Windows ネイティブ codex は書込にサンドボックス全無効フラグが必須 → 不採用。**WSL で `-s workspace-write`（安全）を使う**。
- WSL 環境は構築済（HANDOVER_WSL.md にステータス表）。

## ブロッカー / 要ユーザー対応
- ✅ codex 認証（Windows・WSL とも ChatGPT ログイン済）
- ✅ GitHub push 認証（Windows GCM 済。WSL は GCM 流用 or PAT を設定予定）
- ❓ 対象OSM地区名（後で `--place` 指定可）
