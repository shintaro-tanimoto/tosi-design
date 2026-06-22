from dataclasses import FrozenInstanceError, fields, is_dataclass

import pytest

from nmincity.config import CATEGORY_WEIGHTS, TIME_CONVERSIONS
from nmincity.core.proposals import (
    Proposal,
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
    reach_by_origin["c"]["education"] = False
    reach_by_origin["c"]["leisure"] = False
    reach_by_origin["c"]["work"] = False

    deficiencies = find_deficiencies(reach_by_origin)

    assert deficiencies["a"] == []
    assert deficiencies["b"] == sorted(
        CATEGORY_WEIGHTS,
        key=lambda category: (-CATEGORY_WEIGHTS[category], category),
    )
    assert deficiencies["c"] == ["education", "leisure", "work"]


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
    assert by_facility["school-1"].priority == pytest.approx(CATEGORY_WEIGHTS["health"] * 5.0)
    assert by_facility["school-1"].source_category == "education"
    assert by_facility["hall-1"].affected_population == 8.0
    assert by_facility["hall-1"].priority == pytest.approx(CATEGORY_WEIGHTS["health"] * 8.0)


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
