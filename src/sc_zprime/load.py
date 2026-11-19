"""Load a benchmark checkout into tidy tables.

One adapter is implemented: the layout used by benchmarks built on the
`latch-eval-tools` harness, where a checkout looks like::

    evals/<category>/<task>.json
    trajectories/<task>/<provider>/<model>/<harness>/r<k>/result.json
    trajectories/<task>/<provider>/<model>/<harness>/r<k>/trajectory.json

SpatialBench uses the same tree with its task files under `example_evals/`
instead of `evals/`. Either name is accepted.

Nothing here executes code from the checkout. Files are read as JSON only.

Three tables come back:

tasks   one row per task
runs    one row per graded run (task x configuration x replicate)
fields  one row per graded field of each run

Reference values and submitted values stay in memory for the analysis. The
exporters in `report.py` write only tolerance-normalised quantities, so that
no benchmark answer is redistributed. See docs/DATA_POLICY.md.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from . import graders


@dataclass
class Benchmark:
    name: str
    root: Path
    tasks: pd.DataFrame
    runs: pd.DataFrame
    fields: pd.DataFrame
    graders: dict[str, dict]
    answers: dict[str, object]
    skipped: list[dict]


class NoBenchmarkFound(ValueError):
    """Raised when a path does not hold a readable benchmark checkout."""


def _read_json(path: Path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


TASK_DIRS = ("evals", "example_evals")


def task_dir(root: str | Path) -> Path | None:
    """The directory of task files in a checkout, or None if there is none."""
    for name in TASK_DIRS:
        if (Path(root) / name).is_dir():
            return Path(root) / name
    return None


def load_tasks(root: Path) -> tuple[pd.DataFrame, dict[str, dict]]:
    rows, grader_by_task = [], {}
    where = task_dir(root)
    for path in sorted(where.glob("*/*.json")) if where else []:
        spec = _read_json(path)
        if not isinstance(spec, dict) or "id" not in spec:
            continue
        grader = spec.get("grader") or {}
        meta = spec.get("metadata") or {}
        config = grader.get("config") or {}
        grader_by_task[spec["id"]] = grader
        rows.append({
            "task": spec["id"],
            "category": meta.get("task", path.parent.name),
            "platform": meta.get("kit"),
            "horizon": meta.get("time_horizon"),
            "grader_type": grader.get("type"),
            "n_fields": len(config.get("ground_truth") or {}),
            "has_canary": bool(spec.get("canary")),
        })
    return pd.DataFrame(rows), grader_by_task


def load_latch_layout(root: str | Path, name: str | None = None) -> Benchmark:
    """Load every graded run in a latch-eval-tools style checkout."""
    root = Path(root)
    name = name or root.name
    if task_dir(root) is None or not (root / "trajectories").is_dir():
        raise NoBenchmarkFound(
            f"{root} is not a benchmark checkout: expected evals/ (or example_evals/) and trajectories/ "
            "inside it. Pass the checkout itself, for example ../upstream/scbench.")
    tasks, grader_by_task = load_tasks(root)
    if tasks.empty:
        raise NoBenchmarkFound(f"no task files found under {task_dir(root)}")
    skipped = []
    for task, grader in list(grader_by_task.items()):
        if not graders.supported(grader):
            kind = grader.get("type") if isinstance(grader, dict) else None
            skipped.append({"task": task, "reason": f"grader type {kind!r} is not re-implemented"})
            del grader_by_task[task]
    run_rows, field_rows, answers, unknown = [], [], {}, 0
    for result_path in sorted((root / "trajectories").glob("*/*/*/*/*/result.json")):
        task, provider, model, harness, rep = result_path.parts[-6:-1]
        if task not in grader_by_task:
            unknown += 1
            continue
        doc = _read_json(result_path)
        result = doc.get("result") or {}
        published = result.get("grader_result") or {}
        answer = result.get("agent_answer")
        meta = result.get("metadata") or {}
        grader = grader_by_task[task]
        regraded = graders.grade(answer, grader)
        run_id = "/".join([task, provider, model, harness, rep])
        answers[run_id] = answer
        run_rows.append({
            "benchmark": name,
            "run_id": run_id,
            "task": task,
            "provider": provider,
            "model": model,
            "harness": harness,
            "config": f"{model} / {harness}",
            "rep": rep,
            "published_pass": bool(result.get("passed")),
            "regraded_pass": regraded.passed,
            "config_error": regraded.config_error,
            "score": regraded.score,
            "n_fields": len(regraded.fields),
            "n_fields_passed": sum(f.passed for f in regraded.fields.values()),
            "grader_version": doc.get("latch_eval_tools_version"),
            "runtime_s": doc.get("agent_runtime_seconds"),
            "cost_usd": meta.get("total_cost"),
            "n_steps": meta.get("n_steps", meta.get("n_turns")),
            "dir": str(result_path.parent),
        })
        config = grader.get("config") or {}
        tolerances = graders.tolerance_block(config) or {}
        published_metrics = published.get("metrics") or {}
        if regraded.config_error:
            continue
        for field_name, reference in (config.get("ground_truth") or {}).items():
            band = graders.band_for(float(reference), graders.tolerance_entry(tolerances, field_name))
            fr = regraded.fields[field_name]
            field_rows.append({
                "benchmark": name,
                "run_id": run_id,
                "task": task,
                "provider": provider,
                "model": model,
                "harness": harness,
                "config": f"{model} / {harness}",
                "rep": rep,
                "field": field_name,
                "kind": band.kind,
                "reference": float(reference),
                "band_lower": band.lower,
                "band_upper": band.upper,
                "lower_pinned_at_zero": band.lower_pinned_at_zero,
                "value": fr.value,
                "margin": fr.margin,
                "passed": fr.passed,
                "published_passed": published_metrics.get(f"{field_name}_pass"),
            })
    if not run_rows:
        raise NoBenchmarkFound(f"no graded runs found under {root / 'trajectories'} for a supported grader")
    if unknown:
        skipped.append({"task": "(runs)", "reason": f"{unknown} run(s) belong to a task that was skipped or has no task file"})
    runs = pd.DataFrame(run_rows)
    fields = pd.DataFrame(field_rows)
    tasks = tasks.assign(supported=tasks["task"].isin(grader_by_task))
    return Benchmark(name, root, tasks, runs, fields, grader_by_task, answers, skipped)
