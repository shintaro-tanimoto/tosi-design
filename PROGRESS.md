# PROGRESS — n分都市化支援ツール

最終更新: 2026-06-23 / 担当: Claude(Opus 4.8) 設計・指揮 ＋ codex CLI 実装

## 現在地
**M2a（質レイヤ §6.7 要素A：歩行環境の質）完了。** 街路区間の質 0–1 を OSM タグ＋近傍POIから算出し、インピーダンス補正で実効到達圏を縮める。S(i) と環境の質 Q(i) を並置出力し、歩きやすさ地図＋S×Q 散布図を生成。次は M2b（要素B クロノトピー a(i,c,t)＋要素C 体験指標＋時間帯切替可視化）。
作業ディレクトリ `/home/shint/tosi-design/tosi-design`（WSL）。venv 構築済（geo 依存 + scikit-learn、`pip install -e .` 済）。`pytest` → 19 passed（既存10＋walkability 9）。
谷中 5分walk `--quality`（sample80）: S avg=0.664/min0.100/max0.900、Q avg=0.597/min0.435/max0.708、良好20・要改善44・不足16。M1 の S=0.81 から下がったのは質補正で実効到達圏が縮むため（要素Aが効いている）。地図は `outputs/`（.gitignore対象）。

## マイルストーン状況
| ID | マイルストーン | 状態 |
|----|----------------|------|
| M0a | 環境セットアップ（Node+codex導入, git init, push） | ✅ 完了 |
| M0b | プロジェクトscaffold（config・空IF・README・PROGRESS） | ✅ 完了（pytest 7緑） |
| M1 | 機能A(MVP)：到達圏＋重み合成スコアS＋基本地図 | ✅ 完了（谷中で実走・pytest 10緑） |
| M2 | 質レイヤ(§6.7)：歩行環境A＋クロノトピーB＋体験指標C＋Q | 🟡 要素A完了（M2a）／要素B・C次回（M2b） |
| M3 | 提案(機能B)＋感度分析＋S×Q散布＋時間帯可視化 | ⬜ 未着手 |
| M4 | (任意) 機能C：Location-Allocation 最適配置 | ⬜ 未着手 |

## 直近の決定事項
- ターゲット＝標準Pythonプロトタイプ（osmnx/networkx/geopandas）。`NetworkBackend` 抽象で後から ArcGIS `.pyt` 化可能に。
- 実装は codex CLI(gpt5.5) に委譲、Claude が仕様化・レビュー・git管理。
- データ＝OSM実地区（osmnx）。対象地区名は未確定（既定：小さめの東京の地区）。
- `reference/`（モレノ著書全文）は著作権配慮で `.gitignore` 除外（公開repoに含めない）。

## 次アクション（WSL 側）
1. ✅ M0b/M1/M2a 完了（M2a＝要素A walkability＋Q(i)＋S×Q並置・pytest 19緑・谷中で実走・commit/push）
2. **M2b（質レイヤ §6.7 残り）の codex 仕様作成** → chronotopia a(i,c,t)(要素B: 時間帯別到達・新設なし時間帯転換) + 体験指標(要素C: にぎわい/滞留/トポフィリー/時間帯表情) + Q への要素C統合 + 時間帯切替可視化
3. M2b で `QUALITY_WEIGHTS` の構成見直し余地（現状は要素A 5サブ指標。§6.7.1 の b(i,q) は要素A・C 両方の指標 → Q 重みの再設計を検討）
4. 文脈指標 `_proximity_indicator` は edge×POI 全探索でやや非効率（谷中規模は許容）。広域地区では空間インデックス（KDTree等）化を検討

## 学び / 決定
- Windows ネイティブ codex は書込にサンドボックス全無効フラグが必須 → 不採用。**WSL で `-s workspace-write`（安全）を使う**。
- WSL 環境は構築済（HANDOVER_WSL.md にステータス表）。

## ブロッカー / 要ユーザー対応
- ✅ codex 認証（Windows・WSL とも ChatGPT ログイン済）
- ⚠️ GitHub push 認証（WSL は GCM/PAT 未設定）— push 時に要確認
- ⚠️ `python3.10-venv` 未導入（venv 作成不可）。M0b は user-level pytest で代替。M1 の geo 依存導入方針を要判断
- ❓ 対象OSM地区名（後で `--place` 指定可）
