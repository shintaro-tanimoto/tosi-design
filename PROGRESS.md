# PROGRESS — n分都市化支援ツール

最終更新: 2026-06-23 / 担当: Claude(Opus 4.8) 設計・指揮 ＋ codex CLI 実装

## 現在地
**M3（機能B 提案＋感度分析＋シナリオ比較）完了＝要件の機能A・質レイヤ・機能Bが一通り実走可能。** `run`(S/Q診断)・`propose`(提案)・`compare`(感度分析・シナリオ比較) の3サブコマンド。残るは M4（任意・機能C Location-Allocation）。
作業ディレクトリ `/home/shint/tosi-design/tosi-design`（WSL）。venv 構築済（geo 依存 + scikit-learn、`pip install -e .` 済）。`pytest` → 38 passed。
- M3a（機能B提案）: 不足抽出→新設なし時間帯転換(第一候補)＋近傍多機能転換→優先度 w_c×影響人口。`propose` で根拠付き提案＋地図。
- M3b（感度分析・シナリオ比較）: mean_S=Σŵ_c·reach_rate[c] の線形性で透明化。`compare` で現状/重み変更後(equal/education_heavy/nature_heavy)/提案実施後を並置＋plotlyチャート3種。
- 谷中5分walk compare(sample150): baseline 0.805→nature_heavy 0.832→提案実施後 0.903(良好95→132)。感度: 医療(reach0.62,Δ-0.009)・学ぶ(0.70,-0.005)が不足側、自然/娯楽(0.99,+0.009)が飽和。
- M2a（要素A）: 街路区間の質 0–1 を OSMタグ＋近傍POIから算出→インピーダンス補正で実効到達圏を縮める。
- M2b（要素B/C）: a(i,c,t)＝空間到達×時間帯稼働度＋クロノトピー転換（夜の学校→leisure）。体験指標 liveliness/lingering/topophilia/time_variation。Q を2階層化（WALK_QUALITY_WEIGHTS=要素A 5指標、QUALITY_WEIGHTS=walkability＋要素C）。
- 谷中 5分walk `--quality`（sample80）: S avg=0.664、Q avg=0.531、S(morning/daytime/evening)=0.552/0.642/0.429。夜にSが下がるのは教育/医療/仕事の夜間稼働が低いため（要素Bが効いている）。出力: S地図・歩きやすさ地図・S×Q散布図・時間帯切替地図（`outputs/`、.gitignore対象）。

## マイルストーン状況
| ID | マイルストーン | 状態 |
|----|----------------|------|
| M0a | 環境セットアップ（Node+codex導入, git init, push） | ✅ 完了 |
| M0b | プロジェクトscaffold（config・空IF・README・PROGRESS） | ✅ 完了（pytest 7緑） |
| M1 | 機能A(MVP)：到達圏＋重み合成スコアS＋基本地図 | ✅ 完了（谷中で実走・pytest 10緑） |
| M2 | 質レイヤ(§6.7)：歩行環境A＋クロノトピーB＋体験指標C＋Q | ✅ 完了（M2a要素A＋M2b要素B/C・統合Q・時間帯可視化・pytest 27緑） |
| M3 | 提案(機能B)＋感度分析＋シナリオ比較 | ✅ 完了（M3a提案＋M3b感度分析・シナリオ比較・pytest 38緑） |
| M4 | (任意) 機能C：Location-Allocation 最適配置 | ⬜ 未着手 |

## 直近の決定事項
- ターゲット＝標準Pythonプロトタイプ（osmnx/networkx/geopandas）。`NetworkBackend` 抽象で後から ArcGIS `.pyt` 化可能に。
- 実装は codex CLI(gpt5.5) に委譲、Claude が仕様化・レビュー・git管理。
- データ＝OSM実地区（osmnx）。対象地区名は未確定（既定：小さめの東京の地区）。
- `reference/`（モレノ著書全文）は著作権配慮で `.gitignore` 除外（公開repoに含めない）。

## 次アクション（WSL 側）
1. ✅ M0b/M1/M2/M3（機能A・質レイヤ・機能B・感度分析・シナリオ比較）完了・pytest 38緑・谷中で run/propose/compare 実走・commit/push
2. **M4（任意・機能C Location-Allocation）** → 重みづけ人口カバー最大化で k 箇所の最適新設/転換地を算出（pulp 等）。要件では発展扱い・非必須。やるなら NetworkBackend 経由で到達圏、最適化は透明な重み（w_c×人口）目的に限定（§5-C/§11）
3. 仕上げ候補（M4 前後）: README をサブコマンド3種（run/propose/compare）に更新、感度分析は v_q（質重み）版も追加余地、ArcGIS `.pyt` 化に向け backend 差し替え点の最終確認
4. 既知の簡略化（実運用で要拡張）: `_nearby_convertible`（到達圏内施設のみ）→2x到達圏/直線バッファ＋空間インデックス、TIME_CONVERSIONS の根拠付き拡充、影響人口の人口メッシュ接続（`population` 引数で差し替え可能な設計済み）

## 学び / 決定
- Windows ネイティブ codex は書込にサンドボックス全無効フラグが必須 → 不採用。**WSL で `-s workspace-write`（安全）を使う**。
- WSL 環境は構築済（HANDOVER_WSL.md にステータス表）。

## ブロッカー / 要ユーザー対応
- ✅ codex 認証（Windows・WSL とも ChatGPT ログイン済）
- ⚠️ GitHub push 認証（WSL は GCM/PAT 未設定）— push 時に要確認
- ⚠️ `python3.10-venv` 未導入（venv 作成不可）。M0b は user-level pytest で代替。M1 の geo 依存導入方針を要判断
- ❓ 対象OSM地区名（後で `--place` 指定可）
