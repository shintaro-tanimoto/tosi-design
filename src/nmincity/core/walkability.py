"""§6.7 要素A: 歩行環境の質を扱う純粋計算.

質レイヤは OSM タグや近傍 POI による代理指標であり、観察調査や実測の
代替ではない。要件定義書 §6.7 / §11 に従い、近接性 ``S`` と環境の質
``Q`` は既定では合成せず、並置して診断する。
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from nmincity.config import QUALITY_WEIGHTS
from nmincity.core.score import quality_score


def segment_indicators(tags: Mapping[str, Any]) -> dict[str, float]:
    """OSM way タグから街路区間のタグ由来サブ指標を 0..1 で返す.

    ``greenery`` / ``active_frontage`` / ``water_scenery`` は way タグだけでは
    算出せず、``nmincity.data.loader`` が近傍 POI から注入する。
    """

    highway = _text(_first(tags.get("highway")))
    sidewalk_tag = _text(_first(tags.get("sidewalk")))
    sidewalk = _sidewalk_score(highway, sidewalk_tag)

    width = _number(_first(tags.get("width")))
    if width is not None and width >= 3.0:
        sidewalk = max(sidewalk, 0.6)

    traffic = _traffic_separation_score(highway)
    maxspeed = _number(_first(tags.get("maxspeed")))
    if maxspeed is not None and maxspeed >= 50.0:
        traffic = min(traffic, 0.3)

    return {
        "sidewalk": _clamp_unit(sidewalk),
        "traffic_separation": _clamp_unit(traffic),
    }


def segment_quality(
    indicators: Mapping[str, float],
    weights: Mapping[str, float] | None = None,
) -> float:
    """街路区間の品質を ``quality_score`` で 0..1 に集約する."""

    return quality_score(indicators, QUALITY_WEIGHTS if weights is None else weights)


def impedance_factor(quality: float, beta: float) -> float:
    """質が低いほど大きくなる実効歩行時間の倍率を返す."""

    q = _clamp_unit(quality)
    b = max(0.0, float(beta))
    return 1.0 + b * (1.0 - q)


def effective_travel_time(base_seconds: float, quality: float, beta: float) -> float:
    """基礎歩行時間に質インピーダンスを掛けた実効歩行時間を返す."""

    return max(0.0, float(base_seconds)) * impedance_factor(quality, beta)


def origin_quality(
    graph: Any,
    reachable_node_set: set[Any],
    weights: Mapping[str, float] | None = None,
) -> float:
    """到達ノード集合が誘導する edge の平均指標から起点別 ``Q(i)`` を返す."""

    nodes = set(reachable_node_set)
    if len(nodes) < 2:
        return 0.0

    totals = {key: 0.0 for key in QUALITY_WEIGHTS}
    count = 0
    for u, v, data in _edge_data(graph):
        if u not in nodes or v not in nodes:
            continue
        indicators = _stored_indicators(data)
        for key in totals:
            totals[key] += indicators.get(key, 0.0)
        count += 1

    if count == 0:
        return 0.0
    averages = {key: value / count for key, value in totals.items()}
    return quality_score(averages, QUALITY_WEIGHTS if weights is None else weights)


def _sidewalk_score(highway: str, sidewalk: str) -> float:
    if highway in {"footway", "pedestrian", "path", "living_street"}:
        return 1.0
    if sidewalk == "both":
        return 1.0
    if sidewalk in {"left", "right", "yes", "separate"}:
        return 0.8
    if sidewalk in {"no", "none"}:
        return 0.2
    if highway == "residential":
        return 0.5
    if highway == "tertiary":
        return 0.4
    if highway in {"secondary", "primary", "trunk"}:
        return 0.2
    return 0.5


def _traffic_separation_score(highway: str) -> float:
    if highway in {"pedestrian", "footway", "path", "living_street"}:
        return 1.0
    if highway == "residential":
        return 0.7
    if highway == "tertiary":
        return 0.5
    if highway == "secondary":
        return 0.3
    if highway in {"primary", "trunk", "motorway"}:
        return 0.1
    return 0.5


def _stored_indicators(data: Mapping[str, Any]) -> dict[str, float]:
    raw = data.get("walk_indicators")
    if isinstance(raw, Mapping):
        return {key: _clamp_unit(_safe_float(raw.get(key, 0.0))) for key in QUALITY_WEIGHTS}
    return {
        key: _clamp_unit(_safe_float(data.get(f"q_{key}", 0.0)))
        for key in QUALITY_WEIGHTS
    }


def _edge_data(graph: Any):
    for edge in graph.edges(data=True, keys=True) if graph.is_multigraph() else graph.edges(data=True):
        if len(edge) == 4:
            u, v, _key, data = edge
        else:
            u, v, data = edge
        yield u, v, data


def _first(value: Any) -> Any:
    if isinstance(value, (list, tuple)):
        return value[0] if value else None
    return value


def _text(value: Any) -> str:
    return "" if value is None else str(value).strip().lower()


def _number(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        match = re.search(r"\d+(?:\.\d+)?", str(value))
        return float(match.group(0)) if match else None


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _clamp_unit(value: float) -> float:
    return max(0.0, min(1.0, float(value)))
