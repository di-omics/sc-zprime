"""Command line entry point.

    sc-zprime run --upstream path/to/scbench --out results/scbench
    sc-zprime regrade --upstream path/to/variantbench --out results/variantbench
    sc-zprime inventory --upstream path/to/all/checkouts --out results/family
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import load, report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="sc-zprime", description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="validate a benchmark checkout and write tables and cards")
    run.add_argument("--upstream", required=True, help="path to a benchmark checkout (latch-eval-tools layout)")
    run.add_argument("--out", required=True, help="directory for result tables and validation cards")
    run.add_argument("--annotations", default=None,
                     help="directory of reviewed method labels (default: the labels shipped with the package)")
    run.add_argument("--name", default=None, help="benchmark name used in the outputs")
    run.add_argument("--figures", action="store_true", help="also draw the figures")
    again = sub.add_parser("regrade", help="grade a benchmark that publishes transcripts but no verdicts")
    again.add_argument("--upstream", required=True, help="path to a benchmark checkout")
    again.add_argument("--out", required=True, help="directory for the tables")
    again.add_argument("--name", default=None, help="benchmark name used in the outputs")
    family = sub.add_parser("inventory", help="list what each benchmark checkout publishes")
    family.add_argument("--upstream", required=True, help="directory that holds the benchmark checkouts")
    family.add_argument("--out", required=True, help="directory for the table")
    family.add_argument("--skip", action="append", default=[],
                        help="a checkout to leave out; a name ending in - leaves out every checkout it prefixes")
    family.add_argument("--figures", action="store_true", help="also draw the figure")
    args = parser.parse_args(argv)

    try:
        if args.command == "regrade":
            from . import regrade

            summary = regrade.run(args.upstream, args.out, args.name)
        elif args.command == "inventory":
            from . import inventory

            summary = inventory.run(args.upstream, args.out, tuple(args.skip))
        else:
            summary = report.run(args.upstream, args.out, args.annotations, args.name)
    except load.NoBenchmarkFound as problem:
        parser.exit(2, f"sc-zprime: {problem}\n")
    if args.command in ("run", "inventory") and args.figures:
        from . import figures

        (figures.draw_all if args.command == "run" else figures.draw_family)(args.out)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
