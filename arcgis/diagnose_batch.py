# -*- coding: utf-8 -*-
r"""近接性スコア診断（バッチ版・移動モード不要）。

地理座標の ADF ネットワークでも、ArcGIS 組み込み "Length"(メートル) を
impedance に使う旧 ServiceArea ソルバーで到達圏を一括計算する。徒歩/自転車は
速度一定なので cutoff = 分 × 速度(m/分) で正しい到達圏になる。

全起点を1回（チャンク分割）で解き、カテゴリ施設点をポリゴンへ空間結合して
カテゴリ別到達度 a(i,c) を求め、nmincity.core.score で S を算出する。

ArcGIS Pro の arcpy 環境（Network Analyst）で実行する standalone スクリプト。
"""
from __future__ import annotations

import sys
from pathlib import Path

import arcpy

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from nmincity.config import CATEGORY_WEIGHTS, score_label  # noqa: E402
from nmincity.core.score import proximity_score  # noqa: E402

# ---- 設定（必要に応じて編集） ----
ND = r"C:\Users\SinfoLab\Documents\データセット\道路データ\ADF_Network.gdb\RoadNetwork\RoadNetwork_ND"
ORIGINS = r"C:\Users\SinfoLab\Desktop\tosi-design\tosi-design\mesh\tennoji.gdb\origins_tennoji"
CAT_GDB = r"C:\Users\SinfoLab\Desktop\tosi-design\tosi-design\mesh\tennoji.gdb"
OUT_FC = r"C:\Users\SinfoLab\Desktop\tosi-design\tosi-design\mesh\tennoji.gdb\score_tennoji"
SCRATCH = r"C:\Users\SinfoLab\AppData\Local\Temp\claude\diag.gdb"

MINUTES = 15.0
MODE = "walk"
SPEED_MPM = {"walk": 4.8 * 1000 / 60, "bike": 15.0 * 1000 / 60}  # config 準拠
SAMPLE = None          # 例: 300 で先頭300点だけテスト。None で全件
CHUNK = 1000           # 1ソルブあたりの起点数


def log(msg: str) -> None:
    print(msg, flush=True)
    try:
        arcpy.AddMessage(msg)
    except Exception:
        pass


def main() -> None:
    arcpy.env.overwriteOutput = True
    if arcpy.CheckExtension("network") != "Available":
        sys.exit("Network Analyst ライセンスが利用できません。")
    arcpy.CheckOutExtension("network")

    cutoff_m = MINUTES * SPEED_MPM[MODE]
    log(f"mode={MODE} minutes={MINUTES} → cutoff={cutoff_m:.0f} m")

    if arcpy.Exists(SCRATCH):
        arcpy.management.Delete(SCRATCH)
    arcpy.management.CreateFileGDB(str(Path(SCRATCH).parent), Path(SCRATCH).name)

    # 起点読み込み（OID をキーにする）
    oids = [r[0] for r in arcpy.da.SearchCursor(ORIGINS, ["OID@"])]
    if SAMPLE:
        oids = oids[:SAMPLE]
    log(f"評価起点数: {len(oids)}")

    # 起点を一時 FC 化（Name=OID を保持）
    oid_set = set(oids)
    origins_tmp = SCRATCH + r"\origins_sel"
    arcpy.management.CreateFeatureclass(
        SCRATCH, "origins_sel", "POINT",
        spatial_reference=arcpy.Describe(ORIGINS).spatialReference,
    )
    arcpy.management.AddField(origins_tmp, "OOID", "LONG")
    with arcpy.da.SearchCursor(ORIGINS, ["OID@", "SHAPE@"]) as sc, \
         arcpy.da.InsertCursor(origins_tmp, ["OOID", "SHAPE@"]) as ic:
        for oid, shp in sc:
            if oid in oid_set:
                ic.insertRow([oid, shp])

    # 全到達圏ポリゴンを蓄積
    all_polys = SCRATCH + r"\sa_polys"
    poly_created = False

    chunks = [oids[i:i + CHUNK] for i in range(0, len(oids), CHUNK)]
    for ci, chunk in enumerate(chunks, start=1):
        log(f"[到達圏] チャンク {ci}/{len(chunks)} ({len(chunk)}点) 計算中...")
        res = arcpy.na.MakeServiceAreaLayer(
            ND, f"SA_{ci}", "Length", "TRAVEL_FROM", str(cutoff_m),
            polygon_type="DETAILED_POLYS", merge="NO_MERGE",
        )
        salyr = res.getOutput(0)
        names = arcpy.na.GetNAClassNames(salyr)
        fac_name = names["Facilities"]
        poly_name = names["SAPolygons"]

        # このチャンクの起点だけ選択して投入（Name=OOID）
        lyr = arcpy.management.MakeFeatureLayer(
            origins_tmp, f"orig_{ci}",
            "OOID IN (" + ",".join(str(o) for o in chunk) + ")",
        )
        fm = (
            "Name OOID #;"  # 施設名に OOID を入れる
        )
        arcpy.na.AddLocations(
            salyr, fac_name, lyr,
            field_mappings="Name OOID #",
            search_tolerance="500 Meters",
        )
        arcpy.na.Solve(salyr, "SKIP")

        poly_lyr = None
        for L in salyr.listLayers():
            if L.name == poly_name:
                poly_lyr = L
                break
        if not poly_created:
            arcpy.management.CopyFeatures(poly_lyr, all_polys)
            poly_created = True
        else:
            arcpy.management.Append(poly_lyr, all_polys, "NO_TEST")

    total_polys = int(arcpy.management.GetCount(all_polys)[0])
    log(f"到達圏ポリゴン総数: {total_polys}")

    # カテゴリ別: ポリゴンに施設点を空間結合して到達度判定
    reach: dict[int, dict[str, bool]] = {oid: {} for oid in oids}
    for category in CATEGORY_WEIGHTS:
        cat_fc = CAT_GDB + "\\osm_" + category
        if not arcpy.Exists(cat_fc):
            for oid in oids:
                reach[oid][category] = False
            continue
        joined = SCRATCH + f"\\sj_{category}"
        arcpy.analysis.SpatialJoin(
            all_polys, cat_fc, joined,
            "JOIN_ONE_TO_ONE", "KEEP_ALL", match_option="INTERSECT",
        )
        hit: dict[int, bool] = {}
        with arcpy.da.SearchCursor(joined, ["Name", "Join_Count"]) as c:
            for name, jc in c:
                # Name は "{OOID} : {from} - {to}" 形式
                try:
                    oid = int(str(name).split(":")[0].strip().split()[0])
                except (TypeError, ValueError, IndexError):
                    continue
                hit[oid] = hit.get(oid, False) or (jc and jc > 0)
        for oid in oids:
            reach[oid][category] = bool(hit.get(oid, False))
        log(f"  {category}: 到達 {sum(1 for o in oids if reach[o][category])}/{len(oids)}")

    # スコア算出
    scores = {oid: proximity_score(reach[oid]) for oid in oids}
    labels = {oid: score_label(scores[oid]) for oid in oids}

    # 出力 FC（起点コピー＋S,label）
    if arcpy.Exists(OUT_FC):
        arcpy.management.Delete(OUT_FC)
    arcpy.management.CopyFeatures(origins_tmp, OUT_FC)
    arcpy.management.AddField(OUT_FC, "S", "DOUBLE")
    arcpy.management.AddField(OUT_FC, "label", "TEXT", field_length=16)
    with arcpy.da.UpdateCursor(OUT_FC, ["OOID", "S", "label"]) as c:
        for ooid, _s, _l in c:
            c.updateRow([ooid, scores.get(ooid), labels.get(ooid, "不足")])

    vals = list(scores.values())
    avg = sum(vals) / len(vals) if vals else 0.0
    log("=" * 40)
    log(f"S: avg={avg:.3f} min={min(vals):.3f} max={max(vals):.3f}")
    log(f"良好={sum(1 for v in vals if v>=0.8)} "
        f"要改善={sum(1 for v in vals if 0.5<=v<0.8)} "
        f"不足={sum(1 for v in vals if v<0.5)}")
    log(f"出力: {OUT_FC}")


if __name__ == "__main__":
    main()
