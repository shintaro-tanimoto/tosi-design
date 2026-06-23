from dataclasses import FrozenInstanceError, is_dataclass

import pytest

from nmincity.core.allocation import AllocationResult, coverage_rate, maximize_coverage


def test_greedy_k1_selects_best_marginal_gain():
    result = maximize_coverage(
        {
            "a": ["o1", "o2"],
            "b": ["o3"],
            "c": ["o2", "o3"],
        },
        {"o1": 1.0, "o2": 2.0, "o3": 4.0},
        1,
        solver="greedy",
        target_category="health",
    )

    assert result.selected == ("c",)
    assert result.covered_origins == ("o2", "o3")
    assert result.total_gain == 6.0
    assert result.method == "greedy"
    assert result.target_category == "health"


def test_greedy_k2_uses_union_coverage_without_double_counting():
    result = maximize_coverage(
        {
            "a": ["o1", "o2"],
            "b": ["o2", "o3"],
            "c": ["o3"],
        },
        {"o1": 3.0, "o2": 5.0, "o3": 7.0},
        2,
        solver="greedy",
    )

    assert result.selected == ("a", "b")
    assert result.covered_origins == ("o1", "o2", "o3")
    assert result.total_gain == 15.0


def test_empty_when_k_non_positive_or_no_candidates():
    result = maximize_coverage({"a": ["o1"]}, {"o1": 1.0}, 0, solver="greedy")
    assert result.selected == ()
    assert result.covered_origins == ()
    assert result.total_gain == 0.0

    result = maximize_coverage({}, {"o1": 1.0}, 2, solver="greedy")
    assert result.selected == ()
    assert result.covered_origins == ()
    assert result.total_gain == 0.0


def test_pulp_solution_gain_is_at_least_greedy():
    pytest.importorskip("pulp")

    candidate_cover = {
        "a": ["o1", "o2"],
        "b": ["o2", "o3"],
        "c": ["o4"],
    }
    origin_gain = {"o1": 3.0, "o2": 4.0, "o3": 5.0, "o4": 6.0}

    greedy = maximize_coverage(candidate_cover, origin_gain, 2, solver="greedy")
    exact = maximize_coverage(candidate_cover, origin_gain, 2, solver="pulp")

    assert exact.method == "pulp"
    assert exact.total_gain >= greedy.total_gain


def test_auto_uses_pulp_when_available():
    pytest.importorskip("pulp")

    result = maximize_coverage({"a": ["o1"]}, {"o1": 1.0}, 1, solver="auto")

    assert result.method == "pulp"


def test_allocation_result_is_frozen_dataclass():
    assert is_dataclass(AllocationResult)
    result = AllocationResult(("a",), ("o1",), 1.0, "greedy")

    with pytest.raises(FrozenInstanceError):
        result.total_gain = 2.0


def test_coverage_rate_before_and_after():
    reach_by_origin = {
        "o1": {"health": True},
        "o2": {"health": False},
        "o3": {"health": False},
        "o4": {"health": True},
    }

    assert coverage_rate(reach_by_origin, "health") == 0.5
    assert coverage_rate(reach_by_origin, "health", covered_origins=("o2",)) == 0.75
    assert coverage_rate({}, "health") == 0.0
