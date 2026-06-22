"""osmnx 取得済みグラフを使う到達圏バックエンド."""

from __future__ import annotations

from typing import Any

from nmincity.backend.base import NetworkBackend
from nmincity.core.reachability import reachable_categories, reachable_nodes


class OsmnxBackend(NetworkBackend):
    """NetworkBackend の osmnx/networkx 実装.

    データ取得は ``nmincity.data.loader`` が担当し、このクラスは取得済み
    グラフ上の計算だけを扱う。将来は ArcpyBackend が同じ IF を実装する。
    """

    def __init__(self, graph: Any, category_nodes: dict[str, set], mode: str = "walk") -> None:
        self.graph = graph
        self.category_nodes = category_nodes
        self.mode = mode

    def service_area(
        self,
        origin: Any,
        minutes: float,
        mode: str,
        weight: str = "travel_time",
    ) -> set:
        """起点から ``minutes`` 分以内に到達できるノード集合を返す."""

        _ = mode
        return reachable_nodes(self.graph, origin, float(minutes) * 60.0, weight=weight)

    def reachable_categories(
        self,
        origin: Any,
        minutes: float,
        mode: str,
        weight: str = "travel_time",
    ) -> dict[str, bool]:
        """カテゴリ別到達度 ``a(i,c)`` を返す."""

        _ = mode
        return reachable_categories(
            self.graph,
            origin,
            float(minutes) * 60.0,
            self.category_nodes,
            weight=weight,
        )
