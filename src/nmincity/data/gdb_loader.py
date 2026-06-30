"""ArcGIS ファイルジオデータベース(.gdb)の計算済み結果を読む純データ層.

arcpy 非依存。geopandas + pyogrio(GDAL OpenFileGDB) のみを使う。
ArcGIS Pro の Python Toolbox（``arcgis/nmincity.pyt`` の機能A）が出力した
スコア Feature Class（``S`` / ``label`` / 任意で ``reach_<category>`` / ``POP``）と
``osm_<category>`` 施設点群を、folium 可視化向けの素朴なタプル列へ整形する。
"""

from __future__ import annotations

import pyogrio
import geopandas as gpd

from nmincity.config import CATEGORY_NAMES


def list_layers(gdb_path: str) -> list[str]:
    """``.gdb`` 内の全レイヤー名を返す."""

    return [str(name) for name, _geom_type in pyogrio.list_layers(gdb_path)]


def _layer_fields(gdb_path: str, layer: str) -> list[str]:
    return [str(name) for name in pyogrio.read_info(gdb_path, layer=layer)["fields"]]


def list_score_layers(gdb_path: str) -> list[str]:
    """``S`` 列を持つ（＝機能A出力の）レイヤー名を返す（自動検出）."""

    layers = []
    for name in list_layers(gdb_path):
        if "S" in _layer_fields(gdb_path, name):
            layers.append(name)
    return layers


def load_score_points(gdb_path: str, layer: str) -> list[tuple[float, float, float]]:
    """スコアレイヤーを 4326 へ再投影し ``(lat, lon, S)`` 列へ整形する.

    ``S`` が NULL の行はスキップする。``viz.maps.score_map`` /
    ``score_heatmap`` がそのまま受け取れる形。
    """

    gdf = gpd.read_file(gdb_path, layer=layer).to_crs(4326)
    points: list[tuple[float, float, float]] = []
    for geom, score in zip(gdf.geometry, gdf["S"]):
        if geom is None or geom.is_empty or score is None:
            continue
        try:
            value = float(score)
        except (TypeError, ValueError):
            continue
        if value != value:  # NaN
            continue
        points.append((float(geom.y), float(geom.x), value))
    return points


def _estimate_pitch(values: list[float], fallback: float) -> float:
    """整列した格子座標列から1格子分の間隔を推定する（欠損セルがあっても可）."""

    unique = sorted({round(value, 7) for value in values})
    diffs = [b - a for a, b in zip(unique, unique[1:]) if b - a > 1e-9]
    return min(diffs) if diffs else fallback


def load_score_mesh(
    gdb_path: str, layer: str
) -> list[tuple[list[tuple[float, float]], float, str]]:
    """スコアレイヤーの中心点から各メッシュセル（正方形）を復元する.

    日本の地域メッシュは緯度経度に整列するため、4326 へ再投影してから
    緯度・経度方向の格子間隔を推定し、中心点 ± 半セルで矩形セルを作る。
    返り値は ``(セル外周 [(lat, lon), ...], S, label)`` の列で
    ``viz.maps.score_mesh_map`` がそのまま受け取れる。
    """

    gdf = gpd.read_file(gdb_path, layer=layer).to_crs(4326)
    has_label = "label" in gdf.columns
    centers: list[tuple[float, float, float, str]] = []
    for index, (geom, score) in enumerate(zip(gdf.geometry, gdf["S"])):
        if geom is None or geom.is_empty or score is None:
            continue
        try:
            value = float(score)
        except (TypeError, ValueError):
            continue
        if value != value:
            continue
        label = str(gdf["label"].iloc[index]) if has_label else ""
        centers.append((float(geom.y), float(geom.x), value, label))

    if not centers:
        return []

    # 250m メッシュ（緯度7.5"・経度11.25"）を既定フォールバックにする。
    lat_pitch = _estimate_pitch([lat for lat, _lon, _s, _l in centers], 7.5 / 3600)
    lon_pitch = _estimate_pitch([lon for _lat, lon, _s, _l in centers], 11.25 / 3600)
    half_lat = lat_pitch / 2
    half_lon = lon_pitch / 2

    cells: list[tuple[list[tuple[float, float]], float, str]] = []
    for lat, lon, value, label in centers:
        ring = [
            (lat - half_lat, lon - half_lon),
            (lat - half_lat, lon + half_lon),
            (lat + half_lat, lon + half_lon),
            (lat + half_lat, lon - half_lon),
        ]
        cells.append((ring, value, label))
    return cells


def load_facility_points(
    gdb_path: str, prefix: str = "osm_"
) -> dict[str, list[tuple[float, float]]]:
    """7要素の ``<prefix><category>`` 施設点群を 4326 で読み ``(lat, lon)`` 化する.

    ``CATEGORY_NAMES`` の全カテゴリを必ずキーに持つ（該当レイヤーが無ければ空）。
    """

    available = set(list_layers(gdb_path))
    result: dict[str, list[tuple[float, float]]] = {category: [] for category in CATEGORY_NAMES}
    for category in CATEGORY_NAMES:
        layer = f"{prefix}{category}"
        if layer not in available:
            continue
        gdf = gpd.read_file(gdb_path, layer=layer).to_crs(4326)
        for geom in gdf.geometry:
            if geom is None or geom.is_empty:
                continue
            result[category].append((float(geom.y), float(geom.x)))
    return result


def load_reach_profile(
    gdb_path: str, layer: str, weight_field: str = "POP"
) -> dict[str, float] | None:
    """``reach_<category>`` 列からカテゴリ別到達率を返す（``POP`` があれば人口加重）.

    到達カラムが1つも無いレイヤーでは ``None`` を返す（呼び出し側で
    レーダー比較を省略する）。
    """

    fields = set(_layer_fields(gdb_path, layer))
    reach_cols = {category: f"reach_{category}" for category in CATEGORY_NAMES}
    if not any(col in fields for col in reach_cols.values()):
        return None

    gdf = gpd.read_file(gdb_path, layer=layer)
    use_weight = weight_field in fields
    profile: dict[str, float] = {}
    for category, col in reach_cols.items():
        if col not in fields:
            profile[category] = 0.0
            continue
        numerator = 0.0
        denominator = 0.0
        for index, reached in enumerate(gdf[col]):
            if reached is None or reached != reached:  # None / NaN
                continue
            weight = 1.0
            if use_weight:
                raw = gdf[weight_field].iloc[index]
                weight = float(raw) if raw is not None and raw == raw else 0.0
            numerator += weight * float(reached)
            denominator += weight
        profile[category] = numerator / denominator if denominator else 0.0
    return profile


def load_score_summary(
    gdb_path: str, layer: str, weight_field: str = "POP"
) -> dict[str, object]:
    """起点数・mean S（``POP`` があれば人口加重）・label別件数を返す."""

    fields = set(_layer_fields(gdb_path, layer))
    gdf = gpd.read_file(gdb_path, layer=layer)
    use_weight = weight_field in fields

    numerator = 0.0
    denominator = 0.0
    count = 0
    labels: dict[str, int] = {"良好": 0, "要改善": 0, "不足": 0}
    has_label = "label" in fields
    for index, score in enumerate(gdf["S"]):
        if score is None or score != score:
            continue
        count += 1
        weight = 1.0
        if use_weight:
            raw = gdf[weight_field].iloc[index]
            weight = float(raw) if raw is not None and raw == raw else 0.0
        numerator += weight * float(score)
        denominator += weight
        if has_label:
            label = gdf["label"].iloc[index]
            if label in labels:
                labels[label] += 1
    mean_s = numerator / denominator if denominator else 0.0
    return {"origins": count, "mean_s": mean_s, "labels": labels, "pop_weighted": use_weight}
