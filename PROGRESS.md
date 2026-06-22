# PROGRESS — n分都市化支援ツール

最終更新: 2026-06-22 / 担当: Claude(Opus 4.8) 設計・指揮 ＋ codex CLI 実装

## 現在地
**WSL へ移行完了。M0b scaffold を codex で生成し、pytest 緑・CLI 動作を確認済。** 次は M1（機能A MVP）。
WSL(Ubuntu-22.04) に repo を clone（`/home/shin/tosi_design`）し、codex `-s workspace-write`（危険フラグ不要）で scaffold 生成成功。`python3 -m pytest -q` → 7 passed。`python -m nmincity run ...` スタブ動作確認。

## マイルストーン状況
| ID | マイルストーン | 状態 |
|----|----------------|------|
| M0a | 環境セットアップ（Node+codex導入, git init, push） | 🟡 ほぼ完了（codex login 待ち） |
| M0b | プロジェクトscaffold（config・空IF・README・PROGRESS） | ✅ 完了（pytest 7緑） |
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
1. ✅ clone・git identity 設定・M0b scaffold 生成・pytest 緑・commit/push
2. **M1（機能A MVP）の codex 仕様プロンプト作成** → osmnx loader + osmnx_backend(ego_graph 到達圏) + reachability a(i,c) + score S + folium 地図 + tests
3. M1 では geo 依存（osmnx/geopandas 等）が必要。`python3.10-venv` 未導入のため venv 不可 → `pip install --user` か `sudo apt install python3.10-venv` でvenv のどちらか要判断
4. 対象 OSM 地区名の確定（既定：小さめの東京の地区）

## 学び / 決定
- Windows ネイティブ codex は書込にサンドボックス全無効フラグが必須 → 不採用。**WSL で `-s workspace-write`（安全）を使う**。
- WSL 環境は構築済（HANDOVER_WSL.md にステータス表）。

## ブロッカー / 要ユーザー対応
- ✅ codex 認証（Windows・WSL とも ChatGPT ログイン済）
- ⚠️ GitHub push 認証（WSL は GCM/PAT 未設定）— push 時に要確認
- ⚠️ `python3.10-venv` 未導入（venv 作成不可）。M0b は user-level pytest で代替。M1 の geo 依存導入方針を要判断
- ❓ 対象OSM地区名（後で `--place` 指定可）
