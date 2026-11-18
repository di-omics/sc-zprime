"""Command line entry point.

    sc-zprime run --upstream path/to/scbench --out results/scbench
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
    args = parser.parse_args(argv)

    try:
        summary = report.run(args.upstream, args.out, args.annotations, args.name)
    except load.NoBenchmarkFound as problem:
        parser.exit(2, f"sc-zprime: {problem}\n")
    if args.figures:
        from . import figures

        figures.draw_all(args.out)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
