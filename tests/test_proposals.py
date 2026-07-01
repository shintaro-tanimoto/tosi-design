from dataclasses import FrozenInstanceError, fields, is_dataclass

import pytest

from nmincity.config import CATEGORY_WEIGHTS, TIME_CONVERSIONS
from nmincity.core.proposals import (
    Proposal,
    apply_proposals,
    find_deficiencies,
    multifunction_proposals,
    rank_proposals,
    time_conversion_proposals,
)


def test_find_deficiencies_orders_missing_categories_by_weight():
    reach_by_origin = {
        "a": {category: True for category in CATEGORY_WEIGHTS},
        "b": {category: False for category in CATEGORY_WEIGHTS},
        "c": {category: True for category in CATEGORY_WEIGHTS},
    }
    # "c" は S=0.60（>=0.5）の非・不足エリア。高重みの education 欠落だけが対象になる。
    reach_by_origin["c"]["education"] = False
    reach_by_origin["c"]["leisure"] = False
    reach_by_origin["c"]["work"] = False

    deficiencies = find_deficiencies(reach_by_origin)

    assert deficiencies["a"] == []
    assert deficiencies["b"] == sorted(
        CATEGORY_WEIGHTS,
        key=lambda category: (-CATEGORY_WEIGHTS[category], category),
    )
    assert deficiencies["c"] == ["education"]


def test_find_deficiencies_filters_low_weight_gaps_outside_deficient_areas():
    """§6.6-1: 非・不足エリア（S>=しきい値）は高重みカテゴリの欠落のみ提案対象."""

    healthy = {category: True for category in CATEGORY_WEIGHTS}
    low_weight_gap = dict(healthy, leisure=False, work=False)  # S=0.78
    deficient = {category: False for category in CATEGORY_WEIGHTS}
    deficient["transit"] = True  # S=0.13 < 0.5

    deficiencies = find_deficiencies({"ok": low_weight_gap, "bad": deficient})

    assert deficiencies["ok"] == []
    assert "leisure" in deficiencies["bad"] and "work" in deficiencies["bad"]

    # しきい値を全カテゴリが高重み扱いになる値へ下げると従来挙動に戻る（透明なパラメータ）
    relaxed = find_deficiencies({"ok": low_weight_gap}, high_weight_threshold=0.0)
    assert relaxed["ok"] == ["leisure", "work"]


def test_time_conversion_proposals_counts_only_reachable_source_origins():
    deficiencies = {
        "a": ["leisure"],
        "b": ["leisure"],
        "c": ["leisure"],
        "d": ["health"],
    }
    source_reach_by_origin = {
        "a": {"education": True},
        "b": {"education": False},
        "c": {"education": True},
        "d": {"education": True},
    }

    result = time_conversion_proposals(
        deficiencies,
        source_reach_by_origin,
        conversions=TIME_CONVERSIONS,
    )

    proposal = next(item for item in result if item.target_category == "leisure")
    assert proposal.kind == "time_conversion"
    assert proposal.time_bucket == "evening"
    assert proposal.source_category == "education"
    assert proposal.affected_population == 2.0
    assert proposal.affected_origins == ("a", "c")
    assert proposal.priority == pytest.approx(CATEGORY_WEIGHTS["leisure"] * 2)


def test_rank_proposals_orders_by_priority_and_applies_top_n():
    proposals = [
        _proposal("health", 0.2, 2.0),
        _proposal("leisure", 0.5, 1.0),
        _proposal("goods", 0.5, 3.0),
    ]

    ranked = rank_proposals(proposals, top_n=2)

    assert [proposal.target_category for proposal in ranked] == ["goods", "leisure"]


def test_multifunction_proposals_aggregates_population_by_facility():
    deficiencies = {
        "a": ["health"],
        "b": ["health"],
        "c": ["health"],
    }
    nearby_convertible = {
        "a": {"health": {("school-1", "education")}},
        "b": {"health": {("school-1", "education"), ("hall-1", "leisure")}},
        "c": {"health": {("hall-1", "leisure")}},
    }
    population = {"a": 2.0, "b": 3.0, "c": 5.0}

    result = multifunction_proposals(deficiencies, nearby_convertible, population)
    by_facility = {proposal.facility: proposal for proposal in result}

    assert by_facility["school-1"].affected_population == 5.0
    assert by_facility["school-1"].affected_origins == ("a", "b")
    assert by_facility["school-1"].priority == pytest.approx(CATEGORY_WEIGHTS["health"] * 5.0)
    assert by_facility["school-1"].source_category == "education"
    assert by_facility["hall-1"].affected_population == 8.0
    assert by_facility["hall-1"].affected_origins == ("b", "c")
    assert by_facility["hall-1"].priority == pytest.approx(CATEGORY_WEIGHTS["health"] * 8.0)


def test_apply_proposals_marks_targets_without_mutating_input():
    reach_by_origin = {
        "a": {"health": False, "education": True},
        "b": {"health": False, "education": False},
        "c": {"health": False, "education": False},
    }
    proposal = Proposal(
        kind="multifunction",
        target_category="health",
        source_category="education",
        time_bucket=None,
        facility="school-1",
        affected_population=2.0,
        priority=1.0,
        rationale="test",
        affected_origins=("a", "b"),
    )

    updated = apply_proposals(reach_by_origin, [proposal])

    assert updated["a"]["health"] is True
    assert updated["b"]["health"] is True
    assert updated["c"]["health"] is False
    assert reach_by_origin["a"]["health"] is False


def test_proposal_is_frozen_dataclass_with_required_fields():
    assert is_dataclass(Proposal)
    assert {field.name for field in fields(Proposal)} == {
        "kind",
        "target_category",
        "source_category",
        "time_bucket",
        "facility",
        "affected_population",
        "priority",
        "rationale",
        "affected_origins",
    }
    proposal = _proposal("leisure", 1.0, 1.0)

    with pytest.raises(FrozenInstanceError):
        proposal.priority = 2.0


def _proposal(target_category: str, priority: float, affected_population: float) -> Proposal:
    return Proposal(
        kind="multifunction",
        target_category=target_category,
        source_category=None,
        time_bucket=None,
        facility=None,
        affected_population=affected_population,
        priority=priority,
        rationale="test",
    )
