"""n分都市化支援ツールの CLI スタブ."""

from __future__ import annotations

import argparse

from nmincity.config import MODES


def build_parser() -> argparse.ArgumentParser:
    """CLI パーサを構築する."""

    parser = argparse.ArgumentParser(prog="nmincity")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="指定地区の n分都市度を計算する")
    run_parser.add_argument("--place", required=True, help="対象地区名")
    run_parser.add_argument("--minutes", type=float, default=15, help="到達圏の分数")
    run_parser.add_argument("--mode", choices=MODES, default="walk", help="移動手段")
    run_parser.set_defaults(func=run)

    return parser


def run(args: argparse.Namespace) -> int:
    """M1 で実処理を追加する run サブコマンド."""

    print(
        "M1で実装: "
        f"place={args.place}, minutes={args.minutes:g}, mode={args.mode}"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI エントリポイント."""

    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())

