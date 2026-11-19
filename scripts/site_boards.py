#!/usr/bin/env python3
"""List the boards on benchmarks.bio and what the site says about each one.

    python scripts/site_boards.py --out results/suite

Reads only the plain-text pages the site publishes for machine reading:
its index (`llms.txt`), the overall results page and one page per board.
It takes board-level facts and nothing else: the board's name, its area and
horizon, the size of its current evaluation set, whether it counts toward
the site's overall score, the scoring rule for refusals where the page
states one, and the repository it links. No result of any model is read or
written.

The 6 biosecurity boards are left out on purpose. Their rows in the site's
inventory table are counted, and their pages are never requested.

The site moves. The output carries the site's own data date, and
`docs/SUITE.md` is checked against the committed table, not the live site.
"""

import argparse
import csv
import json
import re
import urllib.request
from pathlib import Path

SITE = "https://benchmarks.bio"
LEFT_OUT = "BioSecBench"
# The plain-text page of this board links no repository. The footer of the rendered site links this one, and it
# is the name pinned in scripts/fetch_upstream.sh.
REPOSITORY_IF_NOT_LINKED = {"TissueMicroscopyBench": "tissuemicroscopybench"}
# A second guard, so that a renamed biosecurity board is refused and not read.
NEVER_READ = re.compile(r"biosec|surveillance|respvirus|respiratory|refusal|structure|function", re.I)
FIELDS = ["board", "area", "horizon", "evaluations", "original_study_evaluations", "counts_toward_overall_score",
          "overall_weight", "refusal_rule_stated", "repository", "board_page", "data_updated"]


def get(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=40) as response:
        return response.read().decode("utf-8", errors="replace")


def flat(text: str) -> str:
    return " ".join(text.split())


def inventory_rows(overall: str) -> list[dict]:
    """The site's own inventory table: one row per board."""
    section = overall[overall.index("## Benchmark inventory"):]
    section = section[:section.index("\n## ", 3)]
    rows = []
    for line in section.splitlines():
        if not line.startswith("| ["):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        name, page = re.match(r"\[([^\]]+)\]\(([^)]+)\)", cells[0]).groups()
        weight = cells[3] if cells[3].isdigit() else ""
        rows.append({"board": name, "board_page": page, "evaluations": int(cells[2]), "overall_weight": weight,
                     "assessment": cells[4], "inclusion": cells[5]})
    return rows


def refusal_rule(page: str) -> str:
    """What the board page states about refusals, if it states anything."""
    text = flat(page)
    if re.search(r"[Rr]efusals[^.]*\bleave the denominator", text):
        return "leaves the denominator"
    if re.search(r"[Rr]efusals[^.]*\bremain in the denominator", text):
        return "stays in the denominator"
    if re.search(r"[Rr]efusals[^.]*\bare failures", text):
        return "a failure"
    return ""


def read(out: Path) -> dict:
    index = get(f"{SITE}/llms.txt")
    markdown = dict(re.findall(r"- \[([^\]]+)\]\([^)]+\).*?\[Markdown\]\(([^)]+)\)", index))
    overall = get(f"{SITE}/results/v1/index.md")
    rows = inventory_rows(overall)
    left_out = [r for r in rows if r["board"].startswith(LEFT_OUT)]
    kept = [r for r in rows if not r["board"].startswith(LEFT_OUT)]

    boards = []
    for row in kept:
        if NEVER_READ.search(row["board"] + " " + row["board_page"] + " " + markdown[row["board"]]):
            raise SystemExit(f"refusing to read {row['board']}: it may be a biosecurity board")
        page = get(markdown[row["board"]])
        text = flat(page)
        original = re.search(r"The original .{1,60}? study reports (\d+) evaluations", text)
        linked = re.search(r"\[Repository\]\(https://github\.com/latchbio/([^)/]+)\)", page)
        boards.append({
            "board": row["board"],
            "area": re.search(r"^- Domain: (.+)$", page, re.M).group(1).strip(),
            "horizon": re.search(r"^- Horizon: (.+)$", page, re.M).group(1).strip(),
            "evaluations": row["evaluations"],
            "original_study_evaluations": original.group(1) if original else "",
            "counts_toward_overall_score": row["inclusion"].startswith("Included"),
            "overall_weight": row["overall_weight"],
            "refusal_rule_stated": refusal_rule(page),
            "repository": linked.group(1) if linked else REPOSITORY_IF_NOT_LINKED[row["board"]],
            "board_page": row["board_page"],
            "data_updated": re.search(r"Data updated:? (\d{4}-\d{2}-\d{2})", text).group(1),
        })

    said = flat(overall)
    counted, capability = map(int, re.search(r"(\d+) of (\d+) published capability benchmarks contribute", said).groups())
    site = {
        "source": f"{SITE}/llms.txt, {SITE}/results/v1/index.md and 1 page per board",
        "data_updated": sorted({b["data_updated"] for b in boards})[-1],
        "leaderboards": len(rows),
        "capability_benchmarks": capability,
        "scored_apart_as_safeguards": sum(r["inclusion"].startswith("Separate") for r in rows),
        "contribute_to_the_overall_score": counted,
        "missing_boards_allowed_in_the_overall_score": int(re.search(r"allow at most (\d+) missing benchmarks", said).group(1)),
        "boards_read": len(boards),
        "evaluations_on_the_boards_read": sum(b["evaluations"] for b in boards),
        "boards_read_that_count_toward_the_overall_score": sum(b["counts_toward_overall_score"] for b in boards),
        "boards_read_that_state_a_refusal_rule": sum(bool(b["refusal_rule_stated"]) for b in boards),
        "boards_read_whose_current_set_differs_from_the_original_study": sum(
            bool(b["original_study_evaluations"]) and int(b["original_study_evaluations"]) != b["evaluations"] for b in boards),
        "biosecurity_boards_left_out": len(left_out),
        "biosecurity_evaluations_left_out": sum(r["evaluations"] for r in left_out),
        "biosecurity_boards_that_count_toward_the_overall_score": sum(r["inclusion"].startswith("Included") for r in left_out),
    }

    out.mkdir(parents=True, exist_ok=True)
    with open(out / "boards.csv", "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(boards)
    (out / "site.json").write_text(json.dumps(site, indent=2) + "\n")
    return site


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", default="results/suite", help="folder for boards.csv and site.json")
    parser.add_argument("--figure", action="store_true", help="also draw the figure (needs the package installed)")
    parser.add_argument("--family", default="results/family", help="folder with inventory.csv, for the figure")
    args = parser.parse_args()
    print(json.dumps(read(Path(args.out)), indent=2))
    if args.figure:
        from sc_zprime import figures

        figures.draw_suite(args.out, args.family)


if __name__ == "__main__":
    main()
