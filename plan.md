# n分都市化支援ツール：実装プラン（Claude=設計/指揮 × codex=実装）

> このファイルは作業ディレクトリ直下の plan コピー。正本は承認済みプラン。進捗は `PROGRESS.md` 参照。

## Context（なぜ・何を）
`要件定義書.html`（近接性都市＝n分都市の診断ツール。§6.7で都市デザインの質レイヤを追加済み）を基に、**実際に動くプログラム**を書き始める。
ユーザー指示：**Claude(Opus 4.8) が必要なプログラムを分割して仕様化・指揮し、codex CLI(gpt5.5) に実装させる**。コードは git 管理し `https://github.com/shintaro-tanimoto/tosi-design`（既存・空）へ適宜 push。

意思決定（確認済）:
- **ターゲット：まず標準Pythonプロトタイプ（osmnx/geopandas/networkx）。後で ArcGIS `.pyt` に作り直せる設計にする。**
- **codex：Claude が Node.js+codex を導入し、ユーザーが `codex login` で認証 → 以降 Claude が `codex exec` で指揮。**
- **データ：OSM から実地区を osmnx で取得（地区名は後で指定。既定は小さめの東京の地区＝高速）。**

環境（確認済）: git=有(identity設定済/GCM構成済)、対象repo=存在・空、python=3.10.11。**codex/node/gh=未導入、ArcGIS=無し。**

## 設計の肝：バックエンド差し替え可能アーキテクチャ
コア（スコア/質/提案）を計算バックエンドから分離し、将来 ArcGIS 化を局所化する。
```
src/nmincity/
  config.py        # 7カテゴリ・初期重みw_c(§6.3)・質サブ重みv_q(§6.7)・n/移動速度4.8km/h・時間帯バケット・カテゴリマッピング
  backend/
    base.py        # NetworkBackend ABC: service_area(origin,minutes,mode), reachable_categories(...) など
    osmnx_backend.py  # networkx ego_graph による到達圏（今回実装）
    # arcpy_backend.py … 将来: Network Analyst Service Area（IFのみ用意・未実装）
  data/loader.py   # osmnx で 歩行ネットワーク・カテゴリ別POI・評価起点(グリッド/建物重心)・街路属性を取得
  core/
    reachability.py  # a(i,c) と 時間依存 a(i,c,t)
    score.py         # S(i)=Σ w_c·a(i,c)（量・軸1）/ Q(i)=Σ v_q·b(i,q)（質・軸2）/ 任意 S*=S·f(Q)
    walkability.py   # §6.7要素A: OSMタグ(歩道/道路種別/緑/沿道店舗)→区間品質→インピーダンス補正
    chronotopia.py   # §6.7要素B: 時間帯ごとの到達カテゴリ・時間帯転換
    proposals.py     # 機能B: 不足メッシュ抽出→「新設なし時間帯転換」優先, 優先度=w_c×影響人口
  viz/maps.py      # folium: スコア/歩きやすさヒートマップ・不足強調・S×Q散布(plotly/matplotlib)・時間帯切替
  cli.py           # `python -m nmincity run --place "..." --minutes 15 --mode walk`
tests/             # pytest: スコア計算・重み正規化・合成グラフでの到達圏
要件定義書.html     # 仕様（同梱）  README.md / requirements.txt / pyproject.toml / .gitignore
PROGRESS.md        # 進捗・タスク・決定事項・次アクション（毎ステップ更新しpush）
```
- **人口メッシュ**：実pop（国勢調査250m）は後付け。プロトタイプは評価起点＝グリッド点 or 建物重心、人口重みは建物数近似（要件のフォールバックに整合、近似である旨を明示）。
- 機能A/質レイヤを先行、機能C(Location-Allocation)は後期マイルストーン（pulp等）。

## 著作権の扱い（重要）
`reference/`（モレノ著書全文テキスト等）は**公開repoに含めない**。`.gitignore` で `reference/` を除外。`要件定義書.html`（本人作・抜粋引用のみ）は同梱可。

## 進捗・タスク管理（逐一メモ・更新）
1. **セッション内タスク**：`TaskCreate`/`TaskUpdate` で各ステップを登録し着手/完了を逐次更新。
2. **`PROGRESS.md`**（このディレクトリ直下）：タスク状態・決定事項・次アクションを各ステップで更新し commit/push。

## codex オーケストレーション方式
1. Claude がモジュール単位の詳細仕様プロンプトを作成
2. `codex exec` を非対話で起動しコード生成（必要に応じ `--full-auto`／承認バイパス）。モデルは codex 既定。
3. Claude が生成物をレビュー＋ `pytest`／CLI 実行で検証 → 不足は再プロンプト
4. Claude が `git add/commit/push`（モジュールごと）

## セットアップ手順
1. `winget install OpenJS.NodeJS.LTS` → npm 確認
2. `npm install -g @openai/codex` → `codex --version`
3. **ユーザー作業**：`codex login`（OpenAI/ChatGPT 認証）
4. git: `git init` → `.gitignore` → remote origin → 初回 commit → `git push -u origin main`
5. `.venv` 作成、requirements 導入（osmnx, geopandas, networkx, folium, plotly, pandas, shapely, pytest）

## マイルストーン（各末で commit/push）
- **M0** スキャフォールド：repo初期化・README・PROGRESS.md・requirements・config・空IF・初回push
- **M1** 機能A(MVP)：loader(osmnx)+osmnx_backend+reachability+score S+基本folium地図+tests
- **M2** 質レイヤ(§6.7)：walkability(A)+chronotopia a(i,c,t)(B)+体験指標(C)+Q(i)
- **M3** 提案＋可視化：proposals(機能B)+感度分析+S×Q散布+時間帯切替
- **M4(任意)** 機能C：Location-Allocation 最適配置

## 検証
- `python -m pytest -q` 緑／`python -m nmincity run --place "<地区>" --minutes 15 --mode walk` 完走で `outputs/` に地図HTML生成
- `git log --oneline` でマイルストーン単位commit・push反映・`reference/`非同梱を確認
- コアが `NetworkBackend` 経由のみでネットワークに触れている（ArcGIS化差し替え可能）ことを確認

---

# 追加機能プラン：ArcGIS .gdb から folium 可視化（M5 / 2026-06-29 承認）

## Context（なぜ・何を）
ArcGIS Pro の Python Toolbox（`arcgis/nmincity.pyt` の機能A）を実行した結果を `tennoji.gdb` に保存済み。
ArcGIS Pro（`arcpy`・Windows 専用ライセンス）を再び開かなくても、この .gdb の**計算済み結果**を
ローカルの Python で地図 HTML として可視化したい。

`tennoji.gdb` の中身（`pyogrio` で確認済み）:
- `score_tennoji` / `score_tennoji_5min` … 105点、列 `OOID, S, label`、CRS **EPSG:2448**。機能A の出力 FC。
- `origins_tennoji` … 評価起点（人口メッシュ、`POP` 等）、CRS 2448。
- `osm_education / osm_nature / osm_goods / osm_health / osm_transit / osm_leisure / osm_work`
  … 7要素の施設点群（geometry のみ）、CRS **EPSG:4326**。レイヤー名サフィックスが
  `config.CATEGORY_NAMES` のキーと完全一致する。

既存 folium 可視化 `score_map(points)` / `score_heatmap(points, ...)` は `(lat, lon, S)` 点群を受け取り
`S` から `score_label` でラベル色を再計算する作りなので、**.gdb の `S` をそのまま渡せる**。
必要なのは「.gdb を読んで 4326 に再投影し点群へ整形する薄いローダ」と「CLI コマンド」だけ。

ユーザー選択: **スコア地図＋ヒートマップ＋7要素施設マップ**（gdb 内情報を最大活用）。

## 変更内容
1. **新規 `src/nmincity/data/gdb_loader.py`**（geopandas、arcpy 非依存の純データ層）
   - `list_score_layers(gdb_path)` … `pyogrio.list_layers` で `S` 列を持つレイヤー名を返す（自動検出）。
   - `load_score_points(gdb_path, layer)` … `read_file` → `.to_crs(4326)` → `(geom.y, geom.x, float(S))`。S が NULL の行はスキップ。
   - `load_facility_points(gdb_path, prefix="osm_")` … `CATEGORY_NAMES` のキーごとに `{prefix}{category}` レイヤーを 4326 で読み `(lat, lon)` 化。全カテゴリをキーに持つ（無いレイヤーは空）。
   - CRS 変換は `src/nmincity/data/loader.py:63-64` の `to_crs(4326)` 流儀に追従。
2. **新規 viz `facility_layers_map`** を `src/nmincity/viz/maps.py` に追加
   - `category_layers_map`（maps.py:86）の `FeatureGroup`＋`LayerControl` パターン踏襲。入力は施設座標 `dict[str, list[(lat,lon)]]`。各カテゴリを `CATEGORY_NAMES` 名のグループで色分け、先頭のみ初期表示。凡例は "7要素 施設分布"。
3. **`src/nmincity/cli.py` に `viz-gdb` サブコマンド追加**
   - 引数: `--gdb`（必須）, `--place`（既定 `天王寺区`）, `--score-layer`（既定: 自動検出すべて）, `--facility-prefix`（既定 `osm_`）。
   - 各スコアレイヤー → `load_score_points` → `score_map`＋`score_heatmap` を `save_map` 出力。続けて `load_facility_points` → `facility_layers_map` 出力。
   - 出力（`_safe_filename` 流用）: `outputs/{place}_gdb_{layer}_S.html` / `_heatmap.html` / `outputs/{place}_gdb_facilities.html`。
   - 点数・S 平均/最小/最大（`_summary` 流用）と出力パスを表示。`osmnx`/`networkx` 非依存。
4. **`tests/test_gdb_loader.py`**（軽量・実gdb非依存）: 合成 GeoDataFrame(EPSG:2448+`S`) の再投影/タプル化検証、`facility_layers_map` が `folium.Map` を返しカテゴリ数の FeatureGroup を持つこと。
   - 注: OpenFileGDB は読み取り専用ドライバのため「書いて読み直す」テストは作らない。実 gdb は手動スモークで担保。
5. **`README.md`** 「ArcGIS Pro での利用」付近に arcpy 不要のローカル可視化経路を追記:
   `python -m nmincity viz-gdb --gdb tennoji.gdb --place "天王寺区"`

## 再利用する既存資産
- `viz/maps.py`: `score_map`(L27), `score_heatmap`(L133), `save_map`(L56)。
- `config.py`: `CATEGORY_NAMES`, `score_label`。
- `cli.py`: `_safe_filename`(L681), `_summary`(L675)。
- `data/loader.py:63-64`: `to_crs(4326)` の流儀。

## 環境メモ（別PC向け）
- `.gdb` 読み取りには geopandas + pyogrio（GDAL OpenFileGDB ドライバ）。当 .venv では `geopandas 1.1.3` / `pyogrio 0.12.1` で読めた（`fiona` 未導入でも可）。
- スコアレイヤーは EPSG:2448（平面直角座標系VI系・大阪）→ folium 用に 4326 へ要再投影。`osm_*` は既に 4326。

## 検証（手動・実データ）
```bash
source .venv/bin/activate
python -m nmincity viz-gdb --gdb tennoji.gdb --place "天王寺区"
ls outputs/天王寺区_gdb_*.html   # S地図/ヒート/施設マップが生成される
# HTML をブラウザで開き、点が天王寺区域内に分布し色分け（良好/要改善/不足）される事を確認
python -m pytest -q              # 既存＋新規 test_gdb_loader が緑
```
