from nmincity.config import CATEGORY_WEIGHTS, QUALITY_WEIGHTS, WALK_QUALITY_WEIGHTS
from nmincity.core.score import environment_quality, proximity_score, quality_score


def test_proximity_score_all_true_is_one():
    reach = {category: True for category in CATEGORY_WEIGHTS}
    assert proximity_score(reach) == 1.0


def test_proximity_score_all_false_is_zero():
    reach = {category: False for category in CATEGORY_WEIGHTS}
    assert proximity_score(reach) == 0.0


def test_proximity_score_education_and_nature():
    reach = {category: False for category in CATEGORY_WEIGHTS}
    reach["education"] = True
    reach["nature"] = True
    assert proximity_score(reach) == 0.36


def test_quality_score_equal_weights():
    indicators = {
        "sidewalk": 1.0,
        "traffic_separation": 0.5,
        "greenery": 0.0,
        "active_frontage": 0.5,
        "water_scenery": 1.0,
    }
    expected = sum(WALK_QUALITY_WEIGHTS[key] * value for key, value in indicators.items())
    assert quality_score(indicators, WALK_QUALITY_WEIGHTS) == expected


def test_environment_quality_uses_top_level_quality_weights():
    experiential = {
        "liveliness": 0.5,
        "lingering": 0.25,
        "topophilia": 0.75,
        "time_variation": 0.1,
    }
    expected = QUALITY_WEIGHTS["walkability"] * 0.8
    expected += sum(QUALITY_WEIGHTS[key] * value for key, value in experiential.items())

    assert environment_quality(0.8, experiential) == expected
