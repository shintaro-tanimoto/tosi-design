# PROGRESS — n分都市化支援ツール

最終更新: 2026-06-22 / 担当: Claude(Opus 4.8) 設計・指揮 ＋ codex CLI 実装

## 現在地
**M1（機能A MVP）完了。谷中（既定地区）で OSM 実データから S を算出し folium 地図を生成。** 次は M2（質レイヤ §6.7）。
WSL(Ubuntu-22.04) `/home/shin/tosi_design`。venv 構築済（geo 依存 + scikit-learn 導入、`pip install -e .` 済）。`pytest` → 10 passed。
谷中 15分walk: 起点848・S=1.0飽和（密な中心市街地のため）。5分walk: avg=0.81/良好556・要改善265・不足27 で空間勾配を確認。地図は `outputs/`（.gitignore対象）。

## マイルストーン状況
| ID | マイルストーン | 状態 |
|----|----------------|------|
| M0a | 環境セットアップ（Node+codex導入, git init, push） | ✅ 完了 |
| M0b | プロジェクトscaffold（config・空IF・README・PROGRESS） | ✅ 完了（pytest 7緑） |
| M1 | 機能A(MVP)：到達圏＋重み合成スコアS＋基本地図 | ✅ 完了（谷中で実走・pytest 10緑） |
| M2 | 質レイヤ(§6.7)：歩行環境A＋クロノトピーB＋体験指標C＋Q | ⬜ 未着手 |
| M3 | 提案(機能B)＋感度分析＋S×Q散布＋時間帯可視化 | ⬜ 未着手 |
| M4 | (任意) 機能C：Location-Allocation 最適配置 | ⬜ 未着手 |

## 直近の決定事項
- ターゲット＝標準Pythonプロトタイプ（osmnx/networkx/geopandas）。`NetworkBackend` 抽象で後から ArcGIS `.pyt` 化可能に。
- 実装は codex CLI(gpt5.5) に委譲、Claude が仕様化・レビュー・git管理。
- データ＝OSM実地区（osmnx）。対象地区名は未確定（既定：小さめの東京の地区）。
- `reference/`（モレノ著書全文）は著作権配慮で `.gitignore` 除外（公開repoに含めない）。

## 次アクション（WSL 側）
1. ✅ M0b/M1 完了（scaffold・機能A MVP・pytest 緑・谷中で実走・commit/push）
2. **M2（質レイヤ §6.7）の codex 仕様作成** → walkability(要素A: OSMタグ→区間品質→インピーダンス補正) + chronotopia a(i,c,t)(要素B: 時間帯別到達) + 体験指標(要素C) + Q(i)・S×Q 並置
3. デモ用に既定 minutes を見直す余地あり（谷中×15分は S 飽和。5分 or やや広い地区だと勾配が出る）

## 学び / 決定
- Windows ネイティブ codex は書込にサンドボックス全無効フラグが必須 → 不採用。**WSL で `-s workspace-write`（安全）を使う**。
- WSL 環境は構築済（HANDOVER_WSL.md にステータス表）。

## ブロッカー / 要ユーザー対応
- ✅ codex 認証（Windows・WSL とも ChatGPT ログイン済）
- ⚠️ GitHub push 認証（WSL は GCM/PAT 未設定）— push 時に要確認
- ⚠️ `python3.10-venv` 未導入（venv 作成不可）。M0b は user-level pytest で代替。M1 の geo 依存導入方針を要判断
- ❓ 対象OSM地区名（後で `--place` 指定可）
