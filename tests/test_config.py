from nmincity.config import CATEGORY_WEIGHTS, QUALITY_WEIGHTS, score_label


def test_category_weights_sum_to_one():
    assert abs(sum(CATEGORY_WEIGHTS.values()) - 1.0) <= 1e-9


def test_quality_weights_sum_to_one():
    assert abs(sum(QUALITY_WEIGHTS.values()) - 1.0) <= 1e-9


def test_score_label_boundaries():
    assert score_label(0.8) == "良好"
    assert score_label(0.5) == "要改善"
    assert score_label(0.49) == "不足"

