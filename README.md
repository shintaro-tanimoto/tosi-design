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

現時点の M0b はスキャフォールドとスコア計算コアのみです。地理処理は M1 で実装します。

```bash
python -m nmincity run --place "東京都渋谷区" --minutes 15 --mode walk
```

## アーキテクチャ

ネットワーク計算は `NetworkBackend` 抽象に分離しています。コアのスコア計算はバックエンドへ依存せず、将来 `OsmnxBackend` から ArcGIS/arcpy ベースの `ArcpyBackend` へ差し替えられる設計です。

主な構成:

- `src/nmincity/config.py`: §6.3 のカテゴリ重み、§6.4 の時間パラメータ、§6.7 の質レイヤ設定
- `src/nmincity/backend/base.py`: 到達圏計算バックエンドの抽象クラス
- `src/nmincity/core/score.py`: 近接性スコア `S(i)`、質スコア `Q(i)`、任意統合スコア
- `src/nmincity/cli.py`: `python -m nmincity` の CLI スタブ

## マイルストーン

- M0b: スキャフォールド、設定、バックエンド抽象、スコア計算、テスト
- M1: osmnx/geopandas/networkx による到達圏とカテゴリ別到達度
- M2: 歩行環境の質レイヤ、クロノトピー、体験指標
- M3: 改善提案、可視化、感度分析
- M4: 最適配置などの追加検討

## テスト

```bash
python -m pytest -q
```
