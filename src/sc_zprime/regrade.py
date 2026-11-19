"""Grade a benchmark that publishes transcripts and grader configs, but no verdicts.

scBench and SpatialBench publish, for every run, the answer file and the
verdict. `sc-zprime run` reproduces those verdicts and then measures them.
Other benchmarks in the family publish less: the task files with their
grader configs, and one transcript per task and configuration. For those the
only thing that can be done from outside is a first grading:

1. recover the answer each run left behind from its transcript (`answers.py`),
2. grade it with the independent graders (`graders.py`),
3. say how each failing field failed: no such field, the wrong shape, or the
   wrong value.

This is weaker evidence than a reproduced verdict, in two ways that every
output repeats. There is no published verdict to compare with, so a mistake
in recovery or in a grader would not show. And with one repeat of four or
five configurations per task there is nothing to say about repeatability and
little about rates.

Outputs carry no answer, no reference value and no label: only pass or fail,
the reason a field failed, and for a set grader one of 3 bands that say how
its similarity score compares with its pass threshold. The score itself is
not written: over a short list it is a fraction with a small denominator,
which would say something about the length of the reference list. Per-run
margins of numeric fields are not written either, in line with
docs/DATA_POLICY.md. A grader whose config is invalid leaves a run out
of the counts, where the upstream tool would count it as failed; no public
config does this.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

from . import __version__, answers, graders, inventory, load, provenance

_VERSION_SUFFIX = re.compile(r"__v\d+$")
NEAR = 0.25


def score_band(gap) -> str | None:
    """A set grader's score against its pass threshold, as one of 3 bands."""
    if gap is None or pd.isna(gap):
        return None
    if gap >= 0:
        return "at or above"
    return f"under {NEAR} below" if gap > -NEAR else f"{NEAR} or more below"


def run_directories(root: Path) -> list[tuple[str, Path]]:
    """(task id, run directory) for every transcript. A trailing version tag on the task directory is dropped."""
    out = []
    for path in sorted((root / "trajectories").glob("*/*/*/*/*/trajectory.json")):
        out.append((_VERSION_SUFFIX.sub("", path.parts[-6]), path.parent))
    return out


def eval_version(run_dir: Path) -> str:
    """The eval version a run directory names, or an empty string. The task files carry no version to compare it with."""
    hit = _VERSION_SUFFIX.search(run_dir.parts[-5])
    return hit.group(0)[2:] if hit else ""


def regrade(root: str | Path, name: str | None = None) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Tables of tasks, runs and graded fields for a transcript-only checkout."""
    root = Path(root)
    name = name or root.name
    found_tasks = inventory.find_tasks(root)
    if not found_tasks or not (root / "trajectories").is_dir():
        raise load.NoBenchmarkFound(
            f"{root} is not a benchmark checkout: expected task files and trajectories/ inside it.")
    grader_by_task = {t["task"]: t["grader"] for t in found_tasks}
    tasks = pd.DataFrame([{
        "task": t["task"],
        "category": (t["spec"].get("metadata") or {}).get("task"),
        "platform": (t["spec"].get("metadata") or {}).get("kit"),
        "horizon": (t["spec"].get("metadata") or {}).get("time_horizon"),
        "grader": graders.describe(t["grader"]),
        "gradable": graders.gradable(t["grader"]),
        "graded_fields": len(answers.graded_fields(t["grader"])),
        "has_design_notes": bool(t["spec"].get("notes")),
        "failure_modes": "; ".join(inventory.failure_modes(t["spec"])),
    } for t in found_tasks])
    run_rows, field_rows = [], []
    for task, run_dir in run_directories(root):
        provider, model, harness, rep = run_dir.parts[-4:]
        grader = grader_by_task.get(task)
        row = {"benchmark": name, "task": task, "provider": provider, "model": model, "harness": harness,
               "config": f"{model} / {harness}", "rep": rep, "eval_version": eval_version(run_dir),
               "verdict_published": (run_dir / "result.json").exists(),
               "grader_public": bool(grader), "gradable": graders.gradable(grader),
               "answer_source": "", "answers_shown": None, "verdict_depends_on_which_answer": None,
               "answer_file_written_again_unseen": None,
               "graded": False, "passed": None, "n_fields": None, "n_fields_passed": None}
        if row["gradable"]:
            found = answers.recover(run_dir / "trajectory.json", grader)
            row["answer_source"] = found.source
            if found.answer is not None:
                result = graders.grade(found.answer, grader)
                if result.config_error is None:
                    verdicts = {graders.grade(other, grader).passed for other in found.shown}
                    row.update(graded=True, passed=bool(result.passed), n_fields=len(result.fields),
                               n_fields_passed=sum(f.passed for f in result.fields.values()),
                               answers_shown=len(found.shown), verdict_depends_on_which_answer=len(verdicts) > 1,
                               answer_file_written_again_unseen=bool(found.written_again_unseen))
                    for field in result.fields.values():
                        field_rows.append({
                            "benchmark": name, "task": task, "config": row["config"], "rep": rep,
                            "field": field.name, "kind": field.kind, "passed": bool(field.passed),
                            "score_vs_threshold": score_band(field.gap),
                            "reason": field.reason, "near_miss": field.near_miss,
                        })
        run_rows.append(row)
    if not run_rows:
        raise load.NoBenchmarkFound(f"no transcripts found under {root / 'trajectories'}")
    runs = pd.DataFrame(run_rows)
    fields = pd.DataFrame(field_rows, columns=["benchmark", "task", "config", "rep", "field", "kind", "passed",
                                               "score_vs_threshold", "reason", "near_miss"])
    per_task = runs.groupby("task").agg(runs=("task", "size"), answers_recovered=("graded", "sum"),
                                        passed=("passed", lambda s: int(sum(v is True for v in s))))
    tasks = tasks.merge(per_task, left_on="task", right_index=True, how="left")
    for column in ("runs", "answers_recovered", "passed"):
        tasks[column] = tasks[column].fillna(0).astype(int)
    return tasks, runs, fields


def run(upstream: str | Path, out: str | Path, name: str | None = None) -> dict:
    upstream, out = Path(upstream), Path(out)
    out.mkdir(parents=True, exist_ok=True)
    tasks, runs, fields = regrade(upstream, name)
    tasks.to_csv(out / "tasks.csv", index=False)
    runs.drop(columns=["provider"]).to_csv(out / "regrade_runs.csv", index=False)
    fields.to_csv(out / "regrade_fields.csv", index=False)

    gradable = runs[runs["gradable"]]
    graded = runs[runs["graded"]]
    failed = fields[~fields["passed"]]
    summary = {
        "tool_version": __version__,
        "benchmark": name or upstream.name,
        "upstream_commit": provenance.git_head(upstream),
        "kind": "first grading from transcripts; no published verdicts to compare with",
        "tasks": int(len(tasks)),
        "tasks_with_a_public_grader": int((tasks["grader"] != "not published").sum()),
        "tasks_gradable": int(tasks["gradable"].sum()),
        "transcripts": int(len(runs)),
        "configurations": int(runs["config"].nunique()),
        "max_repeats_per_configuration": int(runs.groupby(["task", "config"]).size().max()),
        "runs_with_a_published_verdict": int(runs["verdict_published"].sum()),
        "runs_gradable": int(len(gradable)),
        "answers_recovered": int(len(graded)),
        "answer_sources": {k: int(v) for k, v in gradable["answer_source"].value_counts().sort_index().items()},
        "runs_passed": int(sum(v is True for v in graded["passed"])),
        "recovered_answers_that_are_the_only_one_shown": int((graded["answers_shown"] <= 1).sum()),
        "recovered_answers_where_the_verdict_depends_on_which": int(sum(v is True for v in graded["verdict_depends_on_which_answer"])),
        "recovered_answers_where_the_file_was_written_again_unseen": int(sum(v is True for v in graded["answer_file_written_again_unseen"])),
        "recovered_answers_by_harness": {k: int(v) for k, v in graded["harness"].value_counts().sort_index().items()},
        "transcripts_by_harness": {k: int(v) for k, v in runs["harness"].value_counts().sort_index().items()},
        "tasks_no_run_passed": int(((tasks["gradable"]) & (tasks["answers_recovered"] > 0) & (tasks["passed"] == 0)).sum()),
        "tasks_every_run_passed": int(((tasks["answers_recovered"] > 0) & (tasks["passed"] == tasks["answers_recovered"])).sum()),
        "fields_graded": int(len(fields)),
        "fields_failed": int(len(failed)),
        "failed_fields_by_reason": {k: int(v) for k, v in failed["reason"].value_counts().sort_index().items()},
        "failed_fields_by_kind": {k: int(v) for k, v in failed["kind"].value_counts().sort_index().items()},
        "failed_fields_a_change_of_form_would_pass": int((failed["near_miss"] != "").sum()),
        "runs_failed_on_form_alone": _form_only(runs, fields),
        "by_failure_mode": _by_failure_mode(tasks),
        "grader_kinds_checked_against_published_verdicts": list(graders.CHECKED),
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def _by_failure_mode(tasks: pd.DataFrame) -> list[dict]:
    """Graded and passed runs under each failure-mode category. A task with two labels counts under both."""
    totals: dict[str, list[int]] = {}
    for row in tasks.itertuples():
        for category in [c for c in str(row.failure_modes).split("; ") if c and c != "nan"]:
            entry = totals.setdefault(category, [0, 0, 0])
            entry[0] += 1
            entry[1] += int(row.answers_recovered)
            entry[2] += int(row.passed)
    return [{"failure_mode": k, "tasks": v[0], "answers_recovered": v[1], "passed": v[2]}
            for k, v in sorted(totals.items(), key=lambda kv: (-kv[1][0], kv[0]))]


def _form_only(runs: pd.DataFrame, fields: pd.DataFrame) -> int:
    """Runs that failed, and whose every failing field failed on shape or on a near miss of form, not on value."""
    if fields.empty:
        return 0
    count = 0
    for _, group in fields.groupby(["task", "config", "rep"]):
        bad = group[~group["passed"]]
        if len(bad) and ((bad["reason"].isin(["wrong_type"])) | (bad["near_miss"] != "")).all():
            count += 1
    return count
