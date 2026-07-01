"""folium による MVP 地図出力."""

from __future__ import annotations

from pathlib import Path
import base64
import html
import struct
import zlib

import folium
from folium.plugins import HeatMap

from nmincity.config import CATEGORY_NAMES, score_label


LABEL_COLORS = {
    "良好": "#15803d",
    "要改善": "#f97316",
    "不足": "#dc2626",
}

# 7要素レイヤー: 到達=緑 / 未到達=赤。
REACH_COLOR = "#15803d"
UNREACH_COLOR = "#dc2626"

# 施設分布マップ用: 7要素をカテゴリ別に色分けするパレット（config のキー順）。
CATEGORY_COLORS = {
    "education": "#2563eb",
    "nature": "#15803d",
    "goods": "#f97316",
    "health": "#dc2626",
    "transit": "#7c3aed",
    "leisure": "#db2777",
    "work": "#0891b2",
}


def score_map(points: list[tuple[float, float, float]], place: str) -> folium.Map:
    """``(lat, lon, S)`` 点群をスコアラベル色で描画した地図を返す."""

    if points:
        center_lat = sum(lat for lat, _lon, _score in points) / len(points)
        center_lon = sum(lon for _lat, lon, _score in points) / len(points)
    else:
        center_lat, center_lon = 35.0, 139.0

    m = folium.Map(location=[center_lat, center_lon], zoom_start=15, tiles="cartodbpositron")
    for lat, lon, score in points:
        label = score_label(score)
        color = LABEL_COLORS[label]
        folium.CircleMarker(
            location=[lat, lon],
            radius=4,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.72,
            weight=1,
            popup=f"S={score:.3f} / {label}",
        ).add_to(m)

    legend = _legend_html(place)
    m.get_root().html.add_child(folium.Element(legend))
    return m


def save_map(m: folium.Map, path: str) -> None:
    """親ディレクトリを作成して folium 地図 HTML を保存する."""

    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    m.save(str(output))


def category_layer_points(
    reach_by_origin: dict[object, dict[str, bool]],
    latlon_by_origin: dict[object, tuple[float, float]],
) -> dict[str, list[tuple[float, float, bool]]]:
    """起点別カテゴリ到達度を、カテゴリ別の ``(lat, lon, reachable)`` 列に整形する.

    folium 非依存の純データ整形ヘルパ（テスト対象）。``CATEGORY_NAMES`` の
    全7カテゴリを必ずキーに持ち、座標の取れない起点はスキップする。
    """

    result: dict[str, list[tuple[float, float, bool]]] = {category: [] for category in CATEGORY_NAMES}
    for origin, reach in reach_by_origin.items():
        latlon = latlon_by_origin.get(origin)
        if latlon is None:
            continue
        lat, lon = latlon
        for category in CATEGORY_NAMES:
            reachable = bool(reach.get(category, False))
            result[category].append((lat, lon, reachable))
    return result


def category_layers_map(
    category_points: dict[str, list[tuple[float, float, bool]]],
    place: str,
) -> folium.Map:
    """7要素（用途カテゴリ）をレイヤー分けした地図を返す.

    カテゴリごとに ``FeatureGroup`` を作り、到達=緑/未到達=赤で起点を描画する。
    ``LayerControl`` で各要素をトグルできる（先頭カテゴリのみ初期表示）。
    """

    all_points = [
        (lat, lon)
        for points in category_points.values()
        for lat, lon, _reachable in points
    ]
    if all_points:
        center_lat = sum(lat for lat, _lon in all_points) / len(all_points)
        center_lon = sum(lon for _lat, lon in all_points) / len(all_points)
    else:
        center_lat, center_lon = 34.65, 135.51

    m = folium.Map(location=[center_lat, center_lon], zoom_start=15, tiles="cartodbpositron")

    first = True
    for category, points in category_points.items():
        name = CATEGORY_NAMES.get(category, category)
        group = folium.FeatureGroup(name=name, show=first)
        for lat, lon, reachable in points:
            color = REACH_COLOR if reachable else UNREACH_COLOR
            folium.CircleMarker(
                location=[lat, lon],
                radius=4,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.72,
                weight=1,
                popup=f"{name}: {'到達' if reachable else '未到達'}",
            ).add_to(group)
        group.add_to(m)
        first = False

    folium.LayerControl(collapsed=False).add_to(m)
    m.get_root().html.add_child(folium.Element(_category_legend_html(place)))
    return m


def facility_layers_map(
    facilities: dict[str, list[tuple[float, float]]],
    place: str,
) -> folium.Map:
    """7要素の施設分布をカテゴリ別レイヤーに分けて描画した地図を返す.

    ``category_layers_map`` の ``FeatureGroup``＋``LayerControl`` パターンを踏襲し、
    入力 ``{category: [(lat, lon), ...]}`` を ``CATEGORY_COLORS`` で色分けする。
    ArcGIS .gdb の ``osm_<category>`` 施設点群（到達/未到達の区別なし）向け。
    先頭カテゴリのみ初期表示。
    """

    all_points = [point for points in facilities.values() for point in points]
    if all_points:
        center_lat = sum(lat for lat, _lon in all_points) / len(all_points)
        center_lon = sum(lon for _lat, lon in all_points) / len(all_points)
    else:
        center_lat, center_lon = 34.65, 135.51

    m = folium.Map(location=[center_lat, center_lon], zoom_start=15, tiles="cartodbpositron")

    first = True
    for category, points in facilities.items():
        name = CATEGORY_NAMES.get(category, category)
        color = CATEGORY_COLORS.get(category, "#6b7280")
        group = folium.FeatureGroup(name=f"{name} ({len(points)})", show=first)
        for lat, lon in points:
            folium.CircleMarker(
                location=[lat, lon],
                radius=4,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.72,
                weight=1,
                popup=name,
            ).add_to(group)
        group.add_to(m)
        first = False

    folium.LayerControl(collapsed=False).add_to(m)
    m.get_root().html.add_child(folium.Element(_facility_legend_html(place)))
    return m


def category_surfaces_map(
    category_points: dict[str, list[tuple[float, float, bool]]],
    place: str,
    resolution: int = 240,
) -> folium.Map:
    """7要素（用途カテゴリ）別に到達評価 ``a(i,c)`` を補間した連続面を返す（重みづけ前）.

    重みで合成する前の各起点評価（到達=1.0 / 未到達=0.0）を要素ごとに
    ``scipy`` 線形補間し、赤(0)→橙→緑(1)のグラデーション面を ``ImageOverlay``
    として ``FeatureGroup`` に重ねる。全要素で同一の補間範囲を使うので要素間で
    比較できる。``LayerControl`` で要素を切替（先頭カテゴリのみ初期表示）。入力は
    ``category_layer_points`` / ``gdb_loader.load_category_reach_points`` の出力。
    """

    all_points = [
        (lat, lon, 0.0)
        for points in category_points.values()
        for lat, lon, _reachable in points
    ]
    if all_points:
        bounds = _padded_bounds(all_points)
        lat_min, lat_max, lon_min, lon_max = bounds
        center = [(lat_min + lat_max) / 2, (lon_min + lon_max) / 2]
    else:
        bounds = None
        center = [34.65, 135.51]

    m = folium.Map(location=center, zoom_start=15, tiles="cartodbpositron")

    first = True
    for category, points in category_points.items():
        name = CATEGORY_NAMES.get(category, category)
        group = folium.FeatureGroup(name=name, show=first)
        if bounds is not None and points:
            value_points = [
                (lat, lon, 1.0 if reachable else 0.0) for lat, lon, reachable in points
            ]
            overlay = _surface_image_overlay(value_points, bounds, resolution=resolution)
            if overlay is not None:
                overlay.add_to(group)
        group.add_to(m)
        first = False

    folium.LayerControl(collapsed=False).add_to(m)
    m.get_root().html.add_child(folium.Element(_category_surface_legend_html(place)))
    return m


def score_heatmap(
    points: list[tuple[float, float, float]],
    category_points: dict[str, list[tuple[float, float, bool]]] | None,
    place: str,
) -> folium.Map:
    """近接性 ``S`` を連続ヒートマップで表示する地図を返す.

    任意で ``category_points`` を渡すと、各カテゴリの未到達密度ヒートを
    トグル可能なレイヤーとして追加する（不足の集中が面で読める）。
    """

    if points:
        center_lat = sum(lat for lat, _lon, _score in points) / len(points)
        center_lon = sum(lon for _lat, lon, _score in points) / len(points)
    else:
        center_lat, center_lon = 34.65, 135.51

    m = folium.Map(location=[center_lat, center_lon], zoom_start=15, tiles="cartodbpositron")

    s_layer = folium.FeatureGroup(name="S 近接性ヒート", show=True)
    HeatMap(
        [[lat, lon, max(0.0, min(1.0, score))] for lat, lon, score in points],
        radius=18,
        blur=22,
        min_opacity=0.3,
    ).add_to(s_layer)
    s_layer.add_to(m)

    for category, cat_points in (category_points or {}).items():
        name = CATEGORY_NAMES.get(category, category)
        deficit = [[lat, lon, 1.0] for lat, lon, reachable in cat_points if not reachable]
        if not deficit:
            continue
        layer = folium.FeatureGroup(name=f"未到達: {name}", show=False)
        HeatMap(deficit, radius=18, blur=22, min_opacity=0.3).add_to(layer)
        layer.add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)
    m.get_root().html.add_child(folium.Element(_heatmap_legend_html(place)))
    return m


def score_mesh_map(
    cells: list[tuple[list[tuple[float, float]], float, str]],
    place: str,
) -> folium.Map:
    """メッシュセルを評価ラベル色で塗り分けた地図を返す（離散コロプレス）.

    ``cells`` は ``(セル外周 [(lat, lon), ...], S, label)`` の列。各セルを
    ``LABEL_COLORS``（良好/要改善/不足）で塗る。中心点ではなく面で評価が読める。
    """

    all_points = [point for ring, _score, _label in cells for point in ring]
    if all_points:
        center_lat = sum(lat for lat, _lon in all_points) / len(all_points)
        center_lon = sum(lon for _lat, lon in all_points) / len(all_points)
    else:
        center_lat, center_lon = 34.65, 135.51

    m = folium.Map(location=[center_lat, center_lon], zoom_start=15, tiles="cartodbpositron")
    for ring, score, label in cells:
        color = LABEL_COLORS.get(label or score_label(score), "#6b7280")
        folium.Polygon(
            locations=ring,
            color=color,
            weight=0.5,
            fill=True,
            fill_color=color,
            fill_opacity=0.62,
            popup=f"S={score:.3f} / {label}",
        ).add_to(m)

    m.get_root().html.add_child(folium.Element(_legend_html(f"メッシュ評価: {place}")))
    return m


def score_surface_map(
    points: list[tuple[float, float, float]],
    place: str,
    resolution: int = 240,
) -> folium.Map:
    """格子点 ``(lat, lon, S)`` を補間した滑らかな連続サーフェス地図を返す.

    ``scipy.interpolate.griddata`` で線形補間し、凸包外（データ無し）は透過する。
    赤(低)→橙→緑(高)のグラデーションを RGBA-PNG にして ``ImageOverlay`` で重ねる。
    """

    if not points:
        return folium.Map(location=[34.65, 135.51], zoom_start=15, tiles="cartodbpositron")

    bounds = _padded_bounds(points)
    lat_min, lat_max, lon_min, lon_max = bounds
    m = folium.Map(
        location=[(lat_min + lat_max) / 2, (lon_min + lon_max) / 2],
        zoom_start=15,
        tiles="cartodbpositron",
    )
    overlay = _surface_image_overlay(points, bounds, resolution=resolution)
    if overlay is not None:
        overlay.add_to(m)
    m.get_root().html.add_child(folium.Element(_surface_legend_html(place)))
    return m


def _padded_bounds(
    points: list[tuple[float, float, float]], pad: float = 0.02
) -> tuple[float, float, float, float]:
    """点群の緯度経度範囲を ``pad`` 割だけ広げた ``(lat_min, lat_max, lon_min, lon_max)``."""

    lats = [lat for lat, _lon, *_ in points]
    lons = [lon for _lat, lon, *_ in points]
    lat_min, lat_max = min(lats), max(lats)
    lon_min, lon_max = min(lons), max(lons)
    pad_lat = (lat_max - lat_min) * pad or 1e-4
    pad_lon = (lon_max - lon_min) * pad or 1e-4
    return lat_min - pad_lat, lat_max + pad_lat, lon_min - pad_lon, lon_max + pad_lon


def _surface_image_overlay(
    points: list[tuple[float, float, float]],
    bounds: tuple[float, float, float, float],
    *,
    resolution: int = 240,
    opacity: float = 0.85,
) -> "folium.raster_layers.ImageOverlay | None":
    """``(lat, lon, value 0..1)`` を ``bounds`` 上で線形補間した ImageOverlay を返す.

    ``scipy.interpolate.griddata`` で補間し、凸包外（NaN）は透過。点が無い、または
    補間できない（同一直線上など）場合は ``None``。map には add せずに返すので、
    呼び出し側で任意のレイヤーへ add できる。
    """

    if not points:
        return None

    import numpy as np
    from scipy.interpolate import griddata

    lat_min, lat_max, lon_min, lon_max = bounds
    lats = np.array([lat for lat, _lon, _v in points], dtype=float)
    lons = np.array([lon for _lat, lon, _v in points], dtype=float)
    vals = np.array([max(0.0, min(1.0, v)) for _lat, _lon, v in points], dtype=float)

    grid_lon = np.linspace(lon_min, lon_max, resolution)
    grid_lat = np.linspace(lat_max, lat_min, resolution)  # 行0を北端にする
    mesh_lon, mesh_lat = np.meshgrid(grid_lon, grid_lat)
    try:
        surface = griddata((lons, lats), vals, (mesh_lon, mesh_lat), method="linear")
    except Exception:  # 点が少ない/同一直線上で三角形分割できない → 面を省略
        return None

    pixels = bytearray(resolution * resolution * 4)
    for row in range(resolution):
        for col in range(resolution):
            value = surface[row, col]
            if value != value:  # NaN（データ範囲外）→ 透過
                continue
            idx = (row * resolution + col) * 4
            red, green, blue = _score_color_rgb(float(value))
            pixels[idx] = red
            pixels[idx + 1] = green
            pixels[idx + 2] = blue
            pixels[idx + 3] = 180
    data_uri = "data:image/png;base64," + base64.b64encode(
        _encode_png_rgba(bytes(pixels), resolution, resolution)
    ).decode("ascii")
    return folium.raster_layers.ImageOverlay(
        image=data_uri,
        bounds=[[lat_min, lon_min], [lat_max, lon_max]],
        opacity=opacity,
        interactive=False,
        zindex=1,
    )


def walkability_map(lines: list[tuple[list[tuple[float, float]], float]], place: str) -> folium.Map:
    """街路区間を歩行環境の質で色分けした地図を返す."""

    points = [point for coords, _quality in lines for point in coords]
    if points:
        center_lat = sum(lat for lat, _lon in points) / len(points)
        center_lon = sum(lon for _lat, lon in points) / len(points)
    else:
        center_lat, center_lon = 35.0, 139.0

    m = folium.Map(location=[center_lat, center_lon], zoom_start=15, tiles="cartodbpositron")
    for coords, quality in lines:
        folium.PolyLine(
            locations=coords,
            color=_quality_color(quality),
            weight=4,
            opacity=0.78,
            popup=f"Q_edge={quality:.3f}",
        ).add_to(m)

    m.get_root().html.add_child(folium.Element(_walk_legend_html(place)))
    return m


def time_of_day_map(points_by_bucket: dict[str, list[tuple[float, float, float]]], place: str) -> folium.Map:
    """時間帯ごとに ``(lat, lon, S(t))`` 点群を切替表示する地図を返す."""

    all_points = [point for points in points_by_bucket.values() for point in points]
    if all_points:
        center_lat = sum(lat for lat, _lon, _score in all_points) / len(all_points)
        center_lon = sum(lon for _lat, lon, _score in all_points) / len(all_points)
    else:
        center_lat, center_lon = 35.0, 139.0

    m = folium.Map(location=[center_lat, center_lon], zoom_start=15, tiles="cartodbpositron")
    for bucket, points in points_by_bucket.items():
        show = bucket == "daytime"
        group = folium.FeatureGroup(name=bucket, show=show)
        for lat, lon, score in points:
            label = score_label(score)
            color = LABEL_COLORS[label]
            folium.CircleMarker(
                location=[lat, lon],
                radius=4,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.72,
                weight=1,
                popup=f"{bucket}: S={score:.3f} / {label}",
            ).add_to(group)
        group.add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)
    m.get_root().html.add_child(folium.Element(_legend_html(f"時間帯別 n分都市度: {place}")))
    return m


def proposal_map(
    deficient_points: list[tuple[float, float, float]],
    proposal_points: list[tuple[float, float, str, float]],
    place: str,
) -> folium.Map:
    """不足起点と改善提案の代表位置を描画した地図を返す."""

    all_points = [(lat, lon) for lat, lon, _score in deficient_points]
    all_points.extend((lat, lon) for lat, lon, _label, _priority in proposal_points)
    if all_points:
        center_lat = sum(lat for lat, _lon in all_points) / len(all_points)
        center_lon = sum(lon for _lat, lon in all_points) / len(all_points)
    else:
        center_lat, center_lon = 35.0, 139.0

    m = folium.Map(location=[center_lat, center_lon], zoom_start=15, tiles="cartodbpositron")

    deficient_group = folium.FeatureGroup(name="不足起点", show=True)
    for lat, lon, score in deficient_points:
        folium.CircleMarker(
            location=[lat, lon],
            radius=5,
            color="#dc2626",
            fill=True,
            fill_color="#fecaca",
            fill_opacity=0.70,
            weight=1,
            popup=f"不足起点 S={score:.3f}",
        ).add_to(deficient_group)
    deficient_group.add_to(m)

    proposal_group = folium.FeatureGroup(name="改善提案", show=True)
    for lat, lon, label, priority in proposal_points:
        popup = html.escape(f"{label}\n優先度={priority:.3f}").replace("\n", "<br>")
        folium.Marker(
            location=[lat, lon],
            popup=popup,
            tooltip=f"提案 優先度={priority:.3f}",
            icon=folium.Icon(color="blue", icon="info-sign"),
        ).add_to(proposal_group)
    proposal_group.add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)
    m.get_root().html.add_child(folium.Element(_proposal_legend_html(place)))
    return m


def allocation_map(
    selected_points: list[tuple[float, float, str]],
    covered_points: list[tuple[float, float]],
    unmet_points: list[tuple[float, float]],
    place: str,
) -> folium.Map:
    """最適配置候補、配置で新たに被覆される起点、現状未充足起点を描画する."""

    all_points = list(unmet_points) + list(covered_points)
    all_points.extend((lat, lon) for lat, lon, _label in selected_points)
    if all_points:
        center_lat = sum(lat for lat, _lon in all_points) / len(all_points)
        center_lon = sum(lon for _lat, lon in all_points) / len(all_points)
    else:
        center_lat, center_lon = 35.0, 139.0

    m = folium.Map(location=[center_lat, center_lon], zoom_start=15, tiles="cartodbpositron")

    unmet_group = folium.FeatureGroup(name="現状未充足起点", show=True)
    covered_set = set(covered_points)
    for lat, lon in unmet_points:
        if (lat, lon) in covered_set:
            continue
        folium.CircleMarker(
            location=[lat, lon],
            radius=4,
            color="#94a3b8",
            fill=True,
            fill_color="#cbd5e1",
            fill_opacity=0.46,
            weight=1,
            popup="現状未充足起点",
        ).add_to(unmet_group)
    unmet_group.add_to(m)

    covered_group = folium.FeatureGroup(name="新規被覆起点", show=True)
    for lat, lon in covered_points:
        folium.CircleMarker(
            location=[lat, lon],
            radius=6,
            color="#16a34a",
            fill=True,
            fill_color="#86efac",
            fill_opacity=0.82,
            weight=2,
            popup="配置により新たに被覆",
        ).add_to(covered_group)
    covered_group.add_to(m)

    selected_group = folium.FeatureGroup(name="選択配置地", show=True)
    for lat, lon, label in selected_points:
        folium.Marker(
            location=[lat, lon],
            popup=html.escape(label),
            tooltip="選択配置地",
            icon=folium.Icon(color="blue", icon="plus-sign"),
        ).add_to(selected_group)
        folium.CircleMarker(
            location=[lat, lon],
            radius=10,
            color="#1d4ed8",
            fill=False,
            weight=3,
        ).add_to(selected_group)
    selected_group.add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)
    m.get_root().html.add_child(folium.Element(_allocation_legend_html(place)))
    return m


def sq_scatter(points: list[tuple[float, float, str]], place: str, path: str) -> None:
    """起点別の ``S`` と ``Q`` を並置する散布図 PNG を保存する."""

    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)

    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:  # pragma: no cover - optional dependency fallback
        _simple_scatter_png(points, output)
        return

    xs = [s for s, _q, _label in points]
    ys = [q for _s, q, _label in points]
    colors = [LABEL_COLORS.get(label, "#6b7280") for _s, _q, label in points]

    fig, ax = plt.subplots(figsize=(7, 6), dpi=150)
    ax.scatter(xs, ys, c=colors, s=28, alpha=0.78, edgecolors="white", linewidths=0.4)
    ax.axvline(0.5, color="#6b7280", linewidth=1.0, linestyle="--")
    ax.axhline(0.5, color="#6b7280", linewidth=1.0, linestyle="--")
    ax.text(0.98, 0.04, "S高Q低", ha="right", va="bottom", transform=ax.transAxes, color="#374151")
    ax.set_xlim(0.0, 1.0)
    ax.set_ylim(0.0, 1.0)
    ax.set_xlabel("S 近接性")
    ax.set_ylabel("Q 環境の質")
    ax.set_title(place)
    ax.grid(True, color="#e5e7eb", linewidth=0.8)
    fig.tight_layout()
    fig.savefig(output)
    plt.close(fig)


def _legend_html(place: str) -> str:
    rows = "".join(
        f'<div><span style="background:{color};"></span>{label}</div>'
        for label, color in LABEL_COLORS.items()
    )
    return f"""
    <div style="
      position: fixed; bottom: 24px; left: 24px; z-index: 9999;
      background: white; padding: 10px 12px; border: 1px solid #d1d5db;
      border-radius: 6px; font-size: 13px; box-shadow: 0 1px 4px #0002;">
      <div style="font-weight: 700; margin-bottom: 6px;">n分都市度: {place}</div>
      <style>
        .nmincity-legend span {{
          display: inline-block; width: 10px; height: 10px; margin-right: 6px;
          border-radius: 999px;
        }}
      </style>
      <div class="nmincity-legend">{rows}</div>
    </div>
    """


def _category_legend_html(place: str) -> str:
    return f"""
    <div style="
      position: fixed; bottom: 24px; left: 24px; z-index: 9999;
      background: white; padding: 10px 12px; border: 1px solid #d1d5db;
      border-radius: 6px; font-size: 13px; box-shadow: 0 1px 4px #0002;">
      <div style="font-weight: 700; margin-bottom: 6px;">7要素レイヤー: {place}</div>
      <div><span style="display:inline-block; width:10px; height:10px;
        background:{REACH_COLOR}; border-radius:999px; margin-right:6px;"></span>到達</div>
      <div><span style="display:inline-block; width:10px; height:10px;
        background:{UNREACH_COLOR}; border-radius:999px; margin-right:6px;"></span>未到達</div>
      <div style="margin-top:4px; color:#6b7280;">右上のレイヤー操作で要素を切替</div>
    </div>
    """


def _facility_legend_html(place: str) -> str:
    rows = "".join(
        f'<div><span style="display:inline-block; width:10px; height:10px;'
        f' background:{CATEGORY_COLORS.get(category, "#6b7280")}; border-radius:999px;'
        f' margin-right:6px;"></span>{CATEGORY_NAMES.get(category, category)}</div>'
        for category in CATEGORY_COLORS
    )
    return f"""
    <div style="
      position: fixed; bottom: 24px; left: 24px; z-index: 9999;
      background: white; padding: 10px 12px; border: 1px solid #d1d5db;
      border-radius: 6px; font-size: 13px; box-shadow: 0 1px 4px #0002;">
      <div style="font-weight: 700; margin-bottom: 6px;">7要素 施設分布: {place}</div>
      {rows}
      <div style="margin-top:4px; color:#6b7280;">右上のレイヤー操作で要素を切替</div>
    </div>
    """


def _category_surface_legend_html(place: str) -> str:
    return f"""
    <div style="
      position: fixed; bottom: 24px; left: 24px; z-index: 9999;
      background: white; padding: 10px 12px; border: 1px solid #d1d5db;
      border-radius: 6px; font-size: 13px; box-shadow: 0 1px 4px #0002;">
      <div style="font-weight: 700; margin-bottom: 6px;">7要素レイヤー別 到達面（重みづけ前）: {place}</div>
      <div style="display:flex; align-items:center; gap:8px;">
        <span>未到達</span>
        <span style="display:inline-block; width:120px; height:10px;
          background: linear-gradient(90deg, #dc2626, #f59e0b, #15803d);"></span>
        <span>到達</span>
      </div>
      <div style="margin-top:4px; color:#6b7280;">各要素ごとに到達評価を補間した面。右上のレイヤー操作で要素を切替。</div>
    </div>
    """


def _heatmap_legend_html(place: str) -> str:
    return f"""
    <div style="
      position: fixed; bottom: 24px; left: 24px; z-index: 9999;
      background: white; padding: 10px 12px; border: 1px solid #d1d5db;
      border-radius: 6px; font-size: 13px; box-shadow: 0 1px 4px #0002;">
      <div style="font-weight: 700; margin-bottom: 6px;">近接性ヒートマップ: {place}</div>
      <div style="color:#6b7280;">S が高いほど密な面。未到達レイヤーは不足の集中を示す。</div>
    </div>
    """


def _quality_color(quality: float) -> str:
    q = max(0.0, min(1.0, float(quality)))
    red = int(220 + (21 - 220) * q)
    green = int(38 + (128 - 38) * q)
    blue = int(38 + (61 - 38) * q)
    return f"#{red:02x}{green:02x}{blue:02x}"


def _walk_legend_html(place: str) -> str:
    return f"""
    <div style="
      position: fixed; bottom: 24px; left: 24px; z-index: 9999;
      background: white; padding: 10px 12px; border: 1px solid #d1d5db;
      border-radius: 6px; font-size: 13px; box-shadow: 0 1px 4px #0002;">
      <div style="font-weight: 700; margin-bottom: 6px;">歩行環境の質: {place}</div>
      <div style="display:flex; align-items:center; gap:8px;">
        <span>低</span>
        <span style="display:inline-block; width:96px; height:10px;
          background: linear-gradient(90deg, #dc2626, #15803d);"></span>
        <span>高</span>
      </div>
    </div>
    """


def _proposal_legend_html(place: str) -> str:
    return f"""
    <div style="
      position: fixed; bottom: 24px; left: 24px; z-index: 9999;
      background: white; padding: 10px 12px; border: 1px solid #d1d5db;
      border-radius: 6px; font-size: 13px; box-shadow: 0 1px 4px #0002;">
      <div style="font-weight: 700; margin-bottom: 6px;">改善提案: {place}</div>
      <div><span style="display:inline-block; width:10px; height:10px;
        background:#fecaca; border:1px solid #dc2626; border-radius:999px;
        margin-right:6px;"></span>S&lt;0.5 の不足起点</div>
      <div><span style="display:inline-block; width:10px; height:10px;
        background:#2563eb; border-radius:2px; margin-right:6px;"></span>提案代表位置</div>
    </div>
    """


def _allocation_legend_html(place: str) -> str:
    return f"""
    <div style="
      position: fixed; bottom: 24px; left: 24px; z-index: 9999;
      background: white; padding: 10px 12px; border: 1px solid #d1d5db;
      border-radius: 6px; font-size: 13px; box-shadow: 0 1px 4px #0002;">
      <div style="font-weight: 700; margin-bottom: 6px;">最適配置: {place}</div>
      <div><span style="display:inline-block; width:10px; height:10px;
        background:#cbd5e1; border:1px solid #94a3b8; border-radius:999px;
        margin-right:6px;"></span>現状未充足起点</div>
      <div><span style="display:inline-block; width:10px; height:10px;
        background:#86efac; border:1px solid #16a34a; border-radius:999px;
        margin-right:6px;"></span>新規被覆起点</div>
      <div><span style="display:inline-block; width:10px; height:10px;
        background:#2563eb; border-radius:2px; margin-right:6px;"></span>選択配置地</div>
    </div>
    """


def _simple_scatter_png(points: list[tuple[float, float, str]], output: Path) -> None:
    width = 900
    height = 720
    margin_left = 86
    margin_right = 40
    margin_top = 40
    margin_bottom = 78
    plot_w = width - margin_left - margin_right
    plot_h = height - margin_top - margin_bottom
    image = bytearray([255, 255, 255] * width * height)

    def set_pixel(x: int, y: int, color: tuple[int, int, int]) -> None:
        if 0 <= x < width and 0 <= y < height:
            idx = (y * width + x) * 3
            image[idx : idx + 3] = bytes(color)

    def line(x1: int, y1: int, x2: int, y2: int, color: tuple[int, int, int]) -> None:
        dx = abs(x2 - x1)
        dy = -abs(y2 - y1)
        sx = 1 if x1 < x2 else -1
        sy = 1 if y1 < y2 else -1
        err = dx + dy
        while True:
            set_pixel(x1, y1, color)
            if x1 == x2 and y1 == y2:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x1 += sx
            if e2 <= dx:
                err += dx
                y1 += sy

    def fill_circle(cx: int, cy: int, radius: int, color: tuple[int, int, int]) -> None:
        r2 = radius * radius
        for y in range(cy - radius, cy + radius + 1):
            for x in range(cx - radius, cx + radius + 1):
                if (x - cx) ** 2 + (y - cy) ** 2 <= r2:
                    set_pixel(x, y, color)

    grid = (229, 231, 235)
    axis = (55, 65, 81)
    mid = (107, 114, 128)
    for step in range(11):
        x = margin_left + round(plot_w * step / 10)
        y = margin_top + round(plot_h * step / 10)
        line(x, margin_top, x, margin_top + plot_h, grid)
        line(margin_left, y, margin_left + plot_w, y, grid)
    line(margin_left, margin_top + plot_h, margin_left + plot_w, margin_top + plot_h, axis)
    line(margin_left, margin_top, margin_left, margin_top + plot_h, axis)
    mid_x = margin_left + round(plot_w * 0.5)
    mid_y = margin_top + round(plot_h * 0.5)
    line(mid_x, margin_top, mid_x, margin_top + plot_h, mid)
    line(margin_left, mid_y, margin_left + plot_w, mid_y, mid)

    for s, q, label in points:
        x = margin_left + round(plot_w * max(0.0, min(1.0, s)))
        y = margin_top + round(plot_h * (1.0 - max(0.0, min(1.0, q))))
        color = _hex_to_rgb(LABEL_COLORS.get(label, "#6b7280"))
        fill_circle(x, y, 5, color)

    rows = [bytes(image[y * width * 3 : (y + 1) * width * 3]) for y in range(height)]
    raw = b"".join(b"\x00" + row for row in rows)
    png = b"\x89PNG\r\n\x1a\n" + _png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    png += _png_chunk(b"IDAT", zlib.compress(raw, 9))
    png += _png_chunk(b"IEND", b"")
    output.write_bytes(png)


def _png_chunk(kind: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    hex_value = value.lstrip("#")
    return int(hex_value[0:2], 16), int(hex_value[2:4], 16), int(hex_value[4:6], 16)


# 連続サーフェス用カラーランプ: 低=赤 → 中=橙 → 高=緑（スコアラベル配色に整合）。
_SURFACE_STOPS = ((0.0, (220, 38, 38)), (0.5, (245, 158, 11)), (1.0, (21, 128, 61)))


def _score_color_rgb(value: float) -> tuple[int, int, int]:
    """0–1 の S を赤→橙→緑のグラデーション RGB に写す."""

    value = max(0.0, min(1.0, value))
    for (low, low_rgb), (high, high_rgb) in zip(_SURFACE_STOPS, _SURFACE_STOPS[1:]):
        if value <= high:
            span = high - low or 1.0
            ratio = (value - low) / span
            return tuple(  # type: ignore[return-value]
                int(round(lc + (hc - lc) * ratio)) for lc, hc in zip(low_rgb, high_rgb)
            )
    return _SURFACE_STOPS[-1][1]


def _encode_png_rgba(pixels: bytes, width: int, height: int) -> bytes:
    """RGBA（8bit, color type 6）の生バイト列を PNG にエンコードする."""

    stride = width * 4
    raw = b"".join(b"\x00" + pixels[y * stride : (y + 1) * stride] for y in range(height))
    png = b"\x89PNG\r\n\x1a\n" + _png_chunk(
        b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    )
    png += _png_chunk(b"IDAT", zlib.compress(raw, 9))
    png += _png_chunk(b"IEND", b"")
    return png


def _surface_legend_html(place: str) -> str:
    return f"""
    <div style="
      position: fixed; bottom: 24px; left: 24px; z-index: 9999;
      background: white; padding: 10px 12px; border: 1px solid #d1d5db;
      border-radius: 6px; font-size: 13px; box-shadow: 0 1px 4px #0002;">
      <div style="font-weight: 700; margin-bottom: 6px;">近接性 S（補間サーフェス）: {place}</div>
      <div style="display:flex; align-items:center; gap:8px;">
        <span>低</span>
        <span style="display:inline-block; width:120px; height:10px;
          background: linear-gradient(90deg, #dc2626, #f59e0b, #15803d);"></span>
        <span>高</span>
      </div>
      <div style="margin-top:4px; color:#6b7280;">格子点を線形補間。データ範囲外は非表示。</div>
    </div>
    """
