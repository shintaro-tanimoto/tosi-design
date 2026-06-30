# -*- coding: utf-8 -*-
"""ArcGIS Pro Python Toolbox for nmincity.

ArcGIS Pro の Python 環境で ``pip install -e .`` して使うことを推奨する。
未インストールの clone から読み込む場合に備え、隣接する ``../src`` を
``sys.path`` へ追加するフォールバックを持つ。
"""

from __future__ import annotations

import inspect
import sys
from pathlib import Path

import arcpy


def _this_file() -> Path:
    """`.pyt` 読み込み時は ``__file__`` が未定義のことがあるため、
    現在フレームのソースファイル名から自身のパスを解決する。"""
    try:
        return Path(__file__).resolve()
    except NameError:
        return Path(inspect.getfile(inspect.currentframe())).resolve()


_ROOT = _this_file().parents[1]
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


from nmincity.config import CATEGORY_NAMES, CATEGORY_WEIGHTS, CATEGORY_OSM_TAGS, score_label  # noqa: E402
from nmincity.core.score import proximity_score  # noqa: E402
from nmincity.backend.arcpy_backend import ArcpyBackend  # noqa: E402


class Toolbox:
    def __init__(self):
        self.label = "n分都市化支援ツール"
        self.alias = "nmincity"
        self.tools = [DownloadOSMFacilities, DiagnoseProximity]


class DownloadOSMFacilities:
    """OSM から施設データを自動ダウンロードして Feature Class を作成する."""

    label = "OSM施設データ自動取得"
    description = "OpenStreetMap から各カテゴリの施設データを取得し、ジオデータベースに Feature Class として保存します。出力 FC を「近接性スコア診断」の各施設 FC に指定してください。"
    canRunInBackground = False

    def getParameterInfo(self):
        place_param = arcpy.Parameter(
            displayName="地区名 (Nominatim形式)",
            name="place",
            datatype="GPString",
            parameterType="Required",
            direction="Input",
        )
        place_param.value = "谷中, 台東区, 東京都, 日本"

        gdb_param = arcpy.Parameter(
            displayName="出力ジオデータベース",
            name="out_gdb",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input",
        )
        gdb_param.filter.list = ["Local Database", "Remote Database"]

        folder_param = arcpy.Parameter(
            displayName="フォルダー名 (GDB 内に新規作成)",
            name="dataset_name",
            datatype="GPString",
            parameterType="Required",
            direction="Input",
        )
        folder_param.value = "OSM_施設"

        radius_param = arcpy.Parameter(
            displayName="フォールバック半径 (m) ※地区名がポイント認識された場合に使用",
            name="fallback_radius_m",
            datatype="GPDouble",
            parameterType="Optional",
            direction="Input",
        )
        radius_param.value = 1000

        return [place_param, gdb_param, folder_param, radius_param]

    def execute(self, parameters, messages):
        place = parameters[0].valueAsText
        out_gdb = parameters[1].valueAsText
        dataset_name = parameters[2].valueAsText.strip()
        fallback_radius_m = float(parameters[3].value or 1000)

        try:
            import osmnx as ox
        except ImportError:
            arcpy.AddError(
                "osmnx がインストールされていません。"
                " ArcGIS Pro の Python 環境で「pip install osmnx」を実行してください。"
            )
            return

        sr = arcpy.SpatialReference(4326)

        fd_path = f"{out_gdb}\\{dataset_name}"
        if arcpy.Exists(fd_path):
            arcpy.AddMessage(f"フォルダー '{dataset_name}' は既に存在します。既存フォルダーに追加します。")
        else:
            arcpy.management.CreateFeatureDataset(out_gdb, dataset_name, sr)
            arcpy.AddMessage(f"フォルダー '{dataset_name}' を作成しました。")

        created: list[str] = []

        for category, tags in CATEGORY_OSM_TAGS.items():
            cat_label = CATEGORY_NAMES.get(category, category)
            arcpy.AddMessage(f"{cat_label} ({category}) を OSM から取得しています...")

            try:
                features = _fetch_osm_features(ox, place, tags, fallback_radius_m, arcpy)
            except Exception as exc:
                arcpy.AddWarning(f"  {cat_label}: OSM 取得に失敗しました ({exc})")
                continue

            if features is None or features.empty:
                arcpy.AddWarning(f"  {cat_label}: データが見つかりませんでした。")
                continue

            geometries = features.geometry.dropna()
            try:
                utm_crs = geometries.estimate_utm_crs()
                points = geometries.to_crs(utm_crs).centroid.to_crs(4326)
            except Exception as exc:
                arcpy.AddWarning(f"  {cat_label}: 座標変換に失敗しました ({exc})")
                continue

            coords = [(float(p.x), float(p.y)) for p in points if not p.is_empty]
            if not coords:
                arcpy.AddWarning(f"  {cat_label}: 有効なジオメトリがありませんでした。")
                continue

            fc_name = f"osm_{category}"
            fc_path = f"{fd_path}\\{fc_name}"

            try:
                if arcpy.Exists(fc_path):
                    arcpy.management.Delete(fc_path)
                arcpy.management.CreateFeatureclass(
                    fd_path, fc_name, "POINT", spatial_reference=sr
                )
                with arcpy.da.InsertCursor(fc_path, ["SHAPE@XY"]) as cursor:
                    for xy in coords:
                        cursor.insertRow([xy])

                count = int(arcpy.management.GetCount(fc_path).getOutput(0))
                arcpy.AddMessage(f"  → {count} 件を保存: {fc_path}")
                created.append(fc_path)
            except Exception as exc:
                arcpy.AddWarning(f"  {cat_label}: Feature Class の作成に失敗しました ({exc})")

        arcpy.AddMessage("")
        arcpy.AddMessage("=== 完了 ===")
        arcpy.AddMessage("以下の FC を「近接性スコア診断」の各施設 FC に指定してください:")
        for path in created:
            arcpy.AddMessage(f"  {path}")


class DiagnoseProximity:
    """機能A: 評価起点ごとに近接性スコア S を算出する."""

    label = "近接性スコア診断 (機能A)"
    description = "Network Analyst の到達圏からカテゴリ別到達度と近接性スコア S を出力します。"
    canRunInBackground = False

    def getParameterInfo(self):
        params = [
            arcpy.Parameter(
                displayName="Network Dataset",
                name="network_dataset",
                datatype="DENetworkDataset",
                parameterType="Required",
                direction="Input",
            ),
            arcpy.Parameter(
                displayName="評価起点 Feature Class",
                name="origins_fc",
                datatype="GPFeatureLayer",
                parameterType="Required",
                direction="Input",
            ),
            arcpy.Parameter(
                displayName="n分",
                name="minutes",
                datatype="GPDouble",
                parameterType="Required",
                direction="Input",
            ),
            arcpy.Parameter(
                displayName="移動手段",
                name="mode",
                datatype="GPString",
                parameterType="Required",
                direction="Input",
            ),
            arcpy.Parameter(
                displayName="出力 Feature Class",
                name="out_fc",
                datatype="DEFeatureClass",
                parameterType="Required",
                direction="Output",
            ),
        ]
        params[2].value = 15
        params[3].filter.type = "ValueList"
        params[3].filter.list = ["walk", "bike"]
        params[3].value = "walk"

        for category, label in CATEGORY_NAMES.items():
            params.append(
                arcpy.Parameter(
                    displayName=f"{label} 施設 Feature Class ({category})",
                    name=f"{category}_fc",
                    datatype="GPFeatureLayer",
                    parameterType="Optional",
                    direction="Input",
                )
            )
        return params

    def execute(self, parameters, messages):
        network_dataset = parameters[0].valueAsText
        origins_fc = parameters[1].valueAsText
        minutes = float(parameters[2].value)
        mode = parameters[3].valueAsText
        out_fc = parameters[4].valueAsText

        category_layers = {}
        for index, category in enumerate(CATEGORY_WEIGHTS, start=5):
            value = parameters[index].valueAsText
            if value:
                category_layers[category] = value

        arcpy.AddMessage("ArcpyBackend を初期化しています。")
        backend = ArcpyBackend(network_dataset, category_layers)

        arcpy.AddMessage("評価起点をコピーしています。")
        arcpy.management.CopyFeatures(origins_fc, out_fc)
        _ensure_field(out_fc, "S", "DOUBLE")
        _ensure_field(out_fc, "label", "TEXT", field_length=16)
        # カテゴリ別の到達(0/1)も出力する。ローカルの可視化(compare-gdb の
        # 7要素到達率レーダー / viz-gdb の到達率チャート)が .gdb だけで作れるようにする。
        reach_fields = [f"reach_{category}" for category in CATEGORY_WEIGHTS]
        for field_name in reach_fields:
            _ensure_field(out_fc, field_name, "SHORT")

        scores = {}
        labels = {}
        reaches: dict[object, dict[str, bool]] = {}
        total = int(arcpy.management.GetCount(out_fc).getOutput(0))
        arcpy.AddMessage(f"{total} 件の評価起点を診断します。")

        with arcpy.da.SearchCursor(out_fc, ["OID@", "SHAPE@"]) as cursor:
            for row_number, (oid, geometry) in enumerate(cursor, start=1):
                reach = backend.reachable_categories(geometry, minutes, mode)
                score = proximity_score(reach)
                scores[oid] = score
                labels[oid] = score_label(score)
                reaches[oid] = reach
                if row_number == 1 or row_number % 10 == 0 or row_number == total:
                    arcpy.AddMessage(f"{row_number}/{total} 件を処理しました。")

        with arcpy.da.UpdateCursor(out_fc, ["OID@", "S", "label", *reach_fields]) as cursor:
            for row in cursor:
                oid = row[0]
                reach = reaches.get(oid, {})
                reach_values = [int(bool(reach.get(category, False))) for category in CATEGORY_WEIGHTS]
                cursor.updateRow([oid, scores.get(oid), labels.get(oid, "不足"), *reach_values])

        arcpy.AddMessage("近接性スコア診断が完了しました。")


def _fetch_osm_features(ox, place, tags, fallback_radius_m, arcpy):
    """features_from_place を試み、ポリゴン未解決時は地点+半径にフォールバックする."""
    try:
        return ox.features_from_place(place, tags)
    except Exception as exc:
        if "Polygon" not in str(exc):
            raise
        arcpy.AddMessage(
            f"  地区名がポリゴンとして認識されませんでした。"
            f" 地点 + {fallback_radius_m:.0f}m 半径で再取得します。"
        )
        lat, lon = ox.geocode(place)
        return ox.features_from_point((lat, lon), tags, dist=fallback_radius_m)


def _ensure_field(feature_class, field_name, field_type, field_length=None):
    existing = {field.name for field in arcpy.ListFields(feature_class)}
    if field_name in existing:
        return
    kwargs = {}
    if field_length is not None:
        kwargs["field_length"] = field_length
    arcpy.management.AddField(feature_class, field_name, field_type, **kwargs)


# TODO: reach_by_origin を作れば、proposals/allocation の純関数も同様に
# ArcGIS Pro ツール化できる。
