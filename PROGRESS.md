# PROGRESS — n分都市化支援ツール

最終更新: 2026-06-23 / 担当: Claude(Opus 4.8) 設計・指揮 ＋ codex CLI 実装

## 現在地
**M3a（機能B 提案エンジンのコア）完了。** 不足カテゴリ抽出→「新設なし時間帯転換」を第一候補＋近傍既存施設の多機能転換候補→優先度 `w_c×影響人口` でランキング。`propose` サブコマンドで根拠付き提案リスト＋提案地図を出力。次は M3b（感度分析＋シナリオ比較可視化）。
作業ディレクトリ `/home/shint/tosi-design/tosi-design`（WSL）。venv 構築済（geo 依存 + scikit-learn、`pip install -e .` 済）。`pytest` → 32 passed。
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
| M3 | 提案(機能B)＋感度分析＋シナリオ比較 | 🟡 M3a 機能B提案コア完了／感度分析・シナリオ比較は M3b |
| M4 | (任意) 機能C：Location-Allocation 最適配置 | ⬜ 未着手 |

## 直近の決定事項
- ターゲット＝標準Pythonプロトタイプ（osmnx/networkx/geopandas）。`NetworkBackend` 抽象で後から ArcGIS `.pyt` 化可能に。
- 実装は codex CLI(gpt5.5) に委譲、Claude が仕様化・レビュー・git管理。
- データ＝OSM実地区（osmnx）。対象地区名は未確定（既定：小さめの東京の地区）。
- `reference/`（モレノ著書全文）は著作権配慮で `.gitignore` 除外（公開repoに含めない）。

## 次アクション（WSL 側）
1. ✅ M0b/M1/M2/M3a 完了・pytest 32緑・谷中で実走（propose: 学ぶ/医療の多機能転換を優先度順に提示）・commit/push
2. **M3b（感度分析＋シナリオ比較）の codex 仕様作成** → 重み(w_c・v_q)変更で S/Q/提案がどう変わるかの比較（感度分析の図表 §9）・シナリオ並置（現状 vs 重み変更後 vs 提案実施後 §9）。`proposals` の effect 推定（提案適用後の S 再計算）も検討
3. 感度分析の土台は既存：`proximity_score`/`quality_score`/`environment_quality`/各提案関数が weights 差し替え可能（v_q・w_c とも調整可）
4. 文脈指標 `_proximity_indicator`/`origin_context`、機能Bの `_nearby_convertible`（到達圏内施設のみの簡易版）は谷中規模で許容。広域では空間インデックス＋2x到達圏/直線バッファへ拡張
5. クロノトピー転換は現状 evening の education→leisure のみ（要件の例）。実運用では TIME_CONVERSIONS をデータ/根拠付きで拡充
6. 影響人口は現状一様近似（起点数ベース）。国勢調査250mメッシュ等の人口重みを `population` 引数で差し替え可能な設計済み

## 学び / 決定
- Windows ネイティブ codex は書込にサンドボックス全無効フラグが必須 → 不採用。**WSL で `-s workspace-write`（安全）を使う**。
- WSL 環境は構築済（HANDOVER_WSL.md にステータス表）。

## ブロッカー / 要ユーザー対応
- ✅ codex 認証（Windows・WSL とも ChatGPT ログイン済）
- ⚠️ GitHub push 認証（WSL は GCM/PAT 未設定）— push 時に要確認
- ⚠️ `python3.10-venv` 未導入（venv 作成不可）。M0b は user-level pytest で代替。M1 の geo 依存導入方針を要判断
- ❓ 対象OSM地区名（後で `--place` 指定可）
