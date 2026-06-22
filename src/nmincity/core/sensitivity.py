"""重み感度分析とシナリオ比較の純粋ロジック."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from nmincity.config import CATEGORY_WEIGHTS, score_label
from nmincity.core.proposals import Proposal, apply_proposals
from nmincity.core.score import normalize, proximity_score


def reach_rate(
    reach_by_origin: Mapping[Any, Mapping[str, bool]],
    categories: list[str] | tuple[str, ...] | None = None,
) -> dict[str, float]:
    """各カテゴリに到達する起点の割合を返す.

    これはデータ側の性質であり、重みには依存しない。起点がない場合は
    全カテゴリ 0.0 とする。
    """

    selected_categories = list(CATEGORY_WEIGHTS) if categories is None else list(categories)
    origin_count = len(reach_by_origin)
    if origin_count == 0:
        return {category: 0.0 for category in selected_categories}
    return {
        category: sum(
            1 for reach in reach_by_origin.values() if bool(reach.get(category, False))
        )
        / origin_count
        for category in selected_categories
    }


def mean_score(
    reach_by_origin: Mapping[Any, Mapping[str, bool]],
    weights: Mapping[str, float] | None = None,
) -> float:
    """起点平均の近接性スコア ``mean_i S(i)`` を返す."""

    if not reach_by_origin:
        return 0.0
    return sum(proximity_score(reach, weights) for reach in reach_by_origin.values()) / len(reach_by_origin)


def score_distribution(
    reach_by_origin: Mapping[Any, Mapping[str, bool]],
    weights: Mapping[str, float] | None = None,
) -> dict[str, float]:
    """シナリオ比較用に平均・最小・最大と評価ラベル件数を返す."""

    scores = [proximity_score(reach, weights) for reach in reach_by_origin.values()]
    if not scores:
        return {
            "mean": 0.0,
            "min": 0.0,
            "max": 0.0,
            "label_good": 0.0,
            "label_needs_improvement": 0.0,
            "label_deficient": 0.0,
        }

    labels = [score_label(score) for score in scores]
    return {
        "mean": sum(scores) / len(scores),
        "min": min(scores),
        "max": max(scores),
        "label_good": float(labels.count("良好")),
        "label_needs_improvement": float(labels.count("要改善")),
        "label_deficient": float(labels.count("不足")),
    }


def category_sensitivity(
    reach_by_origin: Mapping[Any, Mapping[str, bool]],
    weights: Mapping[str, float] | None = None,
    *,
    delta: float = 0.05,
) -> dict[str, float]:
    """カテゴリ重みを一つずつ増やした時の平均 S の変化量を返す.

    ``mean_i S(i)=Σ_c normalized(w_c) * reach_rate[c]`` なので、符号は
    対象カテゴリの到達率が現在の平均より高いか低いかで透明に読める。
    """

    selected_weights = normalize(CATEGORY_WEIGHTS if weights is None else weights)
    if delta < 0:
        raise ValueError("delta must be non-negative")
    baseline = mean_score(reach_by_origin, selected_weights)
    if delta == 0:
        return {category: 0.0 for category in selected_weights}

    result: dict[str, float] = {}
    for category in selected_weights:
        changed = dict(selected_weights)
        changed[category] = changed.get(category, 0.0) + delta
        result[category] = mean_score(reach_by_origin, normalize(changed)) - baseline
    return result


def weight_scenarios(
    base_weights: Mapping[str, float] | None = None,
) -> dict[str, dict[str, float]]:
    """比較用の正規化済みカテゴリ重みシナリオを返す."""

    baseline = normalize(CATEGORY_WEIGHTS if base_weights is None else base_weights)
    equal = normalize({category: 1.0 for category in baseline})
    education_heavy = _boosted(baseline, "education", factor=2.0)
    nature_heavy = _boosted(baseline, "nature", factor=2.0)
    return {
        "baseline": baseline,
        "equal": equal,
        "education_heavy": education_heavy,
        "nature_heavy": nature_heavy,
    }


def compare_scenarios(
    reach_by_origin: Mapping[Any, Mapping[str, bool]],
    proposals: list[Proposal],
    scenarios: Mapping[str, Mapping[str, float]] | None = None,
) -> dict[str, dict[str, float]]:
    """重み変更後と提案実施後のスコア分布を並置する."""

    selected_scenarios = weight_scenarios() if scenarios is None else {
        name: normalize(weights) for name, weights in scenarios.items()
    }
    comparison = {
        name: score_distribution(reach_by_origin, weights)
        for name, weights in selected_scenarios.items()
    }
    applied = apply_proposals(reach_by_origin, proposals)
    comparison["proposals_applied"] = score_distribution(applied, CATEGORY_WEIGHTS)
    return comparison


def _boosted(weights: Mapping[str, float], category: str, *, factor: float) -> dict[str, float]:
    boosted = dict(weights)
    if category in boosted:
        boosted[category] = boosted[category] * factor
    return normalize(boosted)
