"""可視化データ整形ヘルパのテスト（描画ライブラリ非依存）."""

from __future__ import annotations

import folium

from nmincity.config import CATEGORY_NAMES
from nmincity.viz.maps import (
    _score_color_rgb,
    category_layer_points,
    category_surfaces_map,
    facility_layers_map,
    score_mesh_map,
    score_surface_map,
)


def test_category_layer_points_covers_all_categories():
    reach_by_origin = {
        "a": {"education": True, "nature": False},
        "b": {"education": False, "goods": True},
    }
    latlon_by_origin = {"a": (34.6, 135.5), "b": (34.7, 135.6)}

    result = category_layer_points(reach_by_origin, latlon_by_origin)

    # 全7カテゴリがキーになる
    assert set(result) == set(CATEGORY_NAMES)
    # 各カテゴリに全起点ぶんの点が入る
    for points in result.values():
        assert len(points) == 2


def test_category_layer_points_reflects_reach_flags():
    reach_by_origin = {"a": {"education": True}, "b": {"education": False}}
    latlon_by_origin = {"a": (34.6, 135.5), "b": (34.7, 135.6)}

    result = category_layer_points(reach_by_origin, latlon_by_origin)
    education = {(lat, lon): reachable for lat, lon, reachable in result["education"]}

    assert education[(34.6, 135.5)] is True
    assert education[(34.7, 135.6)] is False
    # 未指定カテゴリは False 既定
    assert all(reachable is False for _lat, _lon, reachable in result["nature"])


def test_category_layer_points_skips_origins_without_coords():
    reach_by_origin = {"a": {"education": True}, "b": {"education": True}}
    latlon_by_origin = {"a": (34.6, 135.5)}  # b は座標なし

    result = category_layer_points(reach_by_origin, latlon_by_origin)

    assert len(result["education"]) == 1


def test_facility_layers_map_returns_map_with_category_groups():
    facilities = {category: [] for category in CATEGORY_NAMES}
    facilities["education"] = [(34.65, 135.51), (34.66, 135.52)]
    facilities["nature"] = [(34.64, 135.50)]

    m = facility_layers_map(facilities, "天王寺区")

    assert isinstance(m, folium.Map)
    # カテゴリごとに FeatureGroup を持つ（7要素ぶん）
    group_count = sum(
        1 for child in m._children.values() if isinstance(child, folium.FeatureGroup)
    )
    assert group_count == len(CATEGORY_NAMES)


def test_category_surfaces_map_has_overlay_per_nonempty_category():
    category_points = {category: [] for category in CATEGORY_NAMES}
    # 非同一直線上の点で補間できる四隅（到達/未到達混在）
    category_points["education"] = [
        (34.64, 135.50, True),
        (34.66, 135.50, False),
        (34.64, 135.52, True),
        (34.66, 135.52, False),
    ]
    # 全て同値（全未到達）でも例外を出さず面が乗ること
    category_points["goods"] = [
        (34.64, 135.50, False),
        (34.66, 135.52, False),
        (34.64, 135.52, False),
    ]

    m = category_surfaces_map(category_points, "天王寺区", resolution=16)

    assert isinstance(m, folium.Map)
    groups = [c for c in m._children.values() if isinstance(c, folium.FeatureGroup)]
    # 7要素ぶんの FeatureGroup（空カテゴリも切替枠として残す）
    assert len(groups) == len(CATEGORY_NAMES)
    overlay_count = sum(
        1
        for group in groups
        for child in group._children.values()
        if isinstance(child, folium.raster_layers.ImageOverlay)
    )
    # 点を持つ education / goods にだけ補間面が乗る
    assert overlay_count == 2


def test_score_mesh_map_draws_polygon_per_cell():
    cells = [
        ([(34.64, 135.50), (34.64, 135.51), (34.65, 135.51), (34.65, 135.50)], 1.0, "良好"),
        ([(34.65, 135.50), (34.65, 135.51), (34.66, 135.51), (34.66, 135.50)], 0.2, "不足"),
    ]

    m = score_mesh_map(cells, "天王寺区")

    assert isinstance(m, folium.Map)
    polygons = sum(1 for child in m._children.values() if isinstance(child, folium.vector_layers.Polygon))
    assert polygons == 2


def test_score_surface_map_overlays_interpolated_raster():
    # 4点格子（S が東に向かって上昇）→ 補間サーフェスが1枚重なる
    points = [
        (34.64, 135.50, 0.1),
        (34.64, 135.52, 0.9),
        (34.66, 135.50, 0.2),
        (34.66, 135.52, 1.0),
    ]

    m = score_surface_map(points, "天王寺区", resolution=24)

    assert isinstance(m, folium.Map)
    overlays = sum(
        1
        for child in m._children.values()
        if isinstance(child, folium.raster_layers.ImageOverlay)
    )
    assert overlays == 1


def test_score_color_rgb_ramps_red_to_green():
    assert _score_color_rgb(0.0) == (220, 38, 38)
    assert _score_color_rgb(1.0) == (21, 128, 61)
    # 中間はおおむね橙
    red, green, _blue = _score_color_rgb(0.5)
    assert red > 200 and green > 120
