"""OSM データを osmnx 2.x で読み込む処理."""

from __future__ import annotations

import math
import random
from typing import Any

import osmnx as ox

from nmincity.config import CATEGORY_OSM_TAGS, MODE_SPEED_KMH


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
