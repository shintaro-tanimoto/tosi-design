# -*- coding: utf-8 -*-
r"""
ADF (拡張全国デジタル道路地図データベース標準) SHP から
ArcGIS Pro Network Dataset を作成するスクリプト。

【実行環境】
  ArcGIS Pro 3.x の Python 環境 (arcpy + Network Analyst ライセンス)

【実行例】
  exec(open(r"...\arcgis\create_network_dataset.py", encoding="utf-8").read())

【出力 Network Dataset パス】
  C:\Users\SinfoLab\Documents\データセット\道路データ\ADF_Network.gdb\RoadNetwork\RoadNetwork_ND
"""
from __future__ import annotations

import os
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

# ---------- 設定 ----------
SHP_ROOT = Path(r"C:\Users\SinfoLab\Documents\データセット\道路データ\900014202302\SHP_230101G")
OUTPUT_GDB = Path(r"C:\Users\SinfoLab\Documents\データセット\道路データ\ADF_Network.gdb")
FD_NAME = "RoadNetwork"
EDGE_FC_NAME = "RoadLinks"
ND_NAME = "RoadNetwork_ND"

WALK_SPEED_MPM = 5_000 / 60
BIKE_SPEED_MPM = 15_000 / 60

_RDCLASS_SPEED_KMH: dict[str, int] = {
    "1": 100, "2": 80, "3": 60,
    "4": 50,  "5": 40, "6": 30,
    "7": 80,  "9": 30,
}
_HIGHWAY_RDCLASS = {"1", "2"}


def main() -> None:
    try:
        import arcpy  # type: ignore[import-not-found]
    except ImportError:
        sys.exit("arcpy が見つかりません。ArcGIS Pro の Python 環境で実行してください。")

    status = arcpy.CheckExtension("network")
    if status != "Available":
        sys.exit(f"Network Analyst ライセンスが利用できません: {status}")
    arcpy.CheckOutExtension("network")
    arcpy.env.overwriteOutput = True

    fd_path, nd_path, edge_fc = _setup_gdb(arcpy)
    _merge_links(arcpy, edge_fc)
    _add_impedance_fields(arcpy, edge_fc)
    _create_nd(arcpy, fd_path, nd_path)
    _configure_via_template(arcpy, nd_path, fd_path)

    print(f"\n{'='*60}")
    print("完了")
    print(f"Network Dataset: {nd_path}")
    print(f"\nArcpyBackend への設定例:")
    print(f"  ArcpyBackend(network_dataset=r'{nd_path}', ...)")


# ------------------------------------------------------------------ #
#  内部実装
# ------------------------------------------------------------------ #

def _setup_gdb(arcpy) -> tuple[str, str, str]:
    print("\n[1/5] GDB + Feature Dataset を作成...")
    if arcpy.Exists(str(OUTPUT_GDB)):
        arcpy.management.Delete(str(OUTPUT_GDB))
    arcpy.management.CreateFileGDB(str(OUTPUT_GDB.parent), OUTPUT_GDB.name)
    sr = arcpy.SpatialReference(6668)
    arcpy.management.CreateFeatureDataset(str(OUTPUT_GDB), FD_NAME, sr)
    fd_path = str(OUTPUT_GDB / FD_NAME)
    print(f"  GDB    : {OUTPUT_GDB}")
    print(f"  Feature Dataset: {fd_path}")
    return fd_path, f"{fd_path}/{ND_NAME}", f"{fd_path}/{EDGE_FC_NAME}"


def _merge_links(arcpy, edge_fc: str) -> None:
    print("\n[2/5] 全メッシュ _32.shp をマージ...")
    link_shps = sorted(SHP_ROOT.rglob("*_32.shp"))
    if not link_shps:
        sys.exit(f"_32.shp が見つかりません: {SHP_ROOT}")
    print(f"  {len(link_shps)} ファイルを検出")
    arcpy.management.Merge([str(p) for p in link_shps], edge_fc)
    n = int(arcpy.management.GetCount(edge_fc)[0])
    print(f"  マージ完了: {n:,} エッジ")


def _add_impedance_fields(arcpy, edge_fc: str) -> None:
    print("\n[3/5] 移動時間フィールドを追加・計算...")
    for fname, alias in [
        ("Walk_Min", "徒歩所要時間(分)"),
        ("Bike_Min", "自転車所要時間(分)"),
        ("Car_Min",  "自動車所要時間(分)"),
    ]:
        arcpy.management.AddField(edge_fc, fname, "DOUBLE", field_alias=alias)

    arcpy.management.CalculateField(
        edge_fc, "Walk_Min",
        f"float(!length!) / {WALK_SPEED_MPM:.8f}", "PYTHON3",
    )
    arcpy.management.CalculateField(
        edge_fc, "Bike_Min",
        f"float(!length!) / {BIKE_SPEED_MPM:.8f}", "PYTHON3",
    )
    speed_map_repr = repr(_RDCLASS_SPEED_KMH)
    arcpy.management.CalculateField(
        edge_fc, "Car_Min",
        f"float(!length!) / ({speed_map_repr}.get(str(!rdclasscd!).strip(), 30) * 1000 / 60)",
        "PYTHON3",
    )
    print("  Walk_Min / Bike_Min / Car_Min 計算完了")


def _create_nd(arcpy, fd_path: str, nd_path: str) -> None:
    print("\n[4/5] Network Dataset を作成...")
    arcpy.na.CreateNetworkDataset(
        feature_dataset=fd_path,
        out_name=ND_NAME,
        source_feature_class_names=[EDGE_FC_NAME],
        elevation_model="NO_ELEVATION",
    )
    print(f"  作成完了: {nd_path}")


def _configure_via_template(arcpy, nd_path: str, fd_path: str) -> None:
    """ArcGIS Pro 3.x: テンプレート XML を経由してネットワーク属性を設定する。

    AddNetworkAttribute / SetNetworkFieldEvaluator は ArcGIS Pro 3.x に存在しないため、
    CreateTemplateFromNetworkDataset → XML 編集 → CreateNetworkDatasetFromTemplate の
    フローで属性と Travel Mode を設定する。失敗した場合は基本ビルドのみ実施し、
    手動設定の手順を案内する。
    """
    print("\n[5/5] ネットワーク属性・Travel Mode をテンプレート経由で設定...")

    create_tpl_fn = getattr(arcpy.na, "CreateTemplateFromNetworkDataset", None)
    from_tpl_fn   = getattr(arcpy.na, "CreateNetworkDatasetFromTemplate", None)

    if create_tpl_fn is None or from_tpl_fn is None:
        print("  テンプレート機能が利用できません。基本ビルドのみ実施します。")
        arcpy.na.BuildNetwork(nd_path)
        _print_manual_instructions(nd_path)
        return

    tmp = os.path.join(tempfile.gettempdir(), "adf_nd_template.xml")
    try:
        # まず基本ビルドしてからテンプレートを書き出す
        print("  基本ネットワークをビルド中...")
        arcpy.na.BuildNetwork(nd_path)

        print("  テンプレートを書き出し中...")
        create_tpl_fn(nd_path, tmp)

        tree = ET.parse(tmp)
        root = tree.getroot()

        # エッジソースのIDを取得（後続の evaluator で使用）
        source_id = _find_edge_source_id(root, EDGE_FC_NAME)
        print(f"  エッジソース ID: {source_id}")

        # 属性コンテナを取得
        attrs_el = _find_or_create_attrs(root)
        existing_ids = _max_existing_id(attrs_el)

        # コスト属性を追加
        cost_defs = [
            ("Walk_Min", "esriNATCost", "esriNAUMinutes", "Walk_Min", True),
            ("Bike_Min", "esriNATCost", "esriNAUMinutes", "Bike_Min", False),
            ("Car_Min",  "esriNATCost", "esriNAUMinutes", "Car_Min",  False),
            ("Meters",   "esriNATCost", "esriNAUMeters",  "length",   False),
        ]
        for i, (name, atype, units, field, default) in enumerate(cost_defs):
            existing_ids += 1
            attrs_el.append(
                _make_field_attr(existing_ids, name, atype, units, field, source_id, default)
            )

        # 制限属性を追加
        restriction_defs = [
            (
                "Oneway",
                "True if str(!mvonlycd!).strip() == '3' else False",
                "True if str(!mvonlycd!).strip() == '1' else False",
                True,
            ),
            (
                "HwyRestrict",
                f"True if str(!rdclasscd!).strip() in {repr(_HIGHWAY_RDCLASS)} else False",
                f"True if str(!rdclasscd!).strip() in {repr(_HIGHWAY_RDCLASS)} else False",
                False,
            ),
        ]
        for name, along_expr, against_expr, default in restriction_defs:
            existing_ids += 1
            attrs_el.append(
                _make_script_attr(existing_ids, name, along_expr, against_expr, source_id, default)
            )

        # Travel Mode を追加
        tm_el = _find_or_create_travel_modes(root)
        _append_travel_mode(tm_el, "Walking Time", "Walk_Min", "Walk_Min", "Meters")
        _append_travel_mode(tm_el, "Cycling Time", "Bike_Min", "Bike_Min", "Meters")

        # 修正済みテンプレートを保存
        tree.write(tmp, encoding="utf-8", xml_declaration=True)

        # 既存 ND を削除して再作成
        print("  Network Dataset を再作成中...")
        arcpy.management.Delete(nd_path)
        from_tpl_fn(tmp, fd_path)

        # 最終ビルド
        print("  最終ビルド中...")
        arcpy.na.BuildNetwork(nd_path)
        print("  属性設定・ビルド完了")
        print("  Travel Mode: 'Walking Time' / 'Cycling Time'")

    except Exception as exc:
        print(f"\n  警告: テンプレート設定に失敗しました ({type(exc).__name__}: {exc})")
        print("  基本ネットワーク（Shape_Length のみ）で使用可能です。")
        print("  ArcpyBackend は Shape_Length フォールバックで動作します。")
        _print_manual_instructions(nd_path)

    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass


# ---- XML ヘルパー ---- #

def _find_edge_source_id(root: ET.Element, source_name: str) -> int:
    """RoadLinks エッジソースの ID を XML から探す。見つからなければ 1 を返す。"""
    for el in root.iter():
        if el.findtext("Name") == source_name:
            id_el = el.find("ID")
            if id_el is not None and id_el.text:
                return int(id_el.text)
    return 1


def _find_or_create_attrs(root: ET.Element) -> ET.Element:
    """ネットワーク属性コンテナ要素を探す（複数の命名規則に対応）。"""
    for tag in ("Attributes", "EvaluatedNetworkAttributes", "NetworkAttributes"):
        el = root.find(f".//{tag}")
        if el is not None:
            return el
    # 見つからなければ DataElement 直下に作成
    data_el = root.find(".//DataElement")
    if data_el is None:
        data_el = root
    attrs_el = ET.SubElement(data_el, "Attributes")
    attrs_el.set("{http://www.w3.org/2001/XMLSchema-instance}type", "esri:ArrayOfNetworkAttribute")
    return attrs_el


def _find_or_create_travel_modes(root: ET.Element) -> ET.Element:
    """Travel Mode コンテナ要素を探す。"""
    for tag in ("TravelModes", "NetworkTravelModes"):
        el = root.find(f".//{tag}")
        if el is not None:
            return el
    data_el = root.find(".//DataElement") or root
    tm_el = ET.SubElement(data_el, "TravelModes")
    tm_el.set("{http://www.w3.org/2001/XMLSchema-instance}type", "esri:ArrayOfNetworkTravelMode")
    return tm_el


def _max_existing_id(attrs_el: ET.Element) -> int:
    """既存属性の最大 ID を返す。"""
    max_id = 0
    for el in attrs_el:
        id_el = el.find("ID")
        if id_el is not None and id_el.text and id_el.text.isdigit():
            max_id = max(max_id, int(id_el.text))
    return max_id


def _make_field_attr(
    attr_id: int, name: str, atype: str, units: str,
    field: str, source_id: int, use_by_default: bool,
) -> ET.Element:
    """フィールド評価器を持つコスト属性要素を生成する。"""
    el = ET.Element("EvaluatedNetworkAttribute")
    el.set("{http://www.w3.org/2001/XMLSchema-instance}type", "esri:EvaluatedNetworkAttribute")
    _sub(el, "ID", str(attr_id))
    _sub(el, "Name", name)
    _sub(el, "Type", atype)
    _sub(el, "Units", units)
    _sub(el, "DataType", "esriNADTDouble")
    _sub(el, "UseByDefault", "true" if use_by_default else "false")
    _sub(el, "ParameterCount", "0")

    evals_el = ET.SubElement(el, "Evaluators")
    evals_el.set("{http://www.w3.org/2001/XMLSchema-instance}type",
                 "esri:ArrayOfNetworkAttributeEvaluator")
    for from_to in (True, False):
        ev = ET.SubElement(evals_el, "NetworkAttributeEvaluator")
        ev.set("{http://www.w3.org/2001/XMLSchema-instance}type",
               "esri:NetworkFieldEvaluator")
        _sub(ev, "NetworkSourceID", str(source_id))
        _sub(ev, "ClassID", "1")
        _sub(ev, "FromToEvaluator", "true" if from_to else "false")
        _sub(ev, "FieldName", field)

    default_el = ET.SubElement(el, "DefaultEvaluator")
    default_el.set("{http://www.w3.org/2001/XMLSchema-instance}type",
                   "esri:NetworkConstantEvaluator")
    _sub(default_el, "NetworkSourceID", "-1")
    _sub(default_el, "ClassID", "0")
    _sub(default_el, "ConstantValue", "0")
    return el


def _make_script_attr(
    attr_id: int, name: str,
    along_expr: str, against_expr: str,
    source_id: int, use_by_default: bool,
) -> ET.Element:
    """スクリプト評価器を持つ制限属性要素を生成する。"""
    el = ET.Element("EvaluatedNetworkAttribute")
    el.set("{http://www.w3.org/2001/XMLSchema-instance}type", "esri:EvaluatedNetworkAttribute")
    _sub(el, "ID", str(attr_id))
    _sub(el, "Name", name)
    _sub(el, "Type", "esriNATRestriction")
    _sub(el, "Units", "esriNAUUnknown")
    _sub(el, "DataType", "esriNADTBoolean")
    _sub(el, "UseByDefault", "true" if use_by_default else "false")
    _sub(el, "ParameterCount", "0")

    evals_el = ET.SubElement(el, "Evaluators")
    evals_el.set("{http://www.w3.org/2001/XMLSchema-instance}type",
                 "esri:ArrayOfNetworkAttributeEvaluator")
    for from_to, expr in ((True, along_expr), (False, against_expr)):
        ev = ET.SubElement(evals_el, "NetworkAttributeEvaluator")
        ev.set("{http://www.w3.org/2001/XMLSchema-instance}type",
               "esri:NetworkScriptEvaluator")
        _sub(ev, "NetworkSourceID", str(source_id))
        _sub(ev, "ClassID", "1")
        _sub(ev, "FromToEvaluator", "true" if from_to else "false")
        _sub(ev, "ScriptExpression", expr)
        _sub(ev, "PreLogic", "")
        _sub(ev, "ScriptExpressionLanguage", "Python3")

    default_el = ET.SubElement(el, "DefaultEvaluator")
    default_el.set("{http://www.w3.org/2001/XMLSchema-instance}type",
                   "esri:NetworkConstantEvaluator")
    _sub(default_el, "NetworkSourceID", "-1")
    _sub(default_el, "ClassID", "0")
    _sub(default_el, "ConstantValue", "false")
    return el


def _append_travel_mode(
    tm_el: ET.Element, name: str,
    impedance: str, time_attr: str, dist_attr: str,
) -> None:
    """Travel Mode 要素を追加する。"""
    # 同名があれば削除
    for existing in list(tm_el):
        if existing.findtext("Name") == name:
            tm_el.remove(existing)

    tm = ET.SubElement(tm_el, "NetworkTravelMode")
    _sub(tm, "Name", name)
    _sub(tm, "Type", "WALK")
    _sub(tm, "Description", name)
    _sub(tm, "Impedance", impedance)
    _sub(tm, "TimeAttributeName", time_attr)
    _sub(tm, "DistanceAttributeName", dist_attr)
    _sub(tm, "UseHierarchy", "-1")
    restrictions_el = ET.SubElement(tm, "Restrictions")
    restrictions_el.set("{http://www.w3.org/2001/XMLSchema-instance}type",
                        "esri:ArrayOfString")
    for r in ("Oneway", "HwyRestrict"):
        _sub(restrictions_el, "String", r)
    ET.SubElement(tm, "RestrictionAttributeParameters").set(
        "{http://www.w3.org/2001/XMLSchema-instance}type",
        "esri:ArrayOfNetworkTravelModeRestrictionAttributeParameter",
    )
    ET.SubElement(tm, "AttributeParameterValues").set(
        "{http://www.w3.org/2001/XMLSchema-instance}type",
        "esri:ArrayOfNetworkTravelModeAttributeParameterValue",
    )


def _sub(parent: ET.Element, tag: str, text: str) -> ET.Element:
    el = ET.SubElement(parent, tag)
    el.text = text
    return el


def _print_manual_instructions(nd_path: str) -> None:
    print("\n" + "=" * 60)
    print("【手動設定の手順】")
    print("=" * 60)
    print("ArcGIS Pro → Catalog → Network Dataset を右クリック")
    print(f"  {nd_path}")
    print("→ Properties → Attributes タブ → Add")
    print()
    print("追加する属性:")
    print("  Walk_Min  : Cost, Minutes, Field=Walk_Min (both dir)")
    print("  Bike_Min  : Cost, Minutes, Field=Bike_Min (both dir)")
    print("  Car_Min   : Cost, Minutes, Field=Car_Min  (both dir)")
    print("  Meters    : Cost, Meters,  Field=length   (both dir)")
    print("  Oneway    : Restriction, mvonlycd==3(Along), ==1(Against)")
    print("  HwyRestrict: Restriction, rdclasscd in {1,2}")
    print()
    print("→ Travel Modes タブ → Add")
    print("  Walking Time : Impedance=Walk_Min, Restrict=Oneway,HwyRestrict")
    print("  Cycling Time : Impedance=Bike_Min, Restrict=Oneway,HwyRestrict")
    print()
    print("※ ArcpyBackend は Travel Mode がなくても Shape_Length で動作します")
    print("=" * 60)


if __name__ == "__main__":
    main()
