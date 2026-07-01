"""機能B: ルールベース改善提案の純粋ロジック."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from nmincity.config import CATEGORY_NAMES, CATEGORY_WEIGHTS, TIME_CONVERSIONS
from nmincity.core.score import normalize, proximity_score


@dataclass(frozen=True)
class Proposal:
    """不足カテゴリを解消する改善提案.

    ``affected_population`` は、人口メッシュが未接続の場合に起点数ベースの
    一様重みを使う近似値である。将来は ``population`` 引数に国勢調査
    メッシュ等の人口重みを渡すことで差し替える。
    """

    kind: str
    target_category: str
    source_category: str | None
    time_bucket: str | None
    facility: object | None
    affected_population: float
    priority: float
    rationale: str
    affected_origins: tuple[Any, ...] = ()


def find_deficiencies(
    reach_by_origin: Mapping[Any, Mapping[str, bool]],
    weights: Mapping[str, float] | None = None,
    *,
    label_threshold: float = 0.5,
    high_weight_threshold: float = 0.14,
) -> dict[Any, list[str]]:
    """起点ごとの不足カテゴリを重みの降順で返す.

    要件定義書 §6.6-1「S(i) が低い、または高重みカテゴリで a(i,c)=0 の
    メッシュを抽出する」に対応する。不足エリア
    （``proximity_score(reach) < label_threshold``）の起点は全欠落カテゴリを、
    それ以外の起点は高重みカテゴリ（正規化重み >= ``high_weight_threshold``、
    初期重みでは教育・自然・物資調達・医療）の欠落だけを返す。全カテゴリに
    到達する起点や、非不足エリアで高重み欠落が無い起点は空リストになる。
    """

    selected_weights = CATEGORY_WEIGHTS if weights is None else weights
    normalized = normalize(selected_weights)
    categories = sorted(normalized, key=lambda category: (-normalized[category], category))
    result: dict[Any, list[str]] = {}
    for origin, reach in reach_by_origin.items():
        is_deficient_area = proximity_score(reach, selected_weights) < label_threshold
        missing = [category for category in categories if not bool(reach.get(category, False))]
        if not is_deficient_area:
            missing = [category for category in missing if normalized[category] >= high_weight_threshold]
        result[origin] = missing
    return result


def time_conversion_proposals(
    deficiencies: Mapping[Any, list[str]],
    source_reach_by_origin: Mapping[Any, Mapping[str, bool]],
    population: Mapping[Any, float] | None = None,
    *,
    weights: Mapping[str, float] | None = None,
    conversions: Mapping[str, list[Mapping[str, float | str]]] | None = None,
) -> list[Proposal]:
    """新設なしの時間帯転換で解消できる不足への提案を返す.

    影響人口は ``population`` が未指定なら起点ごとの一様重み 1.0 を合計する
    近似であり、現段階では「起点数ベース」の代理指標である。
    """

    selected_weights = CATEGORY_WEIGHTS if weights is None else weights
    selected_conversions = TIME_CONVERSIONS if conversions is None else conversions
    proposals: list[Proposal] = []

    for time_bucket, rules in selected_conversions.items():
        for rule in rules:
            source = str(rule["source"])
            target = str(rule["target"])
            affected = [
                origin
                for origin, missing in deficiencies.items()
                if target in missing and bool(source_reach_by_origin.get(origin, {}).get(source, False))
            ]
            affected_population = _population_sum(affected, population)
            if affected_population <= 0:
                continue
            priority = float(selected_weights.get(target, 0.0)) * affected_population
            proposals.append(
                Proposal(
                    kind="time_conversion",
                    target_category=target,
                    source_category=source,
                    time_bucket=time_bucket,
                    facility=None,
                    affected_population=affected_population,
                    priority=priority,
                    rationale=(
                        f"{_time_name(time_bucket)}に近隣の『{_category_name(source)}』施設を"
                        f"『{_category_name(target)}』として開放すれば、"
                        f"{affected_population:g}起点で当該機能の不足を新設なしで解消"
                        "（クロノトピー、影響人口は起点数ベースの近似）。"
                    ),
                    affected_origins=tuple(sorted(affected, key=str)),
                )
            )

    return proposals


def multifunction_proposals(
    deficiencies: Mapping[Any, list[str]],
    nearby_convertible: Mapping[Any, Mapping[str, set[Any]]],
    population: Mapping[Any, float] | None = None,
    *,
    weights: Mapping[str, float] | None = None,
) -> list[Proposal]:
    """近傍既存施設の多機能転換で解消できる不足への提案を返す.

    ``nearby_convertible`` は CLI/loader 側の空間近傍解析結果を受け取る。
    値の施設はノードIDそのもの、または ``(node_id, source_category)`` の
    タプルを許容する。影響人口は未指定時に起点数ベースの近似とする。
    """

    selected_weights = CATEGORY_WEIGHTS if weights is None else weights
    affected_by_facility: dict[tuple[str, Any, str | None], list[Any]] = defaultdict(list)

    for origin, missing in deficiencies.items():
        missing_set = set(missing)
        for target, facilities in nearby_convertible.get(origin, {}).items():
            if target not in missing_set:
                continue
            for raw_facility in facilities:
                facility, source_category = _facility_and_source(raw_facility)
                affected_by_facility[(target, facility, source_category)].append(origin)

    proposals: list[Proposal] = []
    for (target, facility, source_category), origins in affected_by_facility.items():
        affected_population = _population_sum(origins, population)
        if affected_population <= 0:
            continue
        priority = float(selected_weights.get(target, 0.0)) * affected_population
        source_text = (
            f"（元カテゴリ: 『{_category_name(source_category)}』）"
            if source_category is not None
            else ""
        )
        proposals.append(
            Proposal(
                kind="multifunction",
                target_category=target,
                source_category=source_category,
                time_bucket=None,
                facility=facility,
                affected_population=affected_population,
                priority=priority,
                rationale=(
                    f"近隣の既存施設（ノードID={facility}）{source_text}を"
                    f"『{_category_name(target)}』機能に多機能転換すれば、"
                    f"{affected_population:g}起点の不足を解消"
                    "（影響人口は起点数ベースの近似）。"
                ),
                affected_origins=tuple(sorted(origins, key=str)),
            )
        )

    return proposals


def apply_proposals(
    reach_by_origin: Mapping[Any, Mapping[str, bool]],
    proposals: list[Proposal],
) -> dict[Any, dict[str, bool]]:
    """提案実施後の到達可否を返す.

    入力を変更せず、各提案の ``affected_origins`` について
    ``target_category`` を到達済みにする単純な効果モデルである。
    """

    updated = {origin: dict(reach) for origin, reach in reach_by_origin.items()}
    for proposal in proposals:
        for origin in proposal.affected_origins:
            if origin not in updated:
                continue
            updated[origin][proposal.target_category] = True
    return updated


def rank_proposals(proposals: list[Proposal], top_n: int | None = None) -> list[Proposal]:
    """提案を優先度順に並べ、必要なら上位件数だけ返す."""

    ranked = sorted(
        proposals,
        key=lambda proposal: (
            -proposal.priority,
            -proposal.affected_population,
            proposal.target_category,
            proposal.kind,
        ),
    )
    if top_n is None:
        return ranked
    return ranked[: max(0, int(top_n))]


def summarize(proposals: list[Proposal]) -> str:
    """提案一覧を CLI 向けの日本語テキストで返す."""

    if not proposals:
        return "提案はありません。"

    lines: list[str] = []
    for index, proposal in enumerate(proposals, start=1):
        kind_name = "時間帯転換" if proposal.kind == "time_conversion" else "多機能転換"
        lines.append(
            f"{index}. [{kind_name}] {_category_name(proposal.target_category)} "
            f"影響人口={proposal.affected_population:g} "
            f"優先度={proposal.priority:.3f} - {proposal.rationale}"
        )
    return "\n".join(lines)


def _population_sum(origins: list[Any], population: Mapping[Any, float] | None) -> float:
    if population is None:
        return float(len(origins))
    return sum(float(population.get(origin, 1.0)) for origin in origins)


def _facility_and_source(raw_facility: Any) -> tuple[Any, str | None]:
    if isinstance(raw_facility, tuple) and len(raw_facility) == 2:
        facility, source_category = raw_facility
        return facility, str(source_category) if source_category is not None else None
    return raw_facility, None


def _category_name(category: str | None) -> str:
    if category is None:
        return "不明"
    return CATEGORY_NAMES.get(category, category)


def _time_name(time_bucket: str) -> str:
    return {
        "morning": "朝",
        "daytime": "昼間",
        "evening": "夜間",
    }.get(time_bucket, time_bucket)
