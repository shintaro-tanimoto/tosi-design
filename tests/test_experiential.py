import pytest

from nmincity.config import CATEGORY_WEIGHTS
from nmincity.core.experiential import (
    category_mix,
    experiential_indicators,
    lingering,
    liveliness,
    topophilia,
)


def test_category_mix_ratio():
    assert category_mix({category: True for category in CATEGORY_WEIGHTS}) == 1.0
    assert category_mix({category: False for category in CATEGORY_WEIGHTS}) == 0.0

    reach = {category: False for category in CATEGORY_WEIGHTS}
    for category in list(CATEGORY_WEIGHTS)[:3]:
        reach[category] = True
    assert category_mix(reach) == pytest.approx(3 / 7)


def test_experiential_components_clamp_and_are_monotonic():
    assert liveliness(-1.0, 2.0) == 0.5
    assert lingering(-1.0, 2.0) == 0.5
    assert topophilia(-1.0, 2.0) == 0.5

    assert liveliness(0.8, 0.5) > liveliness(0.2, 0.5)
    assert lingering(0.8, 0.5) > lingering(0.2, 0.5)
    assert topophilia(0.8, 0.5) > topophilia(0.2, 0.5)


def test_experiential_indicators_keys_and_time_variation():
    result = experiential_indicators(
        active_frontage=0.8,
        leisure_proximity=0.6,
        water_proximity=0.4,
        greenery=0.2,
        reach={category: True for category in CATEGORY_WEIGHTS},
        time_var=0.35,
    )

    assert set(result) == {"liveliness", "lingering", "topophilia", "time_variation"}
    assert result["time_variation"] == 0.35
