"""n分都市度スコアと質スコアの純粋計算."""

from __future__ import annotations

from collections.abc import Mapping

from nmincity.config import CATEGORY_WEIGHTS, QUALITY_WEIGHTS


def normalize(weights: Mapping[str, float]) -> dict[str, float]:
    """重み辞書を合計 1.0 に正規化して返す."""

    total = float(sum(weights.values()))
    if total <= 0:
        raise ValueError("weight total must be positive")
    if any(value < 0 for value in weights.values()):
        raise ValueError("weights must be non-negative")
    return {key: float(value) / total for key, value in weights.items()}


def proximity_score(
    reach: Mapping[str, bool],
    weights: Mapping[str, float] | None = None,
) -> float:
    """近接性スコア ``S(i)=Σ w_c*a(i,c)`` を返す."""

    selected_weights = CATEGORY_WEIGHTS if weights is None else weights
    normalized = normalize(selected_weights)
    score = sum(weight * float(bool(reach.get(category, False))) for category, weight in normalized.items())
    return _clamp_unit(score)


def quality_score(
    indicators: Mapping[str, float],
    weights: Mapping[str, float] | None = None,
) -> float:
    """環境の質スコア ``Q(i)=Σ v_q*b(i,q)`` を返す.

    ``indicators`` の値は 0..1 の範囲にあることを要求する。未指定の指標は
    0 とみなす。
    """

    selected_weights = QUALITY_WEIGHTS if weights is None else weights
    normalized = normalize(selected_weights)
    score = 0.0
    for key, weight in normalized.items():
        value = float(indicators.get(key, 0.0))
        _require_unit_interval(value, key)
        score += weight * value
    return _clamp_unit(score)


def integrated_score(s: float, q: float, alpha: float = 1.0) -> float:
    """任意シナリオ用の統合スコア ``S*=S*f(Q)`` を返す.

    要件定義書 §6.7.1 は近接性 ``S`` と質 ``Q`` を既定では合成せず、
    並置して診断する方針を取る。この関数は統合ビューを別シナリオで
    試すために提供するだけで、通常のスコア計算では呼ばない。
    """

    _require_unit_interval(s, "s")
    _require_unit_interval(q, "q")
    if alpha < 0:
        raise ValueError("alpha must be non-negative")
    return _clamp_unit(s * (1.0 - alpha + alpha * q))


def _require_unit_interval(value: float, name: str) -> None:
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be between 0 and 1, got {value}")


def _clamp_unit(value: float) -> float:
    return max(0.0, min(1.0, float(value)))

