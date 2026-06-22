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
