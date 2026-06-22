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

# §6.4 時間基準: 徒歩速度、n分オプション、移動手段。
# MVP用の小さく歩ける地区。
DEFAULT_PLACE = "谷中, 台東区, 東京都, 日本"
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
