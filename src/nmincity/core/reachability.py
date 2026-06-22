"""ネットワーク上のカテゴリ別到達度を計算する純粋ロジック."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import networkx as nx

from nmincity.config import CATEGORY_WEIGHTS


def reachable_nodes(
    graph: nx.Graph,
    origin: Any,
    cutoff_seconds: float,
    weight: str = "travel_time",
) -> set[Any]:
    """起点から指定秒数以内に到達できるノード集合を返す.

    ``networkx.single_source_dijkstra_path_length`` は距離 0 の起点を含むため、
    返り値も常に ``origin`` を含む。
    """

    lengths = nx.single_source_dijkstra_path_length(
        graph,
        origin,
        cutoff=float(cutoff_seconds),
        weight=weight,
    )
    return set(lengths)


def reachable_categories(
    graph: nx.Graph,
    origin: Any,
    cutoff_seconds: float,
    category_nodes: Mapping[str, set[Any]],
    weight: str = "travel_time",
) -> dict[str, bool]:
    """カテゴリ別到達度 ``a(i,c)`` を返す.

    要件定義書 §6.5 / 機能Aの ``a(i,c)`` に対応する二値判定で、起点
    ``i`` から n分圏内にカテゴリ ``c`` の施設ノードが1つ以上あれば
    ``True``、なければ ``False`` とする。到達ノード集合は一度だけ計算する。
    """

    nodes = reachable_nodes(graph, origin, cutoff_seconds, weight=weight)
    categories = set(CATEGORY_WEIGHTS) | set(category_nodes)
    return {
        category: bool(nodes & set(category_nodes.get(category, set())))
        for category in categories
    }
