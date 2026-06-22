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
WALK_SPEED_KMH = 4.8
N_MINUTES_OPTIONS = [5, 10, 15, 20]
MODES = ["walk", "bike"]

# §6.7 要素B: クロノトピー用の時間帯バケット。
TIME_OF_DAY = ["morning", "daytime", "evening"]

# §6.7 要素A: 歩行環境の質サブ指標。M0b では等重みを初期値にする。
QUALITY_WEIGHTS: dict[str, float] = {
    "sidewalk": 0.20,
    "traffic_separation": 0.20,
    "greenery": 0.20,
    "active_frontage": 0.20,
    "water_scenery": 0.20,
}

# §6.7 要素C: 体験指標。M0b では名称のみ定義する。
EXPERIENTIAL_INDICATORS = [
    "liveliness",
    "lingering",
    "topophilia",
    "time_variation",
]


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
validate_weights(QUALITY_WEIGHTS)

