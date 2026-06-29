# -*- coding: utf-8 -*-
r"""既存の RoadLinks から Network Dataset の「構築」だけを行うスクリプト。

create_network_dataset.py がエッジ作成（RoadLinks ＋ Walk_Min/Bike_Min）まで
完了し、Network Dataset 本体が未構築のまま止まった場合の続きを実行する。
304 万エッジの再マージ・フィールド再計算はスキップする。

【実行環境】
  ★ ADF_Network.gdb を開いている ArcGIS Pro の「Python ウィンドウ」で実行すること。
    （GDB が Pro にロックされているため、外部 Python からは実行できない）

【実行例】ArcGIS Pro の Python ウィンドウに以下を貼り付け:
  exec(open(r"C:\Users\SinfoLab\Desktop\tosi-design\tosi-design\arcgis\build_nd_only.py", encoding="utf-8").read())
"""
from __future__ import annotations

import sys
from pathlib import Path

import arcpy

_HERE = Path(r"C:\Users\SinfoLab\Desktop\tosi-design\tosi-design\arcgis")
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import create_network_dataset as cnd  # noqa: E402


def main() -> None:
    status = arcpy.CheckExtension("network")
    if status != "Available":
        sys.exit(f"Network Analyst ライセンスが利用できません: {status}")
    arcpy.CheckOutExtension("network")
    arcpy.env.overwriteOutput = True

    fd_path = str(cnd.OUTPUT_GDB / cnd.FD_NAME)
    nd_path = f"{fd_path}/{cnd.ND_NAME}"
    edge_fc = f"{fd_path}/{cnd.EDGE_FC_NAME}"

    if not arcpy.Exists(edge_fc):
        sys.exit(f"エッジ {edge_fc} が見つかりません。先に create_network_dataset.py を実行してください。")
    if arcpy.Exists(nd_path):
        print(f"Network Dataset は既に存在します: {nd_path}")
        print("再構築する場合は ArcGIS Pro 上で削除してから実行してください。")
        return

    print("RoadLinks を再利用して Network Dataset を構築します（再マージなし）。")
    cnd._create_nd(arcpy, fd_path, nd_path)
    cnd._configure_via_template(arcpy, nd_path, fd_path)

    print("\n" + "=" * 60)
    print("完了。Travel Mode を確認します:")
    try:
        modes = arcpy.nax.GetTravelModes(nd_path)
        print("  利用可能 Travel Mode:", list(modes.keys()))
    except Exception as exc:
        print("  Travel Mode 取得に失敗:", exc)
    print(f"Network Dataset: {nd_path}")


if __name__ == "__main__":
    main()
else:
    main()
