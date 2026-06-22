import pytest

from nmincity.config import CATEGORY_WEIGHTS
from nmincity.core.proposals import Proposal
from nmincity.core.score import normalize
from nmincity.core.sensitivity import (
    category_sensitivity,
    compare_scenarios,
    mean_score,
    reach_rate,
    weight_scenarios,
)


def test_reach_rate_matches_manual_counts():
    reach_by_origin = _reach_fixture()

    rates = reach_rate(reach_by_origin, categories=("education", "nature", "goods"))

    assert rates == {
        "education": pytest.approx(2 / 3),
        "nature": pytest.approx(1 / 3),
        "goods": pytest.approx(0.0),
    }


def test_mean_score_matches_weighted_reach_rate_linearity():
    reach_by_origin = _reach_fixture()
    rates = reach_rate(reach_by_origin)
    weights = normalize(CATEGORY_WEIGHTS)

    expected = sum(weights[category] * rates[category] for category in weights)

    assert mean_score(reach_by_origin) == pytest.approx(expected)


def test_category_sensitivity_signs_and_zero_delta():
    reach_by_origin = _reach_fixture()

    sensitivity = category_sensitivity(reach_by_origin, delta=0.05)
    zero_delta = category_sensitivity(reach_by_origin, delta=0)

    assert sensitivity["education"] > 0
    assert sensitivity["goods"] < 0
    assert all(value == 0.0 for value in zero_delta.values())


def test_weight_scenarios_are_normalized_and_boost_expected_categories():
    scenarios = weight_scenarios()

    assert set(scenarios) >= {"baseline", "equal", "education_heavy", "nature_heavy"}
    for weights in scenarios.values():
        assert sum(weights.values()) == pytest.approx(1.0)
    assert scenarios["education_heavy"]["education"] > scenarios["baseline"]["education"]
    assert scenarios["nature_heavy"]["nature"] > scenarios["baseline"]["nature"]


def test_compare_scenarios_proposals_applied_is_monotonic():
    reach_by_origin = _reach_fixture()
    proposal = Proposal(
        kind="multifunction",
        target_category="goods",
        source_category="education",
        time_bucket=None,
        facility="school-1",
        affected_population=2.0,
        priority=1.0,
        rationale="test",
        affected_origins=("a", "b"),
    )

    comparison = compare_scenarios(reach_by_origin, [proposal])

    assert comparison["proposals_applied"]["mean"] >= comparison["baseline"]["mean"]


def _reach_fixture():
    base = {category: False for category in CATEGORY_WEIGHTS}
    return {
        "a": {**base, "education": True, "nature": True},
        "b": {**base, "education": True},
        "c": base.copy(),
    }
