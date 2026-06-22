"""§6.7 要素B: クロノトピーを扱う純粋計算.

質レイヤは OSM タグや時間帯プロファイルによる代理指標であり、観察調査や
実測の代替ではない。近接性 ``S`` と環境の質 ``Q`` は既定では合成せず、
並置して診断する。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from nmincity.config import CATEGORY_TIME_AVAILABILITY, CATEGORY_WEIGHTS, TIME_CONVERSIONS
from nmincity.core.score import quality_score


def category_availability(
    category: str,
    time_bucket: str,
    availability: Mapping[str, Mapping[str, float]] | None = None,
) -> float:
    """カテゴリ ``category`` の時間帯 ``time_bucket`` における稼働度を返す."""

    selected = CATEGORY_TIME_AVAILABILITY if availability is None else availability
    value = selected.get(category, {}).get(time_bucket, 1.0)
    return _clamp_unit(value)


def reachable_categories_at(
    spatial_reach: Mapping[str, bool],
    time_bucket: str,
    *,
    availability: Mapping[str, Mapping[str, float]] | None = None,
    conversions: Mapping[str, Sequence[Mapping[str, Any]]] | None = None,
) -> dict[str, float]:
    """時間帯別到達度 ``a(i,c,t)`` を 0..1 で返す.

    ``spatial_reach`` は CLI や loader がネットワーク到達圏から作るカテゴリ別
    の空間到達判定で、この関数はグラフに触れない。
    """

    result = {
        category: (
            1.0 if bool(spatial_reach.get(category, False)) else 0.0
        )
        * category_availability(category, time_bucket, availability)
        for category in CATEGORY_WEIGHTS
    }

    selected_conversions = TIME_CONVERSIONS if conversions is None else conversions
    for conversion in selected_conversions.get(time_bucket, []):
        source = str(conversion.get("source", ""))
        target = str(conversion.get("target", ""))
        if target not in result or not bool(spatial_reach.get(source, False)):
            continue
        factor = _clamp_unit(_safe_float(conversion.get("factor", 0.0)))
        result[target] = max(result[target], factor)
    return result


def proximity_score_at(
    spatial_reach: Mapping[str, bool],
    time_bucket: str,
    weights: Mapping[str, float] | None = None,
    **kw: Any,
) -> float:
    """時間帯別近接性スコア ``S(i,t)=Σ w_c*a(i,c,t)`` を返す."""

    indicators = reachable_categories_at(spatial_reach, time_bucket, **kw)
    return quality_score(indicators, CATEGORY_WEIGHTS if weights is None else weights)


def time_variation(scores_by_bucket: Mapping[str, float]) -> float:
    """時間帯ごとのスコアの振れ幅を 0..1 で返す."""

    if not scores_by_bucket:
        return 0.0
    values = [_clamp_unit(value) for value in scores_by_bucket.values()]
    return _clamp_unit(max(values) - min(values))


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _clamp_unit(value: float) -> float:
    return max(0.0, min(1.0, float(value)))
