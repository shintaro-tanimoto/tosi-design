"""機能C: Location-Allocation 最適配置の純粋ロジック."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AllocationResult:
    """MCLP による施設配置結果.

    ``selected`` は選ばれた候補地ノードID、``covered_origins`` は新たに
    被覆される起点IDの和集合である。``total_gain`` は被覆起点の利得
    ``w_c * population[i]`` の合計で、人口未接続時は一様人口の近似値になる。
    """

    selected: tuple
    covered_origins: tuple
    total_gain: float
    method: str
    target_category: str | None = None


def maximize_coverage(
    candidate_cover: Mapping[Any, Iterable[Any]],
    origin_gain: Mapping[Any, float],
    k: int,
    *,
    solver: str = "auto",
    target_category: str | None = None,
) -> AllocationResult:
    """重みづけ人口カバー最大化で最大 ``k`` 箇所の候補地を選ぶ.

    ``candidate_cover`` は候補地ごとに被覆できる未充足起点集合を渡す。
    目的関数は ``sum_i origin_gain[i] * y_i`` で、各起点は1回だけ計上する。
    ``solver="auto"`` では PuLP が使える場合に厳密解、使えない場合は
    限界利得最大の greedy 近似にフォールバックする。
    """

    if solver not in {"auto", "pulp", "greedy"}:
        raise ValueError("solver must be one of: auto, pulp, greedy")

    normalized_cover = _normalize_cover(candidate_cover)
    if k <= 0 or not normalized_cover:
        return _result((), (), origin_gain, "greedy" if solver == "greedy" else "pulp" if solver == "pulp" else "greedy", target_category)

    if solver == "greedy":
        return _greedy(normalized_cover, origin_gain, k, target_category)

    try:
        return _pulp(normalized_cover, origin_gain, k, target_category)
    except Exception:
        return _greedy(normalized_cover, origin_gain, k, target_category)


def coverage_rate(
    reach_by_origin: Mapping[Any, Mapping[str, bool]],
    category: str,
    *,
    covered_origins: Iterable[Any] = (),
) -> float:
    """配置前後の当該カテゴリ被覆率を返す.

    分子は現状 ``category`` に到達済みの起点と、今回配置で新たに被覆された
    起点の和集合である。起点がない場合は ``0.0`` を返す。
    """

    if not reach_by_origin:
        return 0.0
    covered = set(covered_origins)
    reached = sum(
        1
        for origin, reach in reach_by_origin.items()
        if bool(reach.get(category, False)) or origin in covered
    )
    return reached / len(reach_by_origin)


def _pulp(
    candidate_cover: Mapping[Any, frozenset[Any]],
    origin_gain: Mapping[Any, float],
    k: int,
    target_category: str | None,
) -> AllocationResult:
    import pulp

    candidates = tuple(sorted(candidate_cover, key=str))
    origins = tuple(
        sorted(
            set(origin_gain) | {origin for origins in candidate_cover.values() for origin in origins},
            key=str,
        )
    )

    problem = pulp.LpProblem("nmincity_mclp", pulp.LpMaximize)
    x = {candidate: pulp.LpVariable(f"x_{index}", cat="Binary") for index, candidate in enumerate(candidates)}
    y = {origin: pulp.LpVariable(f"y_{index}", cat="Binary") for index, origin in enumerate(origins)}

    problem += pulp.lpSum(float(origin_gain.get(origin, 0.0)) * y[origin] for origin in origins)
    problem += pulp.lpSum(x[candidate] for candidate in candidates) <= int(k)

    coverers_by_origin = {origin: [] for origin in origins}
    for candidate, covered in candidate_cover.items():
        for origin in covered:
            if origin in coverers_by_origin:
                coverers_by_origin[origin].append(candidate)

    for origin, coverers in coverers_by_origin.items():
        if coverers:
            problem += y[origin] <= pulp.lpSum(x[candidate] for candidate in coverers)
        else:
            problem += y[origin] <= 0

    status = problem.solve(pulp.PULP_CBC_CMD(msg=False))
    if pulp.LpStatus[status] not in {"Optimal", "Integer Feasible"}:
        raise RuntimeError(f"pulp failed to solve MCLP: {pulp.LpStatus[status]}")

    selected = tuple(candidate for candidate in candidates if (pulp.value(x[candidate]) or 0.0) > 0.5)
    covered = _covered_union(candidate_cover, selected)
    return _result(selected, covered, origin_gain, "pulp", target_category)


def _greedy(
    candidate_cover: Mapping[Any, frozenset[Any]],
    origin_gain: Mapping[Any, float],
    k: int,
    target_category: str | None,
) -> AllocationResult:
    remaining = list(sorted(candidate_cover, key=str))
    selected: list[Any] = []
    covered: set[Any] = set()

    for _ in range(max(0, int(k))):
        best_candidate = None
        best_gain = 0.0
        for candidate in remaining:
            marginal = candidate_cover[candidate] - covered
            gain = sum(float(origin_gain.get(origin, 0.0)) for origin in marginal)
            if gain > best_gain:
                best_candidate = candidate
                best_gain = gain
        if best_candidate is None or best_gain <= 0.0:
            break
        selected.append(best_candidate)
        covered.update(candidate_cover[best_candidate])
        remaining.remove(best_candidate)

    return _result(selected, covered, origin_gain, "greedy", target_category)


def _normalize_cover(candidate_cover: Mapping[Any, Iterable[Any]]) -> dict[Any, frozenset[Any]]:
    return {
        candidate: frozenset(origins)
        for candidate, origins in candidate_cover.items()
    }


def _covered_union(candidate_cover: Mapping[Any, frozenset[Any]], selected: Iterable[Any]) -> set[Any]:
    covered: set[Any] = set()
    for candidate in selected:
        covered.update(candidate_cover.get(candidate, frozenset()))
    return covered


def _result(
    selected: Iterable[Any],
    covered: Iterable[Any],
    origin_gain: Mapping[Any, float],
    method: str,
    target_category: str | None,
) -> AllocationResult:
    selected_tuple = tuple(sorted(selected, key=str))
    covered_tuple = tuple(sorted(covered, key=str))
    total_gain = sum(float(origin_gain.get(origin, 0.0)) for origin in covered_tuple)
    return AllocationResult(
        selected=selected_tuple,
        covered_origins=covered_tuple,
        total_gain=total_gain,
        method=method,
        target_category=target_category,
    )
