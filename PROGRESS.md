# PROGRESS — n分都市化支援ツール

最終更新: 2026-06-23 / 担当: Claude(Opus 4.8) 設計・指揮 ＋ codex CLI 実装

## 現在地
**M2（質レイヤ §6.7）完了＝要素A（歩行環境の質）＋要素B（クロノトピー a(i,c,t)）＋要素C（体験指標）＋統合 Q(i)＋時間帯切替可視化。** S(量) と Q(質) を合成せず並置（§6.7.1）。次は M3（機能B 提案＋感度分析＋シナリオ比較）。
作業ディレクトリ `/home/shint/tosi-design/tosi-design`（WSL）。venv 構築済（geo 依存 + scikit-learn、`pip install -e .` 済）。`pytest` → 27 passed。
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
| M3 | 提案(機能B)＋感度分析＋S×Q散布＋時間帯可視化 | ⬜ 未着手 |
| M4 | (任意) 機能C：Location-Allocation 最適配置 | ⬜ 未着手 |

## 直近の決定事項
- ターゲット＝標準Pythonプロトタイプ（osmnx/networkx/geopandas）。`NetworkBackend` 抽象で後から ArcGIS `.pyt` 化可能に。
- 実装は codex CLI(gpt5.5) に委譲、Claude が仕様化・レビュー・git管理。
- データ＝OSM実地区（osmnx）。対象地区名は未確定（既定：小さめの東京の地区）。
- `reference/`（モレノ著書全文）は著作権配慮で `.gitignore` 除外（公開repoに含めない）。

## 次アクション（WSL 側）
1. ✅ M0b/M1/M2（M2a要素A＋M2b要素B/C・統合Q・時間帯可視化）完了・pytest 27緑・谷中で実走・commit/push
2. **M3（機能B 提案＋可視化）の codex 仕様作成** → proposals: 不足メッシュ抽出→「新設なし時間帯転換」優先（TIME_CONVERSIONS を活用）・多機能転換候補の空間近傍解析・優先度＝w_c×影響人口。感度分析（重み変更→再計算）・シナリオ比較（現状 vs 重み変更 vs 提案後）の並置可視化
3. 感度分析の土台は既存：`proximity_score`/`quality_score`/`environment_quality` が weights 差し替え可能（v_q・w_c とも調整可）
4. 文脈指標 `_proximity_indicator`/`origin_context` は edge×POI 全探索でやや非効率（谷中規模は許容）。広域地区では空間インデックス（KDTree等）化を検討
5. クロノトピー転換は現状 evening の education→leisure のみ（要件の例）。実運用では TIME_CONVERSIONS をデータ/根拠付きで拡充

## 学び / 決定
- Windows ネイティブ codex は書込にサンドボックス全無効フラグが必須 → 不採用。**WSL で `-s workspace-write`（安全）を使う**。
- WSL 環境は構築済（HANDOVER_WSL.md にステータス表）。

## ブロッカー / 要ユーザー対応
- ✅ codex 認証（Windows・WSL とも ChatGPT ログイン済）
- ⚠️ GitHub push 認証（WSL は GCM/PAT 未設定）— push 時に要確認
- ⚠️ `python3.10-venv` 未導入（venv 作成不可）。M0b は user-level pytest で代替。M1 の geo 依存導入方針を要判断
- ❓ 対象OSM地区名（後で `--place` 指定可）
