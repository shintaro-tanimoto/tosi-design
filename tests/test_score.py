from nmincity.config import CATEGORY_WEIGHTS, QUALITY_WEIGHTS
from nmincity.core.score import proximity_score, quality_score


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
    expected = sum(QUALITY_WEIGHTS[key] * value for key, value in indicators.items())
    assert quality_score(indicators) == expected

