"""プロジェクト全体の既定パラメータ."""

from __future__ import annotations


# §6.3 初期重み: 用途カテゴリ別の n分都市度スコア重み。
CATEGORY_NAMES: dict[str, str] = {
    "education": "学ぶ",
    "nature": "自然",
    "goods": "物資調達",
    "health": "医療・健康",
    "transit": "公共交通結節",
    "leisure": "娯楽・自己実現",
    "work": "仕事",
}

# §6.3 初期重み: 教育・自然を高めに置いた正規化済み重み。
CATEGORY_WEIGHTS: dict[str, float] = {
    "education": 0.18,
    "nature": 0.18,
    "goods": 0.15,
    "health": 0.14,
    "transit": 0.13,
    "leisure": 0.12,
    "work": 0.10,
}

# §6.3 重みの根拠: 各カテゴリ重みの設計意図と出典（先生指摘: 重みが正しいか
# 説明できるよう、事例・施策・できればマスタープランに基づく）。
# rationale/reference の本文は利用者が記入する想定で、ここでは骨組みのみ用意する。
# reference には大阪市総合計画・都市計画マスタープラン等の具体出典を入れる。
WEIGHT_RATIONALE: dict[str, dict[str, str]] = {
    "education": {
        "rationale": "子育て・生涯学習の基盤。15分都市の中核機能として高めに設定。",
        "reference": "（出典を記入: 例 大阪市総合計画 / こども・子育て支援計画）",
    },
    "nature": {
        "rationale": "緑とオープンスペースへの近接は健康・環境面で重要。高めに設定。",
        "reference": "（出典を記入: 例 大阪市みどりの基本計画）",
    },
    "goods": {
        "rationale": "日常の買い物（食料品）への近接。生活維持の必須機能。",
        "reference": "（出典を記入）",
    },
    "health": {
        "rationale": "医療・健康施設への近接。高齢化対応として重視。",
        "reference": "（出典を記入: 例 地域医療計画）",
    },
    "transit": {
        "rationale": "公共交通結節へのアクセス。広域移動の起点。",
        "reference": "（出典を記入: 例 都市計画マスタープラン 交通方針）",
    },
    "leisure": {
        "rationale": "娯楽・自己実現の場。生活の質に寄与。",
        "reference": "（出典を記入）",
    },
    "work": {
        "rationale": "職住近接。在宅・近接就労の広がりを踏まえやや低めに設定。",
        "reference": "（出典を記入）",
    },
}

# §6.4 時間基準: 徒歩速度、n分オプション、移動手段。
# 土地勘のある大阪の地区をメインに据える（先生指摘: 土地勘のある場所で見せる）。
# geocoding は Nominatim で要確認。区レベルの方が安定してヒットする。
DEFAULT_PLACE = "天王寺区, 大阪市, 大阪府, 日本"

# 複数地区の比較ビュー（compare-places）用。3つ目は後決めのため差し替え可能にしておく。
# いずれも Nominatim でのヒットを実行時に確認すること。
COMPARISON_PLACES: list[str] = [
    "天王寺区, 大阪市, 大阪府, 日本",  # ターミナル・高交通
    "住吉区, 大阪市, 大阪府, 日本",  # 杉本町（大阪公立大）周辺の住宅地
    "堺市南区, 大阪府, 日本",  # 泉北ニュータウン（計画郊外）
]
WALK_SPEED_KMH = 4.8
BIKE_SPEED_KMH = 15.0
N_MINUTES_OPTIONS = [5, 10, 15, 20]
MODES = ["walk", "bike"]
MODE_SPEED_KMH: dict[str, float] = {"walk": WALK_SPEED_KMH, "bike": BIKE_SPEED_KMH}

# osmnx 2.x ``features_from_place`` 用のカテゴリ別 OSM タグ。
CATEGORY_OSM_TAGS: dict[str, dict] = {
    "education": {"amenity": ["school", "kindergarten", "university", "college", "library"]},
    "nature": {
        "leisure": ["park", "garden"],
        "landuse": ["forest", "grass", "recreation_ground"],
        "natural": ["wood", "water"],
    },
    "goods": {
        "shop": [
            "supermarket",
            "convenience",
            "greengrocer",
            "bakery",
            "butcher",
            "department_store",
        ]
    },
    "health": {"amenity": ["hospital", "clinic", "doctors", "pharmacy", "dentist"]},
    "transit": {
        "railway": ["station"],
        "public_transport": ["station"],
        "highway": ["bus_stop"],
    },
    "leisure": {
        "amenity": ["cafe", "restaurant", "cinema", "theatre", "community_centre"],
        "leisure": ["sports_centre", "fitness_centre"],
    },
    "work": {"office": True, "amenity": ["coworking_space"]},
}

# §6.7 要素B: クロノトピー用の時間帯バケット。
TIME_OF_DAY = ["morning", "daytime", "evening"]

# §6.7 要素A: 歩行環境の質サブ指標。等重みを初期値にする。
WALK_QUALITY_WEIGHTS: dict[str, float] = {
    "sidewalk": 0.20,
    "traffic_separation": 0.20,
    "greenery": 0.20,
    "active_frontage": 0.20,
    "water_scenery": 0.20,
}

# §6.7 要素C: 体験指標の集約重み。代理指標のため感度分析対象にする。
EXPERIENTIAL_WEIGHTS: dict[str, float] = {
    "liveliness": 0.30,
    "lingering": 0.30,
    "topophilia": 0.25,
    "time_variation": 0.15,
}

# §6.7.1 Qトップレベル重み: 要素A集約(walkability)＋要素Cを統合、感度分析対象。
QUALITY_WEIGHTS: dict[str, float] = {
    "walkability": 0.40,
    "liveliness": 0.20,
    "lingering": 0.15,
    "topophilia": 0.15,
    "time_variation": 0.10,
}

# §6.7 要素A: 質による歩行インピーダンス補正。質0で歩行時間2倍。
IMPEDANCE_BETA: float = 1.0

# §6.7 要素A: 緑・沿道活動・水辺景観の近傍代理指標の半径(m)。
WALK_CONTEXT_RADIUS_M: float = 150.0

# §6.7 要素C: 体験指標。M0b では名称のみ定義する。
EXPERIENTIAL_INDICATORS = [
    "liveliness",
    "lingering",
    "topophilia",
    "time_variation",
]

# §6.7 要素B: 時間帯別の稼働度。開店・利用時間を近似する調整可能な代理値。
CATEGORY_TIME_AVAILABILITY: dict[str, dict[str, float]] = {
    "education": {"morning": 1.0, "daytime": 1.0, "evening": 0.2},
    "health": {"morning": 1.0, "daytime": 1.0, "evening": 0.3},
    "work": {"morning": 1.0, "daytime": 1.0, "evening": 0.3},
    "goods": {"morning": 0.6, "daytime": 1.0, "evening": 0.8},
    "leisure": {"morning": 0.4, "daytime": 0.8, "evening": 1.0},
    "nature": {"morning": 1.0, "daytime": 1.0, "evening": 0.7},
    "transit": {"morning": 1.0, "daytime": 1.0, "evening": 1.0},
}

# §6.7 要素B: モレノのクロノトピー(学校の多機能転換)に基づく、新設なし時間帯転換。
TIME_CONVERSIONS: dict[str, list[dict[str, float | str]]] = {
    "morning": [],
    "daytime": [],
    "evening": [{"source": "education", "target": "leisure", "factor": 0.7}],
}


def validate_weights(weights: dict[str, float] | None = None, *, tol: float = 1e-9) -> None:
    """重みが非負で、合計 1.0 であることを検証する."""

    target = CATEGORY_WEIGHTS if weights is None else weights
    if any(value < 0 for value in target.values()):
        raise ValueError("weights must be non-negative")
    total = sum(target.values())
    if abs(total - 1.0) > tol:
        raise ValueError(f"weights must sum to 1.0, got {total:.12f}")


def score_label(s: float) -> str:
    """§6.5 の評価しきい値に従い、スコアのラベルを返す."""

    if s >= 0.8:
        return "良好"
    if s >= 0.5:
        return "要改善"
    return "不足"


validate_weights(CATEGORY_WEIGHTS)
validate_weights(WALK_QUALITY_WEIGHTS)
validate_weights(EXPERIENTIAL_WEIGHTS)
validate_weights(QUALITY_WEIGHTS)
