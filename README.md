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
python -m nmincity run --place "谷中, 台東区, 東京都, 日本" --minutes 5 --mode walk --quality

# 機能B: 不足エリアへのルールベース改善提案（新設なし時間帯転換を第一候補・優先度 w_c×影響人口）
python -m nmincity propose --place "谷中, 台東区, 東京都, 日本" --minutes 5 --top 10

# 重み感度分析＋シナリオ比較（現状 vs 重み変更後 vs 提案実施後）
python -m nmincity compare --place "谷中, 台東区, 東京都, 日本" --minutes 5

# 機能C: 不足カテゴリの最適配置（重みづけ人口カバー最大化 MCLP、k 箇所）
python -m nmincity allocate --place "谷中, 台東区, 東京都, 日本" --minutes 5 --k 3
```

`--sample N` で評価起点を間引けます（高速化）。地区名は `--place` で任意に変更可能です。

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
- `src/nmincity/cli.py`: `run`/`propose`/`compare`/`allocate` サブコマンド

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
4. 出力 Feature Class の `S` と `label` フィールドをシンボロジで可視化します。

設計上、ArcGIS 版は `ArcpyBackend` が `NetworkBackend` を実装し、カテゴリ別到達度だけを返します。近接性スコア `S` は OSM 版と同じ `nmincity.core.score.proximity_score` で計算するため、`OsmnxBackend` と `ArcpyBackend` を同一スコア計算で差し替え可能です。

## マイルストーン

- M0b: スキャフォールド、設定、バックエンド抽象、スコア計算、テスト
- M1: osmnx/networkx による到達圏とカテゴリ別到達度・近接性スコア S（`run`）
- M2: 質レイヤ §6.7（要素A 歩行環境の質・要素B クロノトピー・要素C 体験指標・統合 Q・時間帯可視化）
- M3: 機能B 改善提案（`propose`）＋感度分析・シナリオ比較（`compare`）
- M4: 機能C Location-Allocation 最適配置（`allocate`、任意機能）

## テスト

```bash
python -m pytest -q
```
