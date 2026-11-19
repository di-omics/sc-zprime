"""What each benchmark in a family publishes, and so what can be checked from outside.

An assay kit can be validated by its user only as far as its controls ship
with it. The same holds for a benchmark. Whether an outside reader can
reproduce a verdict, grade a run, measure repeatability or trace a method
depends on which files are public:

- a grader config with its reference values: needed to grade anything;
- transcripts: needed to see what was done, and to recover an answer;
- per-run answer and verdict files: needed to reproduce a verdict rather
  than produce one;
- repeats of the same configuration: needed for repeatability;
- design notes: needed to know which method the authors intended.

This module counts those files per checkout. It also records three things
that show how the family's own design has moved: the harnesses and models in
the public runs, the version of the evaluation tool stamped on result files,
and the failure-mode label that newer task files carry in their metadata.

It reads the structure of the task files (their keys, grader types and
metadata labels), never a prompt, a reference value or an answer, and it
executes nothing.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

from . import graders, provenance

TASK_DIRS = ("evals", "example_evals", "sample-evals")
ANSWER_FILES = ("eval_answer.json", "analysis_output.json")
_FLAT_TRANSCRIPT = re.compile(r"(.+)__(.+)__(r\d+)\.json")


def find_tasks(root: str | Path) -> list[dict]:
    """Every task file in a checkout, whatever its layout.

    A task file is a JSON object with an `id` and a prompt or a grader. Three
    layouts occur: `<category>/<task>.json`, `<task>/eval.json` and `<task>.json`.
    Each entry carries the parsed spec and one normalised grader: the task's
    `grader`, or its list of `graders` wrapped as a `list_of`.
    """
    root = Path(root)
    out, seen = [], set()
    for name in TASK_DIRS:
        base = root / name
        if not base.is_dir():
            continue
        for path in sorted(list(base.glob("*.json")) + list(base.glob("*/*.json"))):
            try:
                with open(path, "r", encoding="utf-8") as handle:
                    spec = json.load(handle)
            except ValueError:
                continue
            if not isinstance(spec, dict) or "id" not in spec or spec["id"] in seen:
                continue
            if not ({"task", "grader", "graders"} & set(spec)):
                continue
            seen.add(spec["id"])
            grader = spec.get("grader")
            if not grader and isinstance(spec.get("graders"), list) and spec["graders"]:
                grader = {"type": "list_of", "config": {"children": spec["graders"]}}
            out.append({"task": str(spec["id"]), "path": path, "spec": spec,
                        "grader": grader if isinstance(grader, dict) else None})
    return out


def failure_modes(spec: dict) -> list[str]:
    """Top-level categories of the failure-mode labels in a task's metadata, without repeats."""
    meta = spec.get("metadata") if isinstance(spec.get("metadata"), dict) else {}
    labels = meta.get("failure_modes")
    if not isinstance(labels, list):
        return []
    out: list[str] = []
    for label in labels:
        category = str(label).split(".")[0]
        if category and category not in out:
            out.append(category)
    return out


def _runs(traj: Path) -> list[tuple[str, str, str, str, Path]]:
    """(task directory, model, harness, repeat, file) for every transcript.

    Two layouts are in use: <task>/<provider>/<model>/<harness>/r<k>/trajectory.json
    and <task>/<model>__<harness>__r<k>.json.
    """
    out = [(p.parts[-6], p.parts[-4], p.parts[-3], p.parts[-2], p) for p in sorted(traj.glob("*/*/*/*/*/trajectory.json"))]
    for p in sorted(traj.rglob("*.json")):
        hit = _FLAT_TRANSCRIPT.fullmatch(p.name)
        if hit:
            out.append((p.parent.name, hit.group(1), hit.group(2), hit.group(3), p))
    return out


def inventory_row(root: str | Path) -> dict | None:
    """One row for one checkout, or None if it holds no task files and no transcripts."""
    root = Path(root)
    tasks = find_tasks(root)
    traj = root / "trajectories"
    standard = sorted(traj.glob("*/*/*/*/*/trajectory.json")) if traj.is_dir() else []
    runs = _runs(traj) if traj.is_dir() else []
    if not tasks and not runs:
        return None
    with_grader = [t for t in tasks if t["grader"]]
    gradable = [t for t in with_grader if graders.gradable(t["grader"])]
    kinds = sorted({graders.describe(t["grader"]) for t in with_grader})
    verdicts = sum((p.parent / "result.json").exists() for p in standard)
    answers = sum(any((p.parent / name).exists() for name in ANSWER_FILES) for p in standard)
    cells: dict[tuple, int] = {}
    for task_dir, model, harness, _, _ in runs:
        key = (task_dir, model, harness)
        cells[key] = cells.get(key, 0) + 1
    configurations = len({key[1:] for key in cells})
    max_repeats = max(cells.values()) if cells else 0
    notes = sum(bool(t["spec"].get("notes")) for t in tasks)
    transcripts = len(runs)
    harness_counts: dict[str, int] = {}
    for _, _, harness, _, _ in runs:
        harness_counts[harness] = harness_counts.get(harness, 0) + 1
    tool_versions = set()
    stamped = 0
    for p in standard:
        result = p.parent / "result.json"
        if result.exists():
            try:
                with open(result, "r", encoding="utf-8") as handle:
                    version = json.load(handle).get("latch_eval_tools_version")
            except ValueError:
                version = None
            if version:
                tool_versions.add(str(version))
                stamped += 1
    metas = [t["spec"].get("metadata") if isinstance(t["spec"].get("metadata"), dict) else {} for t in tasks]
    labelled = [t for t in tasks if failure_modes(t["spec"])]
    taxonomy = sorted({str(m.get("failure_mode_taxonomy_version")) for m in metas if m.get("failure_modes") and m.get("failure_mode_taxonomy_version")})
    declared = sorted({str(m["grader_type"]) for m in metas if m.get("grader_type")})
    row = {
        "benchmark": root.name,
        "upstream_commit": (provenance.git_head(root) or "")[:7],
        "public_tasks": len(tasks),
        "tasks_with_a_public_grader": len(with_grader),
        "tasks_this_tool_can_grade": len(gradable),
        "grader_kinds": "; ".join(kinds) if kinds else "not published",
        "tasks_with_design_notes": notes,
        "transcripts": transcripts,
        "runs_with_an_answer_file": answers,
        "runs_with_a_published_verdict": verdicts,
        "configurations": configurations,
        "max_repeats": max_repeats,
        "summary_table": (root / "results").is_dir() and any((root / "results").iterdir()),
        "harnesses": "; ".join(f"{name} {count}" for name, count in sorted(harness_counts.items(), key=lambda kv: (-kv[1], kv[0]))),
        "models": len({model for _, model, _, _, _ in runs}),
        "eval_tool_versions": "; ".join(sorted(tool_versions, key=lambda v: [int(x) if x.isdigit() else 0 for x in v.split(".")])),
        "result_files_with_a_tool_version": stamped,
        "grader_types_declared_in_metadata": "; ".join(declared),
        "tasks_with_a_failure_mode_label": len(labelled),
        "failure_mode_taxonomy": "; ".join(taxonomy),
    }
    row["can_reproduce_verdicts"] = verdicts > 0 and len(gradable) > 0
    row["can_grade_from_transcripts"] = len(standard) > 0 and len(gradable) > 0
    row["can_measure_repeatability"] = verdicts > 0 and max_repeats >= 2
    row["can_trace_methods"] = transcripts > 0 and notes > 0
    return row


def inventory(upstream: str | Path, skip: tuple[str, ...] = ()) -> pd.DataFrame:
    """One row per benchmark checkout found directly under `upstream`."""
    rows = []
    for path in sorted(Path(upstream).iterdir(), key=lambda p: p.name.lower()):
        if not path.is_dir() or _skipped(path.name, skip):
            continue
        row = inventory_row(path)
        if row is not None:
            rows.append(row)
    return pd.DataFrame(rows)


def _skipped(name: str, skip: tuple[str, ...]) -> bool:
    return name in skip or any(name.startswith(prefix) for prefix in skip if prefix.endswith("-"))


def failure_mode_table(upstream: str | Path, skip: tuple[str, ...] = ()) -> pd.DataFrame:
    """How many public tasks of each benchmark carry each failure-mode category."""
    rows = []
    for path in sorted(Path(upstream).iterdir(), key=lambda p: p.name.lower()):
        if not path.is_dir() or _skipped(path.name, skip):
            continue
        counts: dict[str, int] = {}
        for task in find_tasks(path):
            for category in failure_modes(task["spec"]):
                counts[category] = counts.get(category, 0) + 1
        rows += [{"benchmark": path.name, "failure_mode": category, "tasks": count}
                 for category, count in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))]
    return pd.DataFrame(rows, columns=["benchmark", "failure_mode", "tasks"])


def run(upstream: str | Path, out: str | Path, skip: tuple[str, ...] = ()) -> dict:
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    table = inventory(upstream, skip)
    table.to_csv(out / "inventory.csv", index=False)
    modes = failure_mode_table(upstream, skip)
    modes.to_csv(out / "failure_modes.csv", index=False)
    summary = {
        "benchmarks": int(len(table)),
        "public_tasks": int(table["public_tasks"].sum()),
        "transcripts": int(table["transcripts"].sum()),
        "publish_a_grader_for_every_public_task": int((table["tasks_with_a_public_grader"] == table["public_tasks"]).sum()),
        "publish_no_grader": int((table["tasks_with_a_public_grader"] == 0).sum()),
        "publish_transcripts": int((table["transcripts"] > 0).sum()),
        "publish_per_run_verdicts": int((table["runs_with_a_published_verdict"] > 0).sum()),
        "publish_repeats": int((table["max_repeats"] >= 2).sum()),
        "can_reproduce_verdicts": sorted(table[table["can_reproduce_verdicts"]]["benchmark"]),
        "can_grade_from_transcripts_only": sorted(
            table[table["can_grade_from_transcripts"] & ~table["can_reproduce_verdicts"]]["benchmark"]),
        "can_measure_repeatability": sorted(table[table["can_measure_repeatability"]]["benchmark"]),
        "tasks_with_a_failure_mode_label": int(table["tasks_with_a_failure_mode_label"].sum()),
        "benchmarks_with_a_failure_mode_label": int((table["tasks_with_a_failure_mode_label"] > 0).sum()),
        "failure_mode_taxonomy_versions": sorted({v for cell in table["failure_mode_taxonomy"] for v in str(cell).split("; ") if v and v != "nan"}),
        "failure_mode_categories": int(modes["failure_mode"].nunique()) if len(modes) else 0,
        "most_common_failure_modes": [
            {"failure_mode": k, "tasks": int(v)} for k, v in
            modes.groupby("failure_mode")["tasks"].sum().sort_values(ascending=False, kind="stable").head(5).items()
        ] if len(modes) else [],
        "benchmarks_that_use_only_the_numeric_grader": sorted(
            table[table["grader_kinds"] == "numeric_tolerance"]["benchmark"]),
        "benchmarks_that_withhold_the_grader_and_declare_its_type": sorted(
            table[(table["tasks_with_a_public_grader"] == 0) & (table["grader_types_declared_in_metadata"] != "")]["benchmark"]),
        "skipped": list(skip),
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary
