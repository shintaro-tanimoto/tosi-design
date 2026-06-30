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

    compare_parser = subparsers.add_parser("compare", help="重み感度分析とシナリオ比較を生成する")
    compare_parser.add_argument("--place", default=DEFAULT_PLACE, help="対象地区名")
    compare_parser.add_argument("--minutes", type=float, default=15, help="到達圏の分数")
    compare_parser.add_argument("--mode", choices=MODES, default="walk", help="移動手段")
    compare_parser.add_argument("--sample", type=int, default=None, help="評価起点のサンプル数")
    compare_parser.add_argument("--top", type=int, default=10, help="提案実施後シナリオに使う上位提案件数")
    compare_parser.set_defaults(func=compare)

    allocate_parser = subparsers.add_parser("allocate", help="不足カテゴリの最適配置を計算する")
    allocate_parser.add_argument("--place", default=DEFAULT_PLACE, help="対象地区名")
    allocate_parser.add_argument("--minutes", type=float, default=15, help="到達圏の分数")
    allocate_parser.add_argument("--mode", choices=MODES, default="walk", help="移動手段")
    allocate_parser.add_argument("--sample", type=int, default=None, help="評価起点のサンプル数")
    allocate_parser.add_argument("--k", type=int, default=3, help="選択する新規/転換施設数")
    allocate_parser.add_argument("--category", default=None, help="対象カテゴリID（未指定時は透明な既定で選択）")
    allocate_parser.add_argument("--candidates", type=int, default=60, help="候補地サンプル数")
    allocate_parser.add_argument("--solver", choices=("auto", "pulp", "greedy"), default="auto", help="最適化ソルバ")
    allocate_parser.set_defaults(func=allocate)

    dashboard_parser = subparsers.add_parser("dashboard", help="単一地区の統合ダッシュボードを生成する")
    dashboard_parser.add_argument("--place", default=DEFAULT_PLACE, help="対象地区名")
    dashboard_parser.add_argument("--minutes", type=float, default=15, help="到達圏の分数")
    dashboard_parser.add_argument("--mode", choices=MODES, default="walk", help="移動手段")
    dashboard_parser.add_argument("--sample", type=int, default=None, help="評価起点のサンプル数")
    dashboard_parser.set_defaults(func=dashboard)

    compare_places_parser = subparsers.add_parser(
        "compare-places", help="複数地区の7要素プロファイルを比較する"
    )
    compare_places_parser.add_argument(
        "--places", nargs="+", default=None, help="比較地区名（未指定時は COMPARISON_PLACES）"
    )
    compare_places_parser.add_argument("--minutes", type=float, default=15, help="到達圏の分数")
    compare_places_parser.add_argument("--mode", choices=MODES, default="walk", help="移動手段")
    compare_places_parser.add_argument("--sample", type=int, default=None, help="評価起点のサンプル数")
    compare_places_parser.set_defaults(func=compare_places)

    viz_gdb_parser = subparsers.add_parser(
        "viz-gdb", help="ArcGIS .gdb の計算済み結果を folium で可視化する（arcpy 不要）"
    )
    viz_gdb_parser.add_argument("--gdb", required=True, help="入力ファイルジオデータベース(.gdb)")
    viz_gdb_parser.add_argument("--place", default=DEFAULT_PLACE, help="対象地区名（見出し用）")
    viz_gdb_parser.add_argument(
        "--score-layer", default=None, help="スコアレイヤー名（既定: S 列を持つ層を自動検出）"
    )
    viz_gdb_parser.add_argument("--facility-prefix", default="osm_", help="施設レイヤー名の接頭辞")
    viz_gdb_parser.set_defaults(func=viz_gdb)

    compare_gdb_parser = subparsers.add_parser(
        "compare-gdb", help="複数の ArcGIS .gdb を横断して7要素到達率を比較する（arcpy 不要）"
    )
    compare_gdb_parser.add_argument(
        "--gdbs", nargs="+", required=True, help="比較する .gdb のパス（2つ以上）"
    )
    compare_gdb_parser.add_argument(
        "--labels", nargs="+", default=None, help="各 .gdb の表示ラベル（既定: ファイル名）"
    )
    compare_gdb_parser.add_argument(
        "--score-layer", default=None, help="スコアレイヤー名（既定: 各 .gdb で自動検出）"
    )
    compare_gdb_parser.set_defaults(func=compare_gdb)

    return parser


def run(args: argparse.Namespace) -> int:
    """OSM 実データから機能A(MVP)の近接性スコア地図を生成する."""

    from nmincity.backend.osmnx_backend import OsmnxBackend
    from nmincity.config import TIME_OF_DAY, score_label
    from nmincity.core import chronotopia, experiential, walkability
    from nmincity.core.score import environment_quality, proximity_score
    from nmincity.data import loader
    from nmincity.viz.maps import (
        category_layer_points,
        category_layers_map,
        save_map,
        score_heatmap,
        score_map,
        sq_scatter,
        time_of_day_map,
        walkability_map,
    )

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
    reach_by_origin: dict[object, dict[str, bool]] = {}
    latlon_by_origin: dict[object, tuple[float, float]] = {}
    labels: Counter[str] = Counter()
    origins = loader.make_origins(graph, args.sample)

    for origin in origins:
        weight = "eff_travel_time" if args.quality else "travel_time"
        reach = backend.reachable_categories(origin, args.minutes, args.mode, weight=weight)
        score = proximity_score(reach)
        lon, lat = loader.node_lonlat(graph, origin)
        reach_by_origin[origin] = reach
        latlon_by_origin[origin] = (lat, lon)
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

    title = f"{args.place} ({args.minutes:g}min, {args.mode})"
    m = score_map(points, title)
    output_path = f"outputs/{_safe_filename(args.place)}_S_{args.minutes:g}min_{args.mode}.html"
    save_map(m, output_path)

    category_points = category_layer_points(reach_by_origin, latlon_by_origin)
    layers_path = f"outputs/{_safe_filename(args.place)}_layers_{args.minutes:g}min_{args.mode}.html"
    heatmap_path = f"outputs/{_safe_filename(args.place)}_heatmap_{args.minutes:g}min_{args.mode}.html"
    save_map(category_layers_map(category_points, title), layers_path)
    save_map(score_heatmap(points, category_points, title), heatmap_path)

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
    print(f"category_layers_map: {layers_path}")
    print(f"score_heatmap: {heatmap_path}")
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


def compare(args: argparse.Namespace) -> int:
    """M3b: 感度分析とシナリオ比較を生成する."""

    from nmincity.backend.osmnx_backend import OsmnxBackend
    from nmincity.config import CATEGORY_NAMES, CATEGORY_WEIGHTS
    from nmincity.core import proposals, sensitivity
    from nmincity.data import loader
    from nmincity.viz.charts import reach_rate_chart, scenario_chart, sensitivity_chart

    graph = loader.load_graph(args.place, args.mode)
    category_nodes = loader.load_category_nodes(graph, args.place)
    backend = OsmnxBackend(graph, category_nodes, args.mode)
    origins = loader.make_origins(graph, args.sample)

    reach_by_origin: dict[object, dict[str, bool]] = {}
    service_areas: dict[object, set] = {}
    for origin in origins:
        reach_by_origin[origin] = backend.reachable_categories(origin, args.minutes, args.mode)
        service_areas[origin] = backend.service_area(origin, args.minutes, args.mode)

    deficiencies = proposals.find_deficiencies(reach_by_origin)
    time_based = proposals.time_conversion_proposals(deficiencies, reach_by_origin)
    nearby_convertible = _nearby_convertible(deficiencies, service_areas, category_nodes)
    multifunction = proposals.multifunction_proposals(deficiencies, nearby_convertible)
    ranked = proposals.rank_proposals(time_based + multifunction, top_n=args.top)

    rates = sensitivity.reach_rate(reach_by_origin)
    sens = sensitivity.category_sensitivity(reach_by_origin)
    comparison = sensitivity.compare_scenarios(reach_by_origin, ranked)
    linear_mean = sum(CATEGORY_WEIGHTS[category] * rates[category] for category in CATEGORY_WEIGHTS)

    base = f"outputs/{_safe_filename(args.place)}_compare_{args.minutes:g}min_{args.mode}"
    scenario_path = f"{base}_scenarios.html"
    sensitivity_path = f"{base}_sensitivity.html"
    rates_path = f"{base}_reach_rates.html"
    scenario_chart(comparison, f"{args.place} ({args.minutes:g}min, {args.mode})", scenario_path)
    sensitivity_chart(sens, f"{args.place} ({args.minutes:g}min, {args.mode})", sensitivity_path)
    reach_rate_chart(rates, f"{args.place} ({args.minutes:g}min, {args.mode})", rates_path)

    print(f"place: {args.place}")
    print(f"origins: {len(origins)}")
    print(f"proposals_used: {len(ranked)}")
    print("mean_S は Σ normalized(w_c) * reach_rate[c] として説明できます。")
    print(f"baseline_linear_mean_S: {linear_mean:.3f}")
    print("")
    print("scenario\tmean_S\tmin_S\tmax_S\t良好\t要改善\t不足")
    for name, values in comparison.items():
        print(
            f"{name}\t"
            f"{values['mean']:.3f}\t{values['min']:.3f}\t{values['max']:.3f}\t"
            f"{values['label_good']:.0f}\t"
            f"{values['label_needs_improvement']:.0f}\t"
            f"{values['label_deficient']:.0f}"
        )
    print("")
    print("category\tweight\treach_rate\tΔmean_S(+0.05)")
    for category in CATEGORY_WEIGHTS:
        print(
            f"{CATEGORY_NAMES.get(category, category)}\t"
            f"{CATEGORY_WEIGHTS[category]:.3f}\t"
            f"{rates[category]:.3f}\t"
            f"{sens[category]:+.4f}"
        )
    print(f"scenario_chart: {scenario_path}")
    print(f"sensitivity_chart: {sensitivity_path}")
    print(f"reach_rate_chart: {rates_path}")
    return 0


def allocate(args: argparse.Namespace) -> int:
    """機能C: 重みづけ人口カバー最大化による最適配置を生成する."""

    from nmincity.backend.osmnx_backend import OsmnxBackend
    from nmincity.config import CATEGORY_NAMES, CATEGORY_WEIGHTS
    from nmincity.core import allocation, proposals
    from nmincity.data import loader
    from nmincity.viz.maps import allocation_map, save_map

    graph = loader.load_graph(args.place, args.mode)
    category_nodes = loader.load_category_nodes(graph, args.place)
    backend = OsmnxBackend(graph, category_nodes, args.mode)
    origins = loader.make_origins(graph, args.sample)

    reach_by_origin: dict[object, dict[str, bool]] = {}
    for origin in origins:
        reach_by_origin[origin] = backend.reachable_categories(origin, args.minutes, args.mode)

    target_category = _target_category(args.category, reach_by_origin, proposals)
    target_weight = float(CATEGORY_WEIGHTS.get(target_category, 0.0))
    unmet = {
        origin
        for origin, reach in reach_by_origin.items()
        if not bool(reach.get(target_category, False))
    }
    origin_gain = {origin: target_weight * 1.0 for origin in unmet}

    candidate_count = args.candidates if args.candidates is not None else 60
    candidates = loader.make_origins(graph, candidate_count)
    candidate_cover: dict[object, set] = {}
    for candidate in candidates:
        # TODO: 候補数が大きい場合は到達圏計算が重くなるため、空間索引や
        # 事前計算済み距離行列で高速化する。
        reachable = backend.service_area(candidate, args.minutes, args.mode)
        candidate_cover[candidate] = set(unmet) & set(reachable)

    result = allocation.maximize_coverage(
        candidate_cover,
        origin_gain,
        args.k,
        solver=args.solver,
        target_category=target_category,
    )

    before_rate = allocation.coverage_rate(reach_by_origin, target_category)
    after_rate = allocation.coverage_rate(
        reach_by_origin,
        target_category,
        covered_origins=result.covered_origins,
    )

    unmet_points = [_node_latlon(graph, origin, loader) for origin in unmet if origin in graph.nodes]
    covered_set = set(result.covered_origins)
    covered_points = [_node_latlon(graph, origin, loader) for origin in covered_set if origin in graph.nodes]
    selected_points = [
        (*_node_latlon(graph, candidate, loader), f"node={candidate}")
        for candidate in result.selected
        if candidate in graph.nodes
    ]

    output_path = f"outputs/{_safe_filename(args.place)}_allocation_{args.minutes:g}min_{args.mode}.html"
    save_map(
        allocation_map(
            selected_points,
            covered_points,
            unmet_points,
            f"{args.place} ({args.minutes:g}min, {args.mode})",
        ),
        output_path,
    )

    category_name = CATEGORY_NAMES.get(target_category, target_category)
    print(f"target_category: {category_name} ({target_category})")
    print(f"weight_w_c: {target_weight:.3f}")
    print(f"unmet_origins: {len(unmet)}")
    print(f"k: {args.k}")
    print(f"solver: {args.solver} -> method={result.method}")
    print("population: 一様近似（起点数ベース）")
    print(f"selected_nodes: {', '.join(str(node) for node in result.selected) if result.selected else '(none)'}")
    print(f"coverage_rate: {before_rate:.3f} -> {after_rate:.3f}")
    print(f"total_gain: {result.total_gain:.3f}")
    print(f"allocation_map: {output_path}")
    return 0


def dashboard(args: argparse.Namespace) -> int:
    """単一地区の統合ダッシュボード（地図＋チャート＋重み根拠）を生成する."""

    import os

    from nmincity.backend.osmnx_backend import OsmnxBackend
    from nmincity.config import CATEGORY_NAMES, CATEGORY_WEIGHTS, WEIGHT_RATIONALE, score_label
    from nmincity.core import sensitivity
    from nmincity.core.score import proximity_score
    from nmincity.data import loader
    from nmincity.viz.charts import reach_rate_chart
    from nmincity.viz.dashboard import build_dashboard
    from nmincity.viz.maps import (
        category_layer_points,
        category_layers_map,
        save_map,
        score_map,
        walkability_map,
    )

    graph = loader.load_graph(args.place, args.mode)
    category_nodes = loader.load_category_nodes(graph, args.place)
    loader.annotate_walkability(graph, category_nodes)
    backend = OsmnxBackend(graph, category_nodes, args.mode)
    origins = loader.make_origins(graph, args.sample)

    title = f"{args.place} ({args.minutes:g}min, {args.mode})"
    points: list[tuple[float, float, float]] = []
    scores: list[float] = []
    reach_by_origin: dict[object, dict[str, bool]] = {}
    latlon_by_origin: dict[object, tuple[float, float]] = {}
    labels: Counter[str] = Counter()
    for origin in origins:
        reach = backend.reachable_categories(origin, args.minutes, args.mode, weight="eff_travel_time")
        score = proximity_score(reach)
        lon, lat = loader.node_lonlat(graph, origin)
        reach_by_origin[origin] = reach
        latlon_by_origin[origin] = (lat, lon)
        points.append((lat, lon, score))
        scores.append(score)
        labels[score_label(score)] += 1

    base = f"outputs/{_safe_filename(args.place)}_dash_{args.minutes:g}min_{args.mode}"
    s_path = f"{base}_S.html"
    q_path = f"{base}_Q.html"
    layers_path = f"{base}_layers.html"
    rates_path = f"{base}_reach_rates.html"
    save_map(score_map(points, title), s_path)
    save_map(walkability_map(loader.edge_quality_lines(graph), title), q_path)
    save_map(category_layers_map(category_layer_points(reach_by_origin, latlon_by_origin), title), layers_path)
    reach_rate_chart(sensitivity.reach_rate(reach_by_origin), title, rates_path)

    average, minimum, maximum = _summary(scores)
    summary = [
        ("起点数", str(len(origins))),
        ("S 平均", f"{average:.3f}"),
        ("S 最小/最大", f"{minimum:.3f} / {maximum:.3f}"),
        ("良好/要改善/不足", f"{labels['良好']}/{labels['要改善']}/{labels['不足']}"),
    ]
    weight_rows = [
        {
            "name": CATEGORY_NAMES.get(category, category),
            "weight": f"{CATEGORY_WEIGHTS[category]:.2f}",
            "rationale": WEIGHT_RATIONALE.get(category, {}).get("rationale", ""),
            "reference": WEIGHT_RATIONALE.get(category, {}).get("reference", ""),
        }
        for category in CATEGORY_WEIGHTS
    ]
    panels = [
        ("近接性 S（地図）", os.path.basename(s_path)),
        ("環境の質 Q（歩行環境）", os.path.basename(q_path)),
        ("7要素レイヤー", os.path.basename(layers_path)),
        ("カテゴリ別到達率", os.path.basename(rates_path)),
    ]

    output_path = f"{base}.html"
    build_dashboard(
        place=args.place,
        panels=panels,
        weight_rows=weight_rows,
        summary=summary,
        path=output_path,
        subtitle="S（近接性）と Q（環境の質）は合成せず並置して診断する（要件 §6.7.1）。",
    )

    print(f"place: {args.place}")
    print(f"origins: {len(origins)}")
    print(f"S: avg={average:.3f}, min={minimum:.3f}, max={maximum:.3f}")
    print(f"dashboard: {output_path}")
    return 0


def compare_places(args: argparse.Namespace) -> int:
    """複数地区の7要素到達率プロファイルを比較する."""

    import os

    from nmincity.backend.osmnx_backend import OsmnxBackend
    from nmincity.config import CATEGORY_WEIGHTS, COMPARISON_PLACES
    from nmincity.core import sensitivity
    from nmincity.core.score import proximity_score
    from nmincity.data import loader
    from nmincity.viz.charts import places_radar_chart, places_reach_bar_chart
    from nmincity.viz.dashboard import build_dashboard

    places = args.places if args.places else list(COMPARISON_PLACES)
    profiles: dict[str, dict[str, float]] = {}
    mean_s_by_place: dict[str, float] = {}
    origins_by_place: dict[str, int] = {}

    for place in places:
        graph = loader.load_graph(place, args.mode)
        category_nodes = loader.load_category_nodes(graph, place)
        backend = OsmnxBackend(graph, category_nodes, args.mode)
        origins = loader.make_origins(graph, args.sample)
        reach_by_origin = {
            origin: backend.reachable_categories(origin, args.minutes, args.mode)
            for origin in origins
        }
        rates = sensitivity.reach_rate(reach_by_origin)
        scores = [proximity_score(reach) for reach in reach_by_origin.values()]
        label = _place_label(place)
        profiles[label] = rates
        mean_s_by_place[label] = _summary(scores)[0]
        origins_by_place[label] = len(origins)

    title = f"{len(places)}地区比較 ({args.minutes:g}min, {args.mode})"
    base = f"outputs/compare_places_{args.minutes:g}min_{args.mode}"
    radar_path = f"{base}_radar.html"
    bar_path = f"{base}_bar.html"
    places_radar_chart(profiles, title, radar_path)
    places_reach_bar_chart(profiles, title, bar_path)

    summary = [(label, f"mean S={mean_s_by_place[label]:.3f}") for label in profiles]
    panels = [
        ("7要素プロファイル（レーダー）", os.path.basename(radar_path)),
        ("カテゴリ別到達率（グループ棒）", os.path.basename(bar_path)),
    ]
    weight_rows = _comparison_weight_rows(profiles, mean_s_by_place)

    output_path = f"{base}.html"
    build_dashboard(
        place=title,
        panels=panels,
        weight_rows=weight_rows,
        summary=summary,
        path=output_path,
        subtitle="同一指標を地区横断で比較。レーダーは7要素の到達率プロファイルの「形」を示す。",
    )

    print("places: " + ", ".join(profiles))
    for label in profiles:
        print(f"{label}\torigins={origins_by_place[label]}\tmean_S={mean_s_by_place[label]:.3f}")
    print(f"radar_chart: {radar_path}")
    print(f"bar_chart: {bar_path}")
    print(f"dashboard: {output_path}")
    _ = CATEGORY_WEIGHTS  # 重み参照（将来の重み別比較拡張用）
    return 0


def viz_gdb(args: argparse.Namespace) -> int:
    """ArcGIS .gdb の計算済み結果（S / 施設）を folium で可視化する（arcpy 非依存）."""

    import os

    from nmincity.config import CATEGORY_NAMES, CATEGORY_WEIGHTS, WEIGHT_RATIONALE
    from nmincity.data import gdb_loader
    from nmincity.viz.charts import reach_rate_chart
    from nmincity.viz.dashboard import build_dashboard
    from nmincity.viz.maps import (
        facility_layers_map,
        save_map,
        score_mesh_map,
        score_map,
        score_surface_map,
    )

    score_layers = (
        [args.score_layer] if args.score_layer else gdb_loader.list_score_layers(args.gdb)
    )
    if not score_layers:
        print(f"スコアレイヤー（S 列）が見つかりません: {args.gdb}")
        return 1

    safe_place = _safe_filename(args.place)
    facilities = gdb_loader.load_facility_points(args.gdb, prefix=args.facility_prefix)
    facilities_path = f"outputs/{safe_place}_gdb_facilities.html"
    save_map(facility_layers_map(facilities, args.place), facilities_path)

    primary_panels: list[tuple[str, str]] = []
    for index, layer in enumerate(score_layers):
        points = gdb_loader.load_score_points(args.gdb, layer)
        cells = gdb_loader.load_score_mesh(args.gdb, layer)
        title = f"{args.place} [{layer}]"
        slug = _safe_filename(layer)
        s_path = f"outputs/{safe_place}_gdb_{slug}_S.html"
        mesh_path = f"outputs/{safe_place}_gdb_{slug}_mesh.html"
        surface_path = f"outputs/{safe_place}_gdb_{slug}_surface.html"
        save_map(score_map(points, title), s_path)
        save_map(score_mesh_map(cells, title), mesh_path)
        save_map(score_surface_map(points, title), surface_path)
        average, minimum, maximum = _summary([score for _lat, _lon, score in points])
        print(f"layer={layer}\torigins={len(points)}\tS avg={average:.3f} min={minimum:.3f} max={maximum:.3f}")
        if index == 0:
            primary_panels = [
                ("近接性 S（メッシュ塗り）", os.path.basename(mesh_path)),
                ("近接性 S（滑らかな面）", os.path.basename(surface_path)),
                ("近接性 S（中心点）", os.path.basename(s_path)),
            ]

    primary_layer = score_layers[0]
    summary_stats = gdb_loader.load_score_summary(args.gdb, primary_layer)
    labels = summary_stats["labels"]
    summary = [
        ("起点数", str(summary_stats["origins"])),
        ("mean S" + ("（人口加重）" if summary_stats["pop_weighted"] else ""), f"{summary_stats['mean_s']:.3f}"),
        ("良好/要改善/不足", f"{labels['良好']}/{labels['要改善']}/{labels['不足']}"),
        ("施設総数", str(sum(len(points) for points in facilities.values()))),
    ]

    panels = list(primary_panels)
    profile = gdb_loader.load_reach_profile(args.gdb, primary_layer)
    if profile is not None:
        rates_path = f"outputs/{safe_place}_gdb_reach_rates.html"
        reach_rate_chart(profile, args.place, rates_path)
        panels.append(("カテゴリ別到達率", os.path.basename(rates_path)))
    else:
        print(f"注: {primary_layer} に reach_<category> 列が無いため到達率チャートは省略しました。")
    panels.append(("7要素 施設分布", os.path.basename(facilities_path)))

    weight_rows = [
        {
            "name": CATEGORY_NAMES.get(category, category),
            "weight": f"{CATEGORY_WEIGHTS[category]:.2f}",
            "rationale": WEIGHT_RATIONALE.get(category, {}).get("rationale", ""),
            "reference": WEIGHT_RATIONALE.get(category, {}).get("reference", ""),
        }
        for category in CATEGORY_WEIGHTS
    ]
    output_path = f"outputs/{safe_place}_gdb_dashboard.html"
    build_dashboard(
        place=args.place,
        panels=panels,
        weight_rows=weight_rows,
        summary=summary,
        path=output_path,
        subtitle="ArcGIS(.gdb) の計算済み結果を arcpy 不要で可視化（plan.md M5）。",
    )
    print(f"facilities: {facilities_path}")
    print(f"dashboard: {output_path}")
    return 0


def compare_gdb(args: argparse.Namespace) -> int:
    """複数の ArcGIS .gdb を横断して7要素到達率プロファイルを比較する（arcpy 非依存）."""

    import os
    from pathlib import Path

    from nmincity.data import gdb_loader
    from nmincity.viz.charts import places_radar_chart, places_reach_bar_chart
    from nmincity.viz.dashboard import build_dashboard

    labels = args.labels if args.labels else [Path(gdb).stem for gdb in args.gdbs]
    if len(labels) != len(args.gdbs):
        print("--labels の数は --gdbs の数と一致させてください。")
        return 1

    profiles: dict[str, dict[str, float]] = {}
    mean_s_by_label: dict[str, float] = {}
    for gdb, label in zip(args.gdbs, labels):
        score_layers = (
            [args.score_layer] if args.score_layer else gdb_loader.list_score_layers(gdb)
        )
        if not score_layers:
            print(f"スコアレイヤーが見つかりません（スキップ）: {gdb}")
            continue
        layer = score_layers[0]
        summary_stats = gdb_loader.load_score_summary(gdb, layer)
        mean_s_by_label[label] = float(summary_stats["mean_s"])
        profile = gdb_loader.load_reach_profile(gdb, layer)
        if profile is None:
            print(f"注: {label} ({layer}) に reach_<category> 列が無いためレーダーから除外しました。")
            continue
        profiles[label] = profile
        print(f"{label}\tlayer={layer}\torigins={summary_stats['origins']}\tmean_S={summary_stats['mean_s']:.3f}")

    if not mean_s_by_label:
        print("比較可能な .gdb がありませんでした。")
        return 1

    title = f"{len(mean_s_by_label)}地区比較 (.gdb)"
    panels: list[tuple[str, str]] = []
    if profiles:
        radar_path = "outputs/compare_gdb_radar.html"
        bar_path = "outputs/compare_gdb_bar.html"
        places_radar_chart(profiles, title, radar_path)
        places_reach_bar_chart(profiles, title, bar_path)
        panels = [
            ("7要素プロファイル（レーダー）", os.path.basename(radar_path)),
            ("カテゴリ別到達率（グループ棒）", os.path.basename(bar_path)),
        ]
        print(f"radar_chart: {radar_path}")
        print(f"bar_chart: {bar_path}")
    else:
        print("注: どの .gdb にも reach_<category> 列が無いため、mean S のみの比較になります。")

    summary = [(label, f"mean S={mean_s_by_label[label]:.3f}") for label in mean_s_by_label]
    weight_rows = _comparison_weight_rows(profiles, {label: mean_s_by_label[label] for label in profiles})

    output_path = "outputs/compare_gdb_dashboard.html"
    build_dashboard(
        place=title,
        panels=panels,
        weight_rows=weight_rows,
        summary=summary,
        path=output_path,
        subtitle="ArcGIS(.gdb) の計算済み結果を地区横断で比較。レーダーは7要素到達率の「形」を示す。",
    )
    print(f"dashboard: {output_path}")
    return 0


def _place_label(place: str) -> str:
    """地区名の先頭トークンを比較ラベルにする（例: '住吉区, 大阪市, ...' -> '住吉区'）."""

    return place.split(",")[0].strip() or place


def _comparison_weight_rows(
    profiles: dict[str, dict[str, float]],
    mean_s_by_place: dict[str, float],
) -> list[dict[str, object]]:
    from nmincity.config import CATEGORY_NAMES

    rows: list[dict[str, object]] = []
    for label, rates in profiles.items():
        weakest = min(CATEGORY_NAMES, key=lambda category: rates.get(category, 0.0))
        rows.append(
            {
                "name": label,
                "weight": f"{mean_s_by_place[label]:.3f}",
                "rationale": f"最も弱い要素: {CATEGORY_NAMES.get(weakest, weakest)}（到達率 {rates.get(weakest, 0.0):.2f}）",
                "reference": "",
            }
        )
    return rows


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


def _target_category(
    requested: str | None,
    reach_by_origin: dict[object, dict[str, bool]],
    proposals_module,
) -> str:
    from nmincity.config import CATEGORY_WEIGHTS

    if requested:
        return requested

    deficiencies = proposals_module.find_deficiencies(reach_by_origin)
    missing_counts = Counter(
        category
        for missing_categories in deficiencies.values()
        for category in missing_categories
    )
    if not missing_counts:
        return max(CATEGORY_WEIGHTS, key=lambda category: (CATEGORY_WEIGHTS[category], category))
    return max(
        CATEGORY_WEIGHTS,
        key=lambda category: (
            float(CATEGORY_WEIGHTS[category]) * missing_counts.get(category, 0),
            float(CATEGORY_WEIGHTS[category]),
            category,
        ),
    )


def _node_latlon(graph, node, loader_module) -> tuple[float, float]:
    lon, lat = loader_module.node_lonlat(graph, node)
    return lat, lon


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
