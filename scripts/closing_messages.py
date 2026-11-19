#!/usr/bin/env python3
"""Count the runs whose last stored message names a batch effect.

    scripts/closing_messages.py ../upstream/spatialbench [out.csv]

On the three batch-correction tasks of the public SpatialBench sample, an
agent is asked to cluster a multi-sample dataset and report a number that
says how far the clusters follow sample identity. This script asks one narrow
question of each transcript: does the last assistant text it stores name a
batch effect, or say that the data was not corrected or integrated?

It is a keyword match, with three limits. A transcript that stores no
assistant text counts as not saying so, and how many store any differs by
provider, so the table gives both counts for each provider. It also gives
the median length of the last stored text, since a last text that is only
the answer cannot name anything. The last stored text is not always
the closing message: some transcripts store an opening plan and nothing
after it. And a match does not prove the sentence is about the submitted
number. Only counts are written. No transcript text is copied. Transcripts
are parsed as JSON and never executed.
"""

import csv
import re
import statistics
import sys
from pathlib import Path

from sc_zprime import trajectory

TASKS = ("NORM01_batch_correction", "DR01_batch_confounded_clustering", "curio_ovary_batch_driven_clustering")

NAMES_IT = re.compile(
    r"batch[- ]effects?|batch[- ]correct\w*|batch[- ]driven|donor[- ]driven"
    r"|without (?:batch )?(?:correction|integration)|non-integrated|unintegrated|no integration", re.I)


def count(root: Path) -> list[dict]:
    rows = []
    for task in TASKS:
        runs = with_text = names_it = 0
        by_provider: dict[str, int] = {}
        runs_by: dict[str, int] = {}
        text_by: dict[str, int] = {}
        lengths: dict[str, list[int]] = {}
        for path in sorted((root / "trajectories" / task).glob("*/*/*/*/trajectory.json")):
            runs += 1
            provider = path.parts[-5]
            runs_by[provider] = runs_by.get(provider, 0) + 1
            texts = trajectory.assistant_texts(trajectory.load_document(path))
            with_text += bool(texts)
            text_by[provider] = text_by.get(provider, 0) + bool(texts)
            if texts:
                lengths.setdefault(provider, []).append(len(texts[-1]))
            if texts and NAMES_IT.search(texts[-1]):
                names_it += 1
                by_provider[provider] = by_provider.get(provider, 0) + 1
        rows.append({"task": task, "runs": runs, "runs_with_any_assistant_text": with_text,
                     "last_text_names_a_batch_effect": names_it,
                     "of_those_by_provider": _counts(by_provider),
                     "runs_by_provider": _counts(runs_by),
                     "with_any_assistant_text_by_provider": _counts(text_by),
                     "median_chars_of_last_text_by_provider": "; ".join(
                         f"{k} {int(statistics.median(v))}" for k, v in sorted(lengths.items()))})
    return rows


def _counts(by: dict[str, int]) -> str:
    return "; ".join(f"{k} {v}" for k, v in sorted(by.items(), key=lambda kv: (-kv[1], kv[0])))


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    rows = count(Path(sys.argv[1]))
    out = open(sys.argv[2], "w", newline="", encoding="utf-8") if len(sys.argv) > 2 else sys.stdout
    writer = csv.DictWriter(out, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
