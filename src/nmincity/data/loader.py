"""OSM データを osmnx 2.x で読み込む処理."""

from __future__ import annotations

import math
import random
from typing import Any

import osmnx as ox

from nmincity.config import (
    CATEGORY_OSM_TAGS,
    IMPEDANCE_BETA,
    MODE_SPEED_KMH,
    WALK_QUALITY_WEIGHTS,
    WALK_CONTEXT_RADIUS_M,
)
from nmincity.core.walkability import (
    effective_travel_time,
    segment_indicators,
    segment_quality,
)


ox.settings.use_cache = True
ox.settings.log_console = False


def load_graph(place: str, mode: str):
    """対象地区のネットワークを取得し、各エッジに travel_time 秒を付与する."""

    if mode not in MODE_SPEED_KMH:
        raise ValueError(f"unsupported mode: {mode}")

    graph = ox.graph_from_place(place, network_type=mode)
    speed_mps = MODE_SPEED_KMH[mode] * 1000.0 / 3600.0
    for _u, _v, _k, data in graph.edges(keys=True, data=True):
        length = float(data.get("length", 0.0))
        data["travel_time"] = length / speed_mps
    return graph


def load_category_nodes(
    graph: Any,
    place: str,
    category_tags: dict[str, dict] | None = None,
) -> dict[str, set]:
    """カテゴリ別 POI を取得し、各 POI を最近傍グラフノードへ対応付ける."""

    tags_by_category = CATEGORY_OSM_TAGS if category_tags is None else category_tags
    result: dict[str, set] = {}

    for category, tags in tags_by_category.items():
        try:
            features = ox.features_from_place(place, tags)
            if features.empty or "geometry" not in features:
                result[category] = set()
                continue

            geometries = features.geometry.dropna()
            # 代表点は計量CRS(UTM)で重心を取り、lon/lat(EPSG:4326)へ戻す
            # （地理座標のまま centroid を取ると不正確 + 警告になるため）
            projected = geometries.to_crs(geometries.estimate_utm_crs())
            points = projected.centroid.to_crs(4326)
            lons: list[float] = []
            lats: list[float] = []
            for point in points:
                if point.is_empty:
                    continue
                lons.append(float(point.x))
                lats.append(float(point.y))
            if not lons:
                result[category] = set()
                continue

            nearest = ox.distance.nearest_nodes(graph, X=lons, Y=lats)
            if isinstance(nearest, (str, bytes)) or not hasattr(nearest, "__iter__"):
                nearest_nodes = {nearest}
            else:
                nearest_nodes = set(nearest)
            result[category] = nearest_nodes
        except Exception as exc:  # pragma: no cover - external OSM/geocoder failure path
            print(f"warning: failed to load OSM features for {category}: {exc}")
            result[category] = set()

    return result


def make_origins(graph: Any, sample: int | None = None) -> list:
    """評価起点ノード列を返す。sample 指定時は決定的に間引く."""

    nodes = list(graph.nodes)
    if sample is None or sample >= len(nodes):
        return nodes
    if sample <= 0:
        raise ValueError("sample must be positive")
    return random.Random(0).sample(nodes, sample)


def node_lonlat(graph: Any, node: Any) -> tuple[float, float]:
    """ノード座標を ``(lon, lat)`` で返す."""

    attrs = graph.nodes[node]
    lon = float(attrs["x"])
    lat = float(attrs["y"])
    if not math.isfinite(lon) or not math.isfinite(lat):
        raise ValueError(f"node has invalid coordinates: {node}")
    return lon, lat


def annotate_walkability(
    graph: Any,
    category_nodes: dict[str, set],
    *,
    beta: float | None = None,
    radius_m: float | None = None,
) -> None:
    """各 edge に歩行環境の質と実効歩行時間を in-place で付与する.

    文脈指標は近傍 POI からの代理指標であり、OSM データ欠損時は 0 として
    継続する。近接性 ``S`` と質 ``Q`` は既定では合成せず並置する。
    """

    selected_beta = IMPEDANCE_BETA if beta is None else beta
    selected_radius = WALK_CONTEXT_RADIUS_M if radius_m is None else radius_m
    nature_nodes = set(category_nodes.get("nature", set()))
    active_nodes = set(category_nodes.get("goods", set())) | set(category_nodes.get("leisure", set()))

    for u, v, data in _iter_edges(graph):
        indicators = segment_indicators(data)
        try:
            edge_nodes = [u, v]
            greenery = _proximity_indicator(graph, edge_nodes, nature_nodes, selected_radius)
            active_frontage = _proximity_indicator(graph, edge_nodes, active_nodes, selected_radius)
            # TODO: water 系地物を別カテゴリとして取得できるようにし、nature 流用を置き換える。
            water_scenery = _proximity_indicator(graph, edge_nodes, nature_nodes, selected_radius)
        except Exception:
            greenery = active_frontage = water_scenery = 0.0

        indicators.update(
            {
                "greenery": greenery,
                "active_frontage": active_frontage,
                "water_scenery": water_scenery,
            }
        )
        for key in WALK_QUALITY_WEIGHTS:
            indicators[key] = _clamp_unit(float(indicators.get(key, 0.0)))
            data[f"q_{key}"] = indicators[key]

        quality = segment_quality(indicators)
        data["walk_indicators"] = indicators
        data["walk_quality"] = quality
        data["eff_travel_time"] = effective_travel_time(
            float(data.get("travel_time", 0.0)),
            quality,
            selected_beta,
        )


def edge_quality_lines(graph: Any) -> list[tuple[list[tuple[float, float]], float]]:
    """可視化用に edge 形状 ``[(lat, lon), ...]`` と歩行品質を返す."""

    lines: list[tuple[list[tuple[float, float]], float]] = []
    for u, v, data in _iter_edges(graph):
        coords: list[tuple[float, float]] = []
        geometry = data.get("geometry")
        if geometry is not None and hasattr(geometry, "coords"):
            coords = [(float(lat), float(lon)) for lon, lat in geometry.coords]
        else:
            try:
                u_lon, u_lat = node_lonlat(graph, u)
                v_lon, v_lat = node_lonlat(graph, v)
                coords = [(u_lat, u_lon), (v_lat, v_lon)]
            except Exception:
                coords = []
        if len(coords) >= 2:
            lines.append((coords, _clamp_unit(float(data.get("walk_quality", 0.0)))))
    return lines


def origin_context(
    graph: Any,
    origin: Any,
    reachable_node_set: set[Any],
    category_nodes: dict[str, set],
    radius_m: float | None = None,
) -> dict[str, float]:
    """起点別の体験指標入力を 0..1 で返す.

    近傍 POI と到達 edge の歩行環境指標から作る代理値であり、観察調査や
    実測の代替ではない。
    """

    selected_radius = WALK_CONTEXT_RADIUS_M if radius_m is None else radius_m
    nodes = set(reachable_node_set)
    edge_context = _reachable_edge_context(graph, nodes)
    nature_nodes = set(category_nodes.get("nature", set()))
    leisure_nodes = set(category_nodes.get("leisure", set()))

    try:
        water_proximity = _proximity_indicator(graph, [origin], nature_nodes, selected_radius)
        leisure_proximity = _proximity_indicator(graph, [origin], leisure_nodes, selected_radius)
    except Exception:
        water_proximity = leisure_proximity = 0.0

    return {
        "active_frontage": edge_context.get("active_frontage", 0.0),
        "greenery": edge_context.get("greenery", 0.0),
        "water_proximity": max(edge_context.get("water_scenery", 0.0), water_proximity),
        "leisure_proximity": leisure_proximity,
    }


def _iter_edges(graph: Any):
    edges = graph.edges(keys=True, data=True) if graph.is_multigraph() else graph.edges(data=True)
    for edge in edges:
        if len(edge) == 4:
            u, v, _key, data = edge
        else:
            u, v, data = edge
        yield u, v, data


def _proximity_indicator(
    graph: Any,
    edge_nodes: list[Any],
    poi_nodes: set,
    radius_m: float,
) -> float:
    if radius_m <= 0 or not poi_nodes:
        return 0.0

    min_distance = math.inf
    for edge_node in edge_nodes:
        try:
            lon1, lat1 = node_lonlat(graph, edge_node)
        except Exception:
            continue
        for poi_node in poi_nodes:
            if poi_node not in graph.nodes:
                continue
            try:
                lon2, lat2 = node_lonlat(graph, poi_node)
            except Exception:
                continue
            min_distance = min(min_distance, _haversine_m(lat1, lon1, lat2, lon2))

    if not math.isfinite(min_distance):
        return 0.0
    return _clamp_unit(1.0 - min_distance / float(radius_m))


def _reachable_edge_context(graph: Any, nodes: set[Any]) -> dict[str, float]:
    if len(nodes) < 2:
        return {}

    totals = {"active_frontage": 0.0, "greenery": 0.0, "water_scenery": 0.0}
    count = 0
    for u, v, data in _iter_edges(graph):
        if u not in nodes or v not in nodes:
            continue
        indicators = data.get("walk_indicators")
        if not isinstance(indicators, dict):
            indicators = data
        for key in totals:
            totals[key] += _clamp_unit(_safe_float(indicators.get(key, data.get(f"q_{key}", 0.0))))
        count += 1

    if count == 0:
        return {}
    return {key: value / count for key, value in totals.items()}


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    return 2.0 * radius * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _clamp_unit(value: float) -> float:
    return max(0.0, min(1.0, float(value)))
