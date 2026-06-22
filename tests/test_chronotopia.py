import pytest

from nmincity.config import CATEGORY_WEIGHTS
from nmincity.core.chronotopia import (
    category_availability,
    proximity_score_at,
    reachable_categories_at,
    time_variation,
)


def test_category_availability_defaults_and_profiles():
    assert category_availability("education", "evening") == 0.2
    assert category_availability("transit", "evening") == 1.0
    assert category_availability("unknown", "evening") == 1.0


def test_reachable_categories_at_applies_availability_and_conversion():
    reach = {category: False for category in CATEGORY_WEIGHTS}
    reach["education"] = True
    reach["goods"] = True

    result = reachable_categories_at(reach, "evening")

    assert set(result) == set(CATEGORY_WEIGHTS)
    assert result["education"] == 0.2
    assert result["goods"] == 0.8
    assert result["leisure"] >= 0.7


def test_time_variation_is_score_range():
    assert time_variation({"morning": 0.3, "daytime": 0.9, "evening": 0.5}) == pytest.approx(0.6)
    assert time_variation({"morning": 0.4, "daytime": 0.4, "evening": 0.4}) == 0.0


def test_proximity_score_at_matches_weighted_availability_sum():
    reach = {category: False for category in CATEGORY_WEIGHTS}
    reach["education"] = True
    reach["transit"] = True

    indicators = reachable_categories_at(reach, "evening")
    expected = sum(CATEGORY_WEIGHTS[key] * indicators[key] for key in CATEGORY_WEIGHTS)

    assert proximity_score_at(reach, "evening") == pytest.approx(expected)
