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
    run_parser.set_defaults(func=run)

    return parser


def run(args: argparse.Namespace) -> int:
    """OSM 実データから機能A(MVP)の近接性スコア地図を生成する."""

    from nmincity.backend.osmnx_backend import OsmnxBackend
    from nmincity.core.score import proximity_score
    from nmincity.config import score_label
    from nmincity.data import loader
    from nmincity.viz.maps import save_map, score_map

    graph = loader.load_graph(args.place, args.mode)
    category_nodes = loader.load_category_nodes(graph, args.place)
    backend = OsmnxBackend(graph, category_nodes, args.mode)

    points: list[tuple[float, float, float]] = []
    scores: list[float] = []
    labels: Counter[str] = Counter()
    origins = loader.make_origins(graph, args.sample)

    for origin in origins:
        reach = backend.reachable_categories(origin, args.minutes, args.mode)
        score = proximity_score(reach)
        lon, lat = loader.node_lonlat(graph, origin)
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
    print(f"score: avg={average:.3f}, min={minimum:.3f}, max={maximum:.3f}")
    print(
        "labels: "
        f"良好={labels['良好']}, 要改善={labels['要改善']}, 不足={labels['不足']}"
    )
    print(f"map: {output_path}")
    return 0


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
