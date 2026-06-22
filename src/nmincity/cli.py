"""n分都市化支援ツールの CLI."""

from __future__ import annotations

import argparse
import re
from collections import Counter

from nmincity.config import DEFAULT_PLACE, MODES


def build_parser() -> argparse.ArgumentParser:
    """CLI パーサを構築する."""

    parser = argparse.ArgumentParser(prog="nmincity")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="指定地区の n分都市度を計算する")
    run_parser.add_argument("--place", default=DEFAULT_PLACE, help="対象地区名")
    run_parser.add_argument("--minutes", type=float, default=15, help="到達圏の分数")
    run_parser.add_argument("--mode", choices=MODES, default="walk", help="移動手段")
    run_parser.add_argument("--sample", type=int, default=None, help="評価起点のサンプル数")
    run_parser.add_argument("--quality", action="store_true", help="歩行環境の質レイヤも計算する")
    run_parser.set_defaults(func=run)

    propose_parser = subparsers.add_parser("propose", help="不足エリアへの改善提案を生成する")
    propose_parser.add_argument("--place", default=DEFAULT_PLACE, help="対象地区名")
    propose_parser.add_argument("--minutes", type=float, default=15, help="到達圏の分数")
    propose_parser.add_argument("--mode", choices=MODES, default="walk", help="移動手段")
    propose_parser.add_argument("--sample", type=int, default=None, help="評価起点のサンプル数")
    propose_parser.add_argument("--top", type=int, default=10, help="表示する上位提案件数")
    propose_parser.set_defaults(func=propose)

    return parser


def run(args: argparse.Namespace) -> int:
    """OSM 実データから機能A(MVP)の近接性スコア地図を生成する."""

    from nmincity.backend.osmnx_backend import OsmnxBackend
    from nmincity.config import TIME_OF_DAY, score_label
    from nmincity.core import chronotopia, experiential, walkability
    from nmincity.core.score import environment_quality, proximity_score
    from nmincity.data import loader
    from nmincity.viz.maps import save_map, score_map, sq_scatter, time_of_day_map, walkability_map

    graph = loader.load_graph(args.place, args.mode)
    category_nodes = loader.load_category_nodes(graph, args.place)
    if args.quality:
        loader.annotate_walkability(graph, category_nodes)
    backend = OsmnxBackend(graph, category_nodes, args.mode)

    points: list[tuple[float, float, float]] = []
    scatter_points: list[tuple[float, float, str]] = []
    scores: list[float] = []
    qualities: list[float] = []
    scores_by_bucket: dict[str, list[float]] = {bucket: [] for bucket in TIME_OF_DAY}
    points_by_bucket: dict[str, list[tuple[float, float, float]]] = {bucket: [] for bucket in TIME_OF_DAY}
    labels: Counter[str] = Counter()
    origins = loader.make_origins(graph, args.sample)

    for origin in origins:
        weight = "eff_travel_time" if args.quality else "travel_time"
        reach = backend.reachable_categories(origin, args.minutes, args.mode, weight=weight)
        score = proximity_score(reach)
        lon, lat = loader.node_lonlat(graph, origin)
        if args.quality:
            reachable = backend.service_area(origin, args.minutes, args.mode, weight=weight)
            timed_scores = {
                bucket: chronotopia.proximity_score_at(reach, bucket)
                for bucket in TIME_OF_DAY
            }
            time_var = chronotopia.time_variation(timed_scores)
            ctx = loader.origin_context(graph, origin, reachable, category_nodes)
            exp_indicators = experiential.experiential_indicators(
                active_frontage=ctx["active_frontage"],
                leisure_proximity=ctx["leisure_proximity"],
                water_proximity=ctx["water_proximity"],
                greenery=ctx["greenery"],
                reach=reach,
                time_var=time_var,
            )
            q_value = environment_quality(
                walkability.origin_quality(graph, reachable),
                exp_indicators,
            )
            qualities.append(q_value)
            scatter_points.append((score, q_value, score_label(score)))
            for bucket, bucket_score in timed_scores.items():
                scores_by_bucket[bucket].append(bucket_score)
                points_by_bucket[bucket].append((lat, lon, bucket_score))
        points.append((lat, lon, score))
        scores.append(score)
        labels[score_label(score)] += 1

    m = score_map(points, f"{args.place} ({args.minutes:g}min, {args.mode})")
    output_path = f"outputs/{_safe_filename(args.place)}_S_{args.minutes:g}min_{args.mode}.html"
    save_map(m, output_path)

    if scores:
        average = sum(scores) / len(scores)
        minimum = min(scores)
        maximum = max(scores)
    else:
        average = minimum = maximum = 0.0

    print(f"origins: {len(origins)}")
    if args.quality:
        q_average, q_minimum, q_maximum = _summary(qualities)
        print(f"S: avg={average:.3f}, min={minimum:.3f}, max={maximum:.3f}")
        print(f"Q: avg={q_average:.3f}, min={q_minimum:.3f}, max={q_maximum:.3f}")
        for bucket in TIME_OF_DAY:
            bucket_avg, _bucket_min, _bucket_max = _summary(scores_by_bucket[bucket])
            print(f"S({bucket}): avg={bucket_avg:.3f}")
    else:
        print(f"score: avg={average:.3f}, min={minimum:.3f}, max={maximum:.3f}")
    print(
        "labels: "
        f"良好={labels['良好']}, 要改善={labels['要改善']}, 不足={labels['不足']}"
    )
    print(f"map: {output_path}")
    if args.quality:
        walk_path = f"outputs/{_safe_filename(args.place)}_walk_{args.minutes:g}min_{args.mode}.html"
        scatter_path = f"outputs/{_safe_filename(args.place)}_SxQ_{args.minutes:g}min_{args.mode}.png"
        time_path = f"outputs/{_safe_filename(args.place)}_time_{args.minutes:g}min_{args.mode}.html"
        save_map(
            walkability_map(
                loader.edge_quality_lines(graph),
                f"{args.place} ({args.minutes:g}min, {args.mode})",
            ),
            walk_path,
        )
        sq_scatter(
            scatter_points,
            f"{args.place} ({args.minutes:g}min, {args.mode})",
            scatter_path,
        )
        save_map(
            time_of_day_map(
                points_by_bucket,
                f"{args.place} ({args.minutes:g}min, {args.mode})",
            ),
            time_path,
        )
        print(f"walkability_map: {walk_path}")
        print(f"SxQ_scatter: {scatter_path}")
        print(f"time_of_day_map: {time_path}")
    return 0


def propose(args: argparse.Namespace) -> int:
    """機能B: ルールベースの改善提案を生成する."""

    from nmincity.backend.osmnx_backend import OsmnxBackend
    from nmincity.core import proposals
    from nmincity.core.score import proximity_score
    from nmincity.data import loader
    from nmincity.viz.maps import proposal_map, save_map

    graph = loader.load_graph(args.place, args.mode)
    category_nodes = loader.load_category_nodes(graph, args.place)
    backend = OsmnxBackend(graph, category_nodes, args.mode)
    origins = loader.make_origins(graph, args.sample)

    reach_by_origin: dict[object, dict[str, bool]] = {}
    service_areas: dict[object, set] = {}
    scores: dict[object, float] = {}
    deficient_points: list[tuple[float, float, float]] = []

    for origin in origins:
        reach = backend.reachable_categories(origin, args.minutes, args.mode)
        score = proximity_score(reach)
        reachable = backend.service_area(origin, args.minutes, args.mode)
        reach_by_origin[origin] = reach
        service_areas[origin] = reachable
        scores[origin] = score
        if score < 0.5:
            lon, lat = loader.node_lonlat(graph, origin)
            deficient_points.append((lat, lon, score))

    deficiencies = proposals.find_deficiencies(reach_by_origin)
    time_based = proposals.time_conversion_proposals(deficiencies, reach_by_origin)
    nearby_convertible = _nearby_convertible(deficiencies, service_areas, category_nodes)
    multifunction = proposals.multifunction_proposals(deficiencies, nearby_convertible)
    ranked = proposals.rank_proposals(time_based + multifunction, top_n=args.top)

    proposal_points: list[tuple[float, float, str, float]] = []
    for proposal in ranked:
        if proposal.facility is None or proposal.facility not in graph.nodes:
            continue
        lon, lat = loader.node_lonlat(graph, proposal.facility)
        proposal_points.append((lat, lon, proposal.rationale, proposal.priority))

    output_path = f"outputs/{_safe_filename(args.place)}_proposals_{args.minutes:g}min_{args.mode}.html"
    save_map(
        proposal_map(
            deficient_points,
            proposal_points,
            f"{args.place} ({args.minutes:g}min, {args.mode})",
        ),
        output_path,
    )

    deficient_count = sum(1 for score in scores.values() if score < 0.5)
    print(f"place: {args.place}")
    print(f"origins: {len(origins)}")
    print(f"deficient_origins(S<0.5): {deficient_count}")
    print("影響人口は人口メッシュ未接続のため、起点数ベースの近似です。")
    print(proposals.summarize(ranked))
    print(f"proposal_map: {output_path}")
    return 0


def _nearby_convertible(
    deficiencies: dict[object, list[str]],
    service_areas: dict[object, set],
    category_nodes: dict[str, set],
) -> dict[object, dict[str, set[tuple[object, str]]]]:
    """到達圏内の既存施設を多機能転換候補として簡易抽出する."""

    convertible_sources = ("education", "leisure", "work")
    result: dict[object, dict[str, set[tuple[object, str]]]] = {}
    for origin, missing_categories in deficiencies.items():
        reachable = service_areas.get(origin, set())
        by_target: dict[str, set[tuple[object, str]]] = {}
        for target in missing_categories:
            candidates: set[tuple[object, str]] = set()
            for source in convertible_sources:
                if source == target:
                    continue
                source_nodes = set(category_nodes.get(source, set()))
                # TODO: 本格版では 2x 到達圏や直線距離バッファで、到達圏外だが
                # 近傍にある学校・公共施設も候補化する。
                for facility in sorted(reachable & source_nodes, key=str)[:3]:
                    candidates.add((facility, source))
            if candidates:
                by_target[target] = candidates
        if by_target:
            result[origin] = by_target
    return result


def _summary(values: list[float]) -> tuple[float, float, float]:
    if not values:
        return 0.0, 0.0, 0.0
    return sum(values) / len(values), min(values), max(values)


def _safe_filename(value: str) -> str:
    safe = re.sub(r"[^\w.-]+", "_", value, flags=re.UNICODE).strip("_.")
    return safe or "nmincity"


def main(argv: list[str] | None = None) -> int:
    """CLI エントリポイント."""

    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
