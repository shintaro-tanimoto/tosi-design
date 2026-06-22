import networkx as nx

from nmincity.core.score import quality_score
from nmincity.core.walkability import (
    effective_travel_time,
    impedance_factor,
    origin_quality,
    segment_indicators,
)


def test_segment_indicators_footway_is_high_quality():
    indicators = segment_indicators({"highway": "footway"})

    assert indicators["sidewalk"] == 1.0
    assert indicators["traffic_separation"] == 1.0


def test_segment_indicators_sidewalk_both_on_residential():
    indicators = segment_indicators({"highway": "residential", "sidewalk": "both"})

    assert indicators["sidewalk"] == 1.0
    assert indicators["traffic_separation"] == 0.7


def test_segment_indicators_high_speed_primary_suppresses_separation():
    indicators = segment_indicators({"highway": "primary", "maxspeed": "60"})

    assert indicators["traffic_separation"] <= 0.3


def test_segment_indicators_missing_tags_are_neutral_and_in_range():
    indicators = segment_indicators({})

    assert 0.0 <= indicators["sidewalk"] <= 1.0
    assert 0.0 <= indicators["traffic_separation"] <= 1.0
    assert indicators["sidewalk"] == 0.5
    assert indicators["traffic_separation"] == 0.5


def test_segment_indicators_accepts_list_values():
    indicators = segment_indicators({"highway": ["residential", "service"]})

    assert indicators["sidewalk"] == 0.5
    assert indicators["traffic_separation"] == 0.7


def test_impedance_factor_rules_and_monotonicity():
    assert impedance_factor(1.0, 1.0) == 1.0
    assert impedance_factor(0.2, 0.0) == 1.0
    assert impedance_factor(0.0, 1.0) == 2.0
    assert impedance_factor(0.2, 1.0) > impedance_factor(0.8, 1.0)


def test_effective_travel_time_scales_base_time():
    assert effective_travel_time(60.0, 1.0, 1.0) == 60.0
    assert effective_travel_time(60.0, 0.0, 1.0) == 120.0


def test_origin_quality_averages_reachable_edge_indicators():
    graph = nx.MultiDiGraph()
    graph.add_edge(
        "A",
        "B",
        walk_indicators={
            "sidewalk": 1.0,
            "traffic_separation": 0.5,
            "greenery": 0.0,
            "active_frontage": 0.5,
            "water_scenery": 1.0,
        },
    )
    graph.add_edge(
        "B",
        "C",
        walk_indicators={
            "sidewalk": 0.0,
            "traffic_separation": 0.5,
            "greenery": 1.0,
            "active_frontage": 0.5,
            "water_scenery": 0.0,
        },
    )
    expected = quality_score(
        {
            "sidewalk": 0.5,
            "traffic_separation": 0.5,
            "greenery": 0.5,
            "active_frontage": 0.5,
            "water_scenery": 0.5,
        }
    )

    assert origin_quality(graph, {"A", "B", "C"}) == expected


def test_origin_quality_without_reachable_edges_is_zero():
    graph = nx.MultiDiGraph()
    graph.add_edge("A", "B")

    assert origin_quality(graph, {"A"}) == 0.0
