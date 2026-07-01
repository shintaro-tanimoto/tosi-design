# n分都市化支援ツール

近接性都市（n分都市）の考え方に基づき、任意の地区について用途カテゴリ別の到達可否と重み付きスコアを診断する Python プロトタイプです。要件定義書 §6 の重みづけ設計を起点に、教育・自然を高めに置いた初期重みと、§6.7 の都市デザインの質レイヤを扱える構成にしています。

## セットアップ

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip install -e .
```

## 使い方

OSM 実データから対象地区を解析します。`outputs/` に地図・チャート HTML を生成します。

```bash
# 機能A: n分都市度 S と歩行環境の質 Q を診断（--quality で質レイヤ §6.7 も計算）
# run は S 地図に加え、7要素レイヤー分け地図と近接性ヒートマップも出力します。
python -m nmincity run --place "天王寺区, 大阪市, 大阪府, 日本" --minutes 10 --mode walk --quality

# 統合ダッシュボード（基準 S／実効 S（質補正）／Q 地図／7要素レイヤー／到達率／重み根拠を1枚に並置）
python -m nmincity dashboard --place "天王寺区, 大阪市, 大阪府, 日本" --minutes 10

# 複数地区の7要素プロファイル比較（レーダー＋グループ棒、既定は config.COMPARISON_PLACES）
python -m nmincity compare-places --minutes 10
python -m nmincity compare-places --places "天王寺区, 大阪市, 大阪府, 日本" "住吉区, 大阪市, 大阪府, 日本" --minutes 10

# 機能B: 不足エリアへのルールベース改善提案（新設なし時間帯転換を第一候補・優先度 w_c×影響人口）
# 提案対象は要件 §6.6-1 に従い、不足エリア（S<0.5）の全欠落カテゴリと、
# それ以外の起点の高重みカテゴリ（正規化重み>=0.14）欠落に限定されます。
python -m nmincity propose --place "天王寺区, 大阪市, 大阪府, 日本" --minutes 10 --top 10

# 重み感度分析＋シナリオ比較（現状 vs 重み変更後 vs 提案実施後）
python -m nmincity compare --place "天王寺区, 大阪市, 大阪府, 日本" --minutes 10

# 機能C: 不足カテゴリの最適配置（重みづけ人口カバー最大化 MCLP、k 箇所）
python -m nmincity allocate --place "天王寺区, 大阪市, 大阪府, 日本" --minutes 10 --k 3
```

`--sample N` で評価起点を間引けます（高速化）。地区名は `--place` で任意に変更可能です。
既定地区は大阪（天王寺区）です。比較対象地区は `config.COMPARISON_PLACES`、重みづけの根拠（事例・施策・マスタープラン出典）は `config.WEIGHT_RATIONALE` で編集できます。

### 可視化（ビジュアライズ）

- **7要素レイヤー分け地図**: 用途カテゴリ別の到達/未到達を `LayerControl` で切替表示（`run` が出力）。
- **7要素レイヤー別 到達面（重みづけ前）**: 各要素の到達評価 `a(i,c)`（到達=1/未到達=0）を線形補間し、赤→緑のグラデーション連続面を `LayerControl` で切替表示（`viz-gdb` が `reach_<category>` 列から出力）。
- **近接性ヒートマップ**: S を連続面で表示し、各カテゴリの未到達密度もトグル可能（`run` が出力）。
- **統合ダッシュボード**: S と Q を合成せず並置（要件 §6.7.1）し、重み根拠表を併載（`dashboard`）。
- **地区比較**: 7要素到達率プロファイルをレーダー＋グループ棒で地区横断比較（`compare-places`）。

## アーキテクチャ

ネットワーク計算は `NetworkBackend` 抽象に分離しています。コア（スコア・質・提案・感度・配置）はバックエンドへ依存せず、
`OsmnxBackend` から ArcGIS/arcpy ベースの `ArcpyBackend` へ差し替えられる設計です。スコアリングの純ロジックは
`networkx`/`osmnx` 非依存で、単体テスト可能です。

主な構成:

- `src/nmincity/config.py`: §6.3 のカテゴリ重み `w_c`、§6.4 の時間パラメータ、§6.7 の質重み（`WALK_QUALITY_WEIGHTS`/`EXPERIENTIAL_WEIGHTS`/`QUALITY_WEIGHTS`）・時間帯稼働度・クロノトピー転換
- `src/nmincity/backend/`: 到達圏計算バックエンドの抽象（`base.py`）と osmnx 実装（`osmnx_backend.py`）
- `src/nmincity/core/score.py`: 近接性スコア `S(i)`、質スコア `Q(i)`、統合 `environment_quality`
- `src/nmincity/core/walkability.py`: §6.7 要素A 歩行環境の質・インピーダンス補正
- `src/nmincity/core/chronotopia.py`: §6.7 要素B 時間帯別到達 `a(i,c,t)`・クロノトピー転換
- `src/nmincity/core/experiential.py`: §6.7 要素C 体験指標（にぎわい/滞留/トポフィリー/時間帯表情）
- `src/nmincity/core/proposals.py`: 機能B ルールベース改善提案（優先度 `w_c×影響人口`）
- `src/nmincity/core/sensitivity.py`: 重み感度分析・シナリオ比較（`mean_S=Σŵ_c·reach_rate[c]`）
- `src/nmincity/core/allocation.py`: 機能C Location-Allocation（MCLP、pulp 厳密解＋greedy フォールバック）
- `src/nmincity/data/gdb_loader.py`: ArcGIS `.gdb` の計算済み結果を `arcpy` 非依存で読む層（スコア点群・メッシュセル復元・施設点群・人口加重到達率）
- `src/nmincity/cli.py`: `run`/`dashboard`/`compare-places`/`propose`/`compare`/`allocate`/`viz-gdb`/`compare-gdb` サブコマンド

質レイヤ・提案・最適化はいずれも調整可能な重みで透明に効く設計とし、近接性 `S` と質 `Q` は既定では合成せず並置します（要件 §6.7.1 / §11）。

## ArcGIS Pro での利用

ArcGIS Pro 3.x と Network Analyst エクステンション、徒歩/自転車の Travel Mode を持つ Network Dataset が必要です。`arcpy` は ArcGIS Pro 同梱の Windows 専用ライセンス製品のため、Linux や通常の Python 環境では実行できません。リポジトリの自動テストは `arcpy` 非依存部分のみを対象にしています。

手順:

1. ArcGIS Pro の Python 環境、または `arcpy` を利用できる conda env で、このリポジトリを editable install します。

   ```bash
   python -m pip install -e .
   ```

2. ArcGIS Pro で Python Toolbox `arcgis/nmincity.pyt` を追加します。
3. 「近接性スコア診断 (機能A)」ツールに Network Dataset、評価起点 Feature Class、カテゴリ別施設 Feature Class、n分、移動手段、出力 Feature Class を指定して実行します。
4. 出力 Feature Class の `S` と `label` フィールドをシンボロジで可視化します。診断ツールは
   カテゴリ別の到達(0/1)を `reach_<category>` 列としても出力するので、ローカル可視化（後述）で
   7要素到達率の比較ができます。

設計上、ArcGIS 版は `ArcpyBackend` が `NetworkBackend` を実装し、カテゴリ別到達度だけを返します。近接性スコア `S` は OSM 版と同じ `nmincity.core.score.proximity_score` で計算するため、`OsmnxBackend` と `ArcpyBackend` を同一スコア計算で差し替え可能です。

### ArcGIS の計算済み結果をローカルで可視化（`arcpy` 不要）

ArcGIS Pro で出力した `.gdb`（スコア Feature Class と `osm_<category>` 施設点群）は、`arcpy` を使わず
geopandas + pyogrio で読んで folium 地図にできます。分析は ArcGIS、可視化は Python という役割分担です。

```bash
# 単一地区: 中心点スコア / メッシュ塗り / 滑らかな補間サーフェス / 7要素施設レイヤー / ダッシュボード
python -m nmincity viz-gdb --gdb tennoji.gdb --place "天王寺区"

# 複数地区比較: 7要素到達率のレーダー / グループ棒（reach_<category> 列が必要）
python -m nmincity compare-gdb --gdbs tennoji.gdb sumiyoshi.gdb sakai.gdb --labels 天王寺 住吉 堺南
```

スコアの面表示は2種類を出力します。**メッシュ塗り**（各メッシュセルを評価ラベル色で塗る離散表示）と、
**補間サーフェス**（格子点を線形補間した連続的で滑らかなヒートマップ）です。メッシュセルは中心点から
緯度経度方向の格子間隔を推定して正方形を復元します（日本の地域メッシュは緯度経度に整列）。

## マイルストーン

- M0b: スキャフォールド、設定、バックエンド抽象、スコア計算、テスト
- M1: osmnx/networkx による到達圏とカテゴリ別到達度・近接性スコア S（`run`）
- M2: 質レイヤ §6.7（要素A 歩行環境の質・要素B クロノトピー・要素C 体験指標・統合 Q・時間帯可視化）
- M3: 機能B 改善提案（`propose`）＋感度分析・シナリオ比較（`compare`）
- M4: 機能C Location-Allocation 最適配置（`allocate`、任意機能）
- M5: ArcGIS `.gdb` のローカル可視化（`arcpy` 非依存）— 7要素レイヤー・スコア面2種（メッシュ塗り／補間サーフェス）・複数地区比較（`viz-gdb`／`compare-gdb`）

## テスト

```bash
python -m pytest -q
```
