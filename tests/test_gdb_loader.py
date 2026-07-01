"""gdb_loader の整形・集計ロジックのテスト（実 .gdb 非依存）.

OpenFileGDB は読取専用ドライバのため、書込可能な GeoPackage(.gpkg) に
合成データ（EPSG:2448 + S + reach_* + POP）を書いて読み直し、
再投影・タプル化・人口加重の到達率/サマリを検証する。
"""

from __future__ import annotations

import geopandas as gpd
from shapely.geometry import Point

from nmincity.config import CATEGORY_NAMES
from nmincity.data import gdb_loader


def _write_score_gpkg(tmp_path, *, with_reach=True, with_pop=True):
    # 大阪・平面直角VI系(EPSG:2448)の座標を2点。
    data = {
        "S": [1.0, 0.0],
        "label": ["良好", "不足"],
    }
    if with_pop:
        data["POP"] = [300.0, 100.0]
    if with_reach:
        # education: 起点1のみ到達 / nature: 両方到達
        data["reach_education"] = [1, 0]
        data["reach_nature"] = [1, 1]
    geometry = [Point(-45980.0, -150457.0), Point(-45000.0, -149000.0)]
    gdf = gpd.GeoDataFrame(data, geometry=geometry, crs="EPSG:2448")
    path = tmp_path / "score.gpkg"
    gdf.to_file(path, layer="score", driver="GPKG")
    return str(path)


def test_load_score_points_reprojects_to_4326(tmp_path):
    path = _write_score_gpkg(tmp_path)
    points = gdb_loader.load_score_points(path, "score")

    assert len(points) == 2
    for lat, lon, score in points:
        # 大阪付近（4326）に再投影されている
        assert 34.0 < lat < 35.5
        assert 135.0 < lon < 136.5
        assert isinstance(score, float)


def test_load_reach_profile_population_weighted(tmp_path):
    path = _write_score_gpkg(tmp_path)
    profile = gdb_loader.load_reach_profile(path, "score")

    assert profile is not None
    # education: POP加重 = (300*1 + 100*0) / 400 = 0.75
    assert profile["education"] == 0.75
    # nature: 両方到達 = 1.0
    assert profile["nature"] == 1.0
    # 未提供カテゴリは 0.0、全カテゴリがキー
    assert set(profile) == set(CATEGORY_NAMES)
    assert profile["goods"] == 0.0


def test_load_reach_profile_returns_none_without_reach_columns(tmp_path):
    path = _write_score_gpkg(tmp_path, with_reach=False)
    assert gdb_loader.load_reach_profile(path, "score") is None


def test_load_category_reach_points_per_origin(tmp_path):
    path = _write_score_gpkg(tmp_path)
    result = gdb_loader.load_category_reach_points(path, "score")

    assert result is not None
    assert set(result) == set(CATEGORY_NAMES)
    # education: 起点1=到達 / 起点2=未到達（行順は保たれる）
    education = result["education"]
    assert len(education) == 2
    assert [reached for _lat, _lon, reached in education] == [True, False]
    for lat, lon, _reached in education:
        assert 34.0 < lat < 35.5 and 135.0 < lon < 136.5
    # nature は両方到達
    assert [reached for _lat, _lon, reached in result["nature"]] == [True, True]
    # 列の無いカテゴリは空リスト
    assert result["goods"] == []


def test_load_category_reach_points_returns_none_without_reach_columns(tmp_path):
    path = _write_score_gpkg(tmp_path, with_reach=False)
    assert gdb_loader.load_category_reach_points(path, "score") is None


def test_load_score_summary_population_weighted(tmp_path):
    path = _write_score_gpkg(tmp_path)
    summary = gdb_loader.load_score_summary(path, "score")

    assert summary["origins"] == 2
    assert summary["pop_weighted"] is True
    # mean S = (300*1.0 + 100*0.0) / 400 = 0.75
    assert summary["mean_s"] == 0.75
    assert summary["labels"]["良好"] == 1
    assert summary["labels"]["不足"] == 1


def test_load_score_summary_unweighted_without_pop(tmp_path):
    path = _write_score_gpkg(tmp_path, with_pop=False)
    summary = gdb_loader.load_score_summary(path, "score")

    assert summary["pop_weighted"] is False
    # 単純平均 = (1.0 + 0.0)/2 = 0.5
    assert summary["mean_s"] == 0.5
