"""§6.7 要素C: 体験指標を扱う純粋計算.

体験指標は OSM タグや到達カテゴリから作る代理指標であり、観察調査や
実測の代替ではない。近接性 ``S`` と環境の質 ``Q`` は既定では合成せず、
並置して診断する。
"""

from __future__ import annotations

from collections.abc import Mapping

from nmincity.config import CATEGORY_WEIGHTS


def liveliness(active_frontage: float, category_mix: float) -> float:
    """にぎわい代理指標として、沿道活気と用途混在度の平均を返す."""

    return _clamp_unit((_clamp_unit(active_frontage) + _clamp_unit(category_mix)) / 2.0)


def lingering(leisure_proximity: float, water_proximity: float) -> float:
    """滞留代理指標として、余暇施設と水辺への近接の平均を返す."""

    return _clamp_unit((_clamp_unit(leisure_proximity) + _clamp_unit(water_proximity)) / 2.0)


def topophilia(greenery: float, water_proximity: float) -> float:
    """場所への愛着代理指標として、緑と水辺への近接・眺望の平均を返す."""

    return _clamp_unit((_clamp_unit(greenery) + _clamp_unit(water_proximity)) / 2.0)


def category_mix(reach: Mapping[str, bool]) -> float:
    """到達カテゴリの多様性を 0..1 で返す."""

    if not CATEGORY_WEIGHTS:
        return 0.0
    reached = sum(1 for category in CATEGORY_WEIGHTS if bool(reach.get(category, False)))
    return _clamp_unit(reached / len(CATEGORY_WEIGHTS))


def experiential_indicators(
    *,
    active_frontage: float,
    leisure_proximity: float,
    water_proximity: float,
    greenery: float,
    reach: Mapping[str, bool],
    time_var: float,
) -> dict[str, float]:
    """要素Cの4指標を 0..1 dict として返す."""

    mix = category_mix(reach)
    return {
        "liveliness": liveliness(active_frontage, mix),
        "lingering": lingering(leisure_proximity, water_proximity),
        "topophilia": topophilia(greenery, water_proximity),
        "time_variation": _clamp_unit(time_var),
    }


def _clamp_unit(value: float) -> float:
    return max(0.0, min(1.0, float(value)))
