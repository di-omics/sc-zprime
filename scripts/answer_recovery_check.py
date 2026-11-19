#!/usr/bin/env python3
"""Measure answer recovery against the runs whose answer file is published.

    scripts/answer_recovery_check.py ../upstream [out.csv]

scBench, SpatialBench and SpatialBench-Long publish each run's answer next to
its transcript. That makes them a test set for `sc_zprime.answers`, which
recovers an answer from the transcript alone. SpatialBench-Long withholds its
grader, so there the fields to look for are the keys of the published answer
and no verdict can be compared. It is the only one of the three with runs
from the pi harness. One row per benchmark and harness: the runs, the
runs whose answer was recovered, how the recovered answer was found (printed
by a step, written as a literal to the answer file, or tagged in a message),
the recovered answers that equal the published one exactly, the ones that get
the published verdict when graded, and the ones flagged because the answer
file was written again without showing what was written. Only counts are
written.
"""

import csv
import json
import sys
from pathlib import Path

from sc_zprime import answers, graders, load

BENCHMARKS = ("scbench", "spatialbench")
COLUMNS = ("runs", "answers_recovered", "printed", "written", "tagged", "equal_to_the_published_answer",
           "equal_among_printed", "equal_among_written", "same_verdict_as_published",
           "flagged_written_again_unseen", "equal_among_flagged")


def measure(upstream: Path) -> list[dict]:
    rows: dict[tuple, dict] = {}
    for name in BENCHMARKS:
        bench = load.load_latch_layout(upstream / name, name)
        for run in bench.runs.itertuples():
            row = rows.setdefault((name, run.harness), {"benchmark": name, "harness": run.harness, **{c: 0 for c in COLUMNS}})
            grader = bench.graders[run.task]
            found = answers.recover(Path(run.dir) / "trajectory.json", grader)
            row["runs"] += 1
            if found.answer is None:
                continue
            equal = found.answer == bench.answers[run.run_id]
            row["answers_recovered"] += 1
            row[found.source] += 1
            row["equal_to_the_published_answer"] += int(equal)
            if found.source in ("printed", "written"):
                row["equal_among_" + found.source] += int(equal)
            row["same_verdict_as_published"] += int(graders.grade(found.answer, grader).passed == bool(run.published_pass))
            if found.written_again_unseen:
                row["flagged_written_again_unseen"] += 1
                row["equal_among_flagged"] += int(equal)
    # A benchmark with answers and no public grader: fields from the answer's own keys, no verdict.
    long_root = upstream / "spatialbench-long" / "trajectories"
    for answer_path in sorted(long_root.glob("*/*/*/*/*/eval_answer.json")):
        harness = answer_path.parts[-3]
        row = rows.setdefault(("spatialbench-long", harness),
                              {"benchmark": "spatialbench-long", "harness": harness, **{c: 0 for c in COLUMNS}})
        row["runs"] += 1
        try:
            truth = json.loads(answer_path.read_text(encoding="utf-8"))
        except ValueError:
            continue
        if not isinstance(truth, dict) or not truth:
            continue
        found = answers.recover(answer_path.parent / "trajectory.json", None, fields=set(truth))
        if found.answer is None:
            continue
        equal = found.answer == truth
        row["answers_recovered"] += 1
        row[found.source] += 1
        row["equal_to_the_published_answer"] += int(equal)
        if found.source in ("printed", "written"):
            row["equal_among_" + found.source] += int(equal)
        if found.written_again_unseen:
            row["flagged_written_again_unseen"] += 1
            row["equal_among_flagged"] += int(equal)
    for (name, _), row in rows.items():
        if name == "spatialbench-long":
            row["same_verdict_as_published"] = ""
    return [rows[key] for key in sorted(rows)]


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    rows = measure(Path(sys.argv[1]))
    out = open(sys.argv[2], "w", newline="", encoding="utf-8") if len(sys.argv) > 2 else sys.stdout
    writer = csv.DictWriter(out, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
