"""到達圏計算バックエンドの基底クラス."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class NetworkBackend(ABC):
    """ネットワーク到達圏計算を差し替えるための抽象基底クラス.

    M1 では OsmnxBackend、将来は ArcGIS Network Analyst を使う
    ArcpyBackend がこのインターフェースを実装する想定。
    """

    @abstractmethod
    def service_area(
        self,
        origin: Any,
        minutes: float,
        mode: str,
        weight: str = "travel_time",
    ) -> Any:
        """起点から指定分数で到達できる範囲を返す.

        Parameters
        ----------
        origin:
            起点。座標、ノードID、GISオブジェクトなど実装ごとの型を許容する。
        minutes:
            到達圏の時間しきい値（分）。
        mode:
            移動手段。例: ``"walk"`` または ``"bike"``。
        weight:
            到達圏計算に使う edge 重み。既定は通常歩行時間。

        Returns
        -------
        Any
            到達圏ジオメトリまたはノード集合。具体型はサブクラスで定義する。
        """

    @abstractmethod
    def reachable_categories(
        self,
        origin: Any,
        minutes: float,
        mode: str,
        weight: str = "travel_time",
    ) -> dict[str, bool]:
        """カテゴリ別到達度 ``a(i,c)`` を返す.

        返り値は ``category_slug -> bool`` の辞書で、1施設以上に到達できる場合
        ``True``、到達できない場合 ``False`` とする。
        """
