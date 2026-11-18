#!/usr/bin/env python3
"""Compare two result directories table by table.

    scripts/compare_results.py committed_dir regenerated_dir [--tolerance 0.005]

Without --tolerance every CSV, Markdown and JSON file must be identical
(summary.json is compared without its environment block). That is the check
to use on one machine.

With --tolerance, CSV files are compared cell by cell: text must match and
numbers must agree within the tolerance. Markdown and JSON are then only
checked for presence. That is the check to use across machines, where a
bootstrap percentile can differ in the last printed digit.

Figures are not compared: rendered images depend on the fonts installed.
Exit status 0 if everything matches, 1 otherwise.
"""

import argparse
import csv
import json
import sys
from pathlib import Path

TEXT = {".csv", ".md", ".json"}


def table_files(root: Path) -> dict:
    return {p.relative_to(root).as_posix(): p for p in sorted(root.rglob("*")) if p.is_file() and p.suffix in TEXT}


def normalise(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    if path.name != "summary.json":
        return text
    doc = json.loads(text)
    doc.pop("environment", None)
    return json.dumps(doc, indent=2, sort_keys=True)


def csv_matches(a: Path, b: Path, tolerance: float) -> bool:
    with open(a, newline="", encoding="utf-8") as fa, open(b, newline="", encoding="utf-8") as fb:
        ra, rb = list(csv.reader(fa)), list(csv.reader(fb))
    if len(ra) != len(rb):
        return False
    for row_a, row_b in zip(ra, rb):
        if len(row_a) != len(row_b):
            return False
        for x, y in zip(row_a, row_b):
            if x == y:
                continue
            try:
                if abs(float(x) - float(y)) > tolerance:
                    return False
            except ValueError:
                return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("committed")
    parser.add_argument("regenerated")
    parser.add_argument("--tolerance", type=float, default=None)
    args = parser.parse_args()
    a, b = Path(args.committed), Path(args.regenerated)
    fa, fb = table_files(a), table_files(b)
    problems = [f"only in {a}: {k}" for k in sorted(set(fa) - set(fb))]
    problems += [f"only in {b}: {k}" for k in sorted(set(fb) - set(fa))]
    compared = 0
    for key in sorted(set(fa) & set(fb)):
        if args.tolerance is None:
            same = normalise(fa[key]) == normalise(fb[key])
        elif key.endswith(".csv"):
            same = csv_matches(fa[key], fb[key], args.tolerance)
        else:
            continue
        compared += 1
        if not same:
            problems.append(f"differs: {key}")
    for line in problems:
        print(line)
    print(f"{compared - sum(p.startswith('differs') for p in problems)} of {compared} compared files match")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
