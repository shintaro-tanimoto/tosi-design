# -*- coding: utf-8 -*-
"""ArcGIS Pro Python Toolbox for nmincity.

ArcGIS Pro の Python 環境で ``pip install -e .`` して使うことを推奨する。
未インストールの clone から読み込む場合に備え、隣接する ``../src`` を
``sys.path`` へ追加するフォールバックを持つ。
"""

from __future__ import annotations

import sys
from pathlib import Path

import arcpy


_ROOT = Path(__file__).resolve().parents[1]
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


from nmincity.config import CATEGORY_NAMES, CATEGORY_WEIGHTS, score_label  # noqa: E402
from nmincity.core.score import proximity_score  # noqa: E402
from nmincity.backend.arcpy_backend import ArcpyBackend  # noqa: E402


class Toolbox:
    def __init__(self):
        self.label = "n分都市化支援ツール"
        self.alias = "nmincity"
        self.tools = [DiagnoseProximity]


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

        scores = {}
        labels = {}
        total = int(arcpy.management.GetCount(out_fc).getOutput(0))
        arcpy.AddMessage(f"{total} 件の評価起点を診断します。")

        with arcpy.da.SearchCursor(out_fc, ["OID@", "SHAPE@"]) as cursor:
            for row_number, (oid, geometry) in enumerate(cursor, start=1):
                reach = backend.reachable_categories(geometry, minutes, mode)
                score = proximity_score(reach)
                scores[oid] = score
                labels[oid] = score_label(score)
                if row_number == 1 or row_number % 10 == 0 or row_number == total:
                    arcpy.AddMessage(f"{row_number}/{total} 件を処理しました。")

        with arcpy.da.UpdateCursor(out_fc, ["OID@", "S", "label"]) as cursor:
            for oid, _score, _label in cursor:
                cursor.updateRow([oid, scores.get(oid), labels.get(oid, "不足")])

        arcpy.AddMessage("近接性スコア診断が完了しました。")


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
