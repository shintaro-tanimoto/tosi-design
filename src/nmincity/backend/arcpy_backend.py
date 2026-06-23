"""ArcGIS Pro Network Analyst を使う到達圏バックエンド.

このモジュールは ArcGIS Pro 3.x の ``arcpy.nax`` を使う実装を提供する。
``arcpy`` は ArcGIS Pro 同梱の Windows 専用ライセンス製品であり、
Linux や通常の Python 環境では実行できない。パッケージ全体の import と
自動テストを壊さないため、``arcpy`` はコンストラクタまたはメソッド内で
遅延 import する。

実際の動作確認には ArcGIS Pro と Network Analyst エクステンション、
徒歩/自転車の Travel Mode を持つ Network Dataset が必要。
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from nmincity.backend.base import NetworkBackend
from nmincity.config import CATEGORY_WEIGHTS


def _arcpy() -> Any:
    """遅延 import した ``arcpy`` モジュールを返す."""

    try:
        import arcpy  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover - arcpy 非導入環境での説明用
        raise RuntimeError(
            "ArcpyBackend の実行には ArcGIS Pro の arcpy が必要です。"
            " ArcGIS Pro の Python 環境で実行してください。"
        ) from exc
    return arcpy


class ArcpyBackend(NetworkBackend):
    """ArcGIS Pro ``arcpy.nax`` による ``NetworkBackend`` 実装.

    スコア計算は行わず、カテゴリ別到達度 ``a(i,c)`` だけを返す。
    近接性スコア ``S`` は既存の ``nmincity.core.score`` に委ねる。
    """

    def __init__(
        self,
        network_dataset: str,
        category_layers: dict[str, str],
        *,
        travel_modes: dict[str, str] | None = None,
        spatial_reference: int = 4326,
    ) -> None:
        """Network Dataset とカテゴリ別施設レイヤを受け取る.

        ``travel_modes`` の既定値は一般的な名前であり、実際に利用できる
        Travel Mode 名は Network Dataset の設定に依存する。
        """

        arcpy = _arcpy()
        status = arcpy.CheckExtension("network")
        if status != "Available":
            raise RuntimeError(
                "ArcGIS Network Analyst エクステンションが利用できません "
                f"(CheckExtension('network')={status!r})。"
            )
        arcpy.CheckOutExtension("network")

        self.network_dataset = network_dataset
        self.category_layers = dict(category_layers)
        self.travel_modes = travel_modes or {
            "walk": "Walking Time",
            "bike": "Cycling Time",
        }
        self.spatial_reference = spatial_reference
        self._arc = arcpy

    def service_area(
        self,
        origin: Any,
        minutes: float,
        mode: str,
        weight: str = "travel_time",
    ) -> Any:
        """起点から ``minutes`` 分以内の到達圏ポリゴンを返す.

        ``origin`` は ``(lon, lat)`` タプルまたは ``arcpy.PointGeometry`` を
        受け付ける。``weight`` は抽象 IF 互換の引数で、ArcGIS 版では
        Network Dataset の Travel Mode に委ねる。
        """

        _ = weight
        arcpy = self._arc
        point = self._to_point(origin)
        travel_mode = self._travel_mode(mode)

        solver = arcpy.nax.ServiceArea(self.network_dataset)
        solver.travelMode = travel_mode
        solver.timeUnits = arcpy.nax.TimeUnits.Minutes
        solver.defaultImpedanceCutoffs = [float(minutes)]
        solver.outputType = arcpy.nax.ServiceAreaOutputType.Polygons
        solver.geometryAtOverlap = arcpy.nax.ServiceAreaOverlapGeometry.Split

        facilities_fc = self._make_origin_fc(point)
        polygons_fc = f"in_memory/nmincity_sa_{uuid4().hex}"
        try:
            solver.load(arcpy.nax.ServiceAreaInputDataType.Facilities, facilities_fc)
            result = solver.solve()
            if not result.solveSucceeded:
                messages = result.solverMessages(arcpy.nax.MessageSeverity.All)
                raise RuntimeError(f"ServiceArea の解析に失敗しました: {messages}")

            result.export(arcpy.nax.ServiceAreaOutputDataType.Polygons, polygons_fc)
            polygons = [row[0] for row in arcpy.da.SearchCursor(polygons_fc, ["SHAPE@"])]
            if not polygons:
                raise RuntimeError("ServiceArea の解析結果にポリゴンがありません。")
            if len(polygons) == 1:
                return polygons[0]

            merged = polygons[0]
            for polygon in polygons[1:]:
                merged = merged.union(polygon)
            return merged
        finally:
            for dataset in (facilities_fc, polygons_fc):
                try:
                    if arcpy.Exists(dataset):
                        arcpy.management.Delete(dataset)
                except Exception:
                    pass

    def reachable_categories(
        self,
        origin: Any,
        minutes: float,
        mode: str,
        weight: str = "travel_time",
    ) -> dict[str, bool]:
        """カテゴリ別到達度 ``a(i,c)`` を返す.

        全 ``CATEGORY_WEIGHTS`` キーを含む辞書を返す。施設レイヤ未指定、
        空レイヤ、空間検索エラーのカテゴリは ``False`` として扱う。
        """

        arcpy = self._arc
        try:
            polygon = self.service_area(origin, minutes, mode, weight=weight)
        except Exception:
            return {category: False for category in CATEGORY_WEIGHTS}

        reach: dict[str, bool] = {}
        for category in CATEGORY_WEIGHTS:
            source = self.category_layers.get(category)
            if not source:
                reach[category] = False
                continue
            # SelectLayerByLocation はレイヤ/テーブルビューを要求するため、
            # FeatureClass パスが渡されても確実に動くよう一時レイヤ化する。
            layer_name = f"nmincity_cat_{uuid4().hex}"
            try:
                arcpy.management.MakeFeatureLayer(source, layer_name)
                selected = arcpy.management.SelectLayerByLocation(
                    layer_name,
                    "INTERSECT",
                    polygon,
                    selection_type="NEW_SELECTION",
                )
                count = int(arcpy.management.GetCount(selected).getOutput(0))
                reach[category] = count > 0
            except Exception:
                reach[category] = False
            finally:
                try:
                    if arcpy.Exists(layer_name):
                        arcpy.management.Delete(layer_name)
                except Exception:
                    pass
        return reach

    def _to_point(self, origin: Any) -> Any:
        """``(lon, lat)`` または ArcPy geometry を ``PointGeometry`` に揃える."""

        arcpy = self._arc
        if origin.__class__.__name__ == "PointGeometry":
            return origin
        if hasattr(origin, "centroid"):
            centroid = origin.centroid
            return arcpy.PointGeometry(
                arcpy.Point(centroid.X, centroid.Y),
                arcpy.SpatialReference(self.spatial_reference),
            )
        if isinstance(origin, (tuple, list)) and len(origin) == 2:
            lon, lat = origin
            return arcpy.PointGeometry(
                arcpy.Point(float(lon), float(lat)),
                arcpy.SpatialReference(self.spatial_reference),
            )
        raise TypeError("origin は (lon, lat) または arcpy.PointGeometry を指定してください。")

    def _travel_mode(self, mode: str) -> Any:
        arcpy = self._arc
        mode_name = self.travel_modes.get(mode, mode)
        modes = arcpy.nax.GetTravelModes(self.network_dataset)
        try:
            return modes[mode_name]
        except KeyError as exc:
            available = ", ".join(sorted(modes.keys()))
            raise RuntimeError(
                f"Travel Mode {mode_name!r} が Network Dataset に見つかりません。"
                f" 利用可能: {available}"
            ) from exc

    def _make_origin_fc(self, point: Any) -> str:
        arcpy = self._arc
        name = f"nmincity_origin_{uuid4().hex}"
        workspace = "in_memory"
        arcpy.management.CreateFeatureclass(
            workspace,
            name,
            "POINT",
            spatial_reference=arcpy.SpatialReference(self.spatial_reference),
        )
        fc = f"{workspace}/{name}"
        with arcpy.da.InsertCursor(fc, ["SHAPE@"]) as cursor:
            cursor.insertRow([point])
        return fc
