"""Grading from transcripts, and the family inventory, on small synthetic checkouts."""

import json

import pandas as pd
import pytest

from sc_zprime import inventory, load, regrade

NUMERIC = {"type": "numeric_tolerance", "config": {"ground_truth": {"n": 10}, "tolerances": {"n": {"type": "absolute", "value": 2}}}}
LABELS = {"type": "label_set_jaccard", "config": {"ground_truth_labels": ["alpha-label", "beta-label"], "answer_field": "names",
                                                   "scoring": {"pass_threshold": 1}}}


def transcript(run_dir, shown):
    run_dir.mkdir(parents=True, exist_ok=True)
    messages = [{"role": "assistant", "content": "", "tool_calls": [{"id": "c0", "function": {"arguments": json.dumps({"command": "cat eval_answer.json"})}}]},
                {"role": "tool", "tool_call_id": "c0", "content": json.dumps({"returncode": 0, "output": shown})}]
    (run_dir / "trajectory.json").write_text(json.dumps({"messages": messages}))


def make(root):
    """Three tasks in the three layouts, one of them with no public grader."""
    files = {"evals/one/eval.json": {"id": "one", "task": "prompt", "grader": NUMERIC, "notes": "why", "metadata": {"task": "cat", "kit": "kit"}},
             "evals/two.json": {"id": "two", "task": "prompt", "graders": [NUMERIC, LABELS]},
             "evals/cat/three.json": {"id": "three", "task": "prompt", "metadata": {}},
             "evals/manifest.json": [{"eval_id": "one"}]}
    for name, body in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(body))
    base = root / "trajectories"
    transcript(base / "one__v123" / "prov" / "m1" / "h" / "r1", json.dumps({"n": 11}))
    transcript(base / "one__v123" / "prov" / "m2" / "h" / "r1", "n is 11, written to the answer file")
    transcript(base / "two" / "prov" / "m1" / "h" / "r1", json.dumps({"n": 30, "names": ["beta-label", "alpha-label"]}))
    transcript(base / "three" / "prov" / "m1" / "h" / "r1", json.dumps({"n": 1}))
    return root


def test_every_layout_is_found_and_a_version_tag_on_the_run_directory_is_dropped(tmp_path):
    root = make(tmp_path / "bench")
    assert sorted(t["task"] for t in inventory.find_tasks(root)) == ["one", "three", "two"]
    tasks, runs, fields = regrade.regrade(root, "bench")
    assert set(runs["task"]) == {"one", "two", "three"}
    by = runs.set_index(["task", "model"])
    assert by.loc[("one", "m1"), "passed"] is True or bool(by.loc[("one", "m1"), "passed"])
    assert by.loc[("one", "m2"), "answer_source"] == "none" and not by.loc[("one", "m2"), "graded"]
    assert not bool(by.loc[("two", "m1"), "passed"]) and by.loc[("two", "m1"), "n_fields_passed"] == 1
    assert not by.loc[("three", "m1"), "gradable"] and not by.loc[("three", "m1"), "grader_public"]
    assert dict(zip(tasks["task"], tasks["grader"])) == {
        "one": "numeric_tolerance", "two": "list_of(label_set_jaccard + numeric_tolerance)", "three": "not published"}


def test_the_written_tables_hold_no_answer_and_no_reference(tmp_path):
    root = make(tmp_path / "bench")
    summary = regrade.run(root, tmp_path / "out", "bench")
    assert summary["runs_with_a_published_verdict"] == 0 and summary["answers_recovered"] == 2
    assert summary["runs_passed"] == 1 and summary["failed_fields_by_reason"] == {"value": 1}
    written = "".join(p.read_text() for p in (tmp_path / "out").iterdir())
    assert "alpha-label" not in written and "beta-label" not in written
    fields = pd.read_csv(tmp_path / "out" / "regrade_fields.csv")
    assert set(fields["kind"]) == {"numeric", "label_set"}
    assert "margin" not in fields.columns, "per-run margins are published for traced tasks only"
    assert "score_minus_threshold" not in fields.columns, "a set grader's score is written as a band, never as a number"
    assert set(fields["score_vs_threshold"].dropna()) <= {"at or above", "under 0.25 below", "0.25 or more below"}
    runs = pd.read_csv(tmp_path / "out" / "regrade_runs.csv")
    assert set(runs.loc[runs["task"] == "one", "eval_version"].astype(str)) == {"v123"}


def test_a_directory_that_is_not_a_checkout_is_refused(tmp_path):
    with pytest.raises(load.NoBenchmarkFound):
        regrade.regrade(tmp_path)


def test_the_inventory_says_what_each_checkout_lets_an_outside_reader_check(tmp_path):
    family = tmp_path / "family"
    make(family / "transcripts-only")
    full = family / "with-verdicts"
    (full / "evals" / "cat").mkdir(parents=True)
    (full / "evals" / "cat" / "t.json").write_text(json.dumps({"id": "t", "task": "p", "grader": NUMERIC, "notes": "n"}))
    for rep in ("r1", "r2", "r3"):
        run = full / "trajectories" / "t" / "prov" / "m1" / "h" / rep
        transcript(run, json.dumps({"n": 10}))
        (run / "result.json").write_text(json.dumps({"result": {"agent_answer": {"n": 10}, "passed": True}}))
        (run / "eval_answer.json").write_text(json.dumps({"n": 10}))
    (family / "tooling").mkdir()
    (family / "left-out").mkdir()
    table = inventory.inventory(family, skip=("left-",)).set_index("benchmark")
    assert list(table.index) == ["transcripts-only", "with-verdicts"]
    a, b = table.loc["transcripts-only"], table.loc["with-verdicts"]
    assert (a["public_tasks"], a["tasks_with_a_public_grader"], a["tasks_this_tool_can_grade"], a["transcripts"]) == (3, 2, 2, 4)
    assert a["can_grade_from_transcripts"] and not a["can_reproduce_verdicts"] and not a["can_measure_repeatability"]
    assert b["can_reproduce_verdicts"] and b["can_measure_repeatability"] and b["max_repeats"] == 3
    summary = inventory.run(family, tmp_path / "out", skip=("left-",))
    assert summary["can_grade_from_transcripts_only"] == ["transcripts-only"]


def test_the_flat_transcript_layout_counts_toward_configurations_and_repeats(tmp_path):
    root = tmp_path / "flat"
    (root / "evals" / "t").mkdir(parents=True)
    (root / "evals" / "t" / "eval.json").write_text(json.dumps({"id": "t", "task": "p", "metadata": {"grader_type": "all_of"}}))
    for model in ("m1", "m2"):
        path = root / "trajectories" / "t" / f"{model}__pi__r1.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("[]")
    (root / "trajectories" / "manifest.json").write_text("{}")
    (root / "trajectories" / "t" / "notes__about__results.json").write_text("{}")
    row = inventory.inventory_row(root)
    assert (row["transcripts"], row["configurations"], row["max_repeats"], row["models"]) == (2, 2, 1, 2)
    assert row["harnesses"] == "pi 2" and row["grader_types_declared_in_metadata"] == "all_of"


def test_a_set_score_is_written_as_one_of_three_bands():
    """A score over a short list is a fraction with a small denominator, which would say how long the reference is."""
    assert regrade.score_band(None) is None and regrade.score_band(float("nan")) is None
    assert regrade.score_band(0.0) == regrade.score_band(0.4) == "at or above"
    assert regrade.score_band(-0.14) == "under 0.25 below"
    assert regrade.score_band(-0.25) == regrade.score_band(-1.0) == "0.25 or more below"


def test_the_family_figure_draws_from_the_committed_inventory(tmp_path):
    import shutil
    from pathlib import Path

    from sc_zprime import figures

    committed = Path(__file__).resolve().parents[1] / "results" / "family" / "inventory.csv"
    shutil.copy(committed, tmp_path / "inventory.csv")
    figures.draw_family(tmp_path)
    for suffix in ("png", "svg"):
        assert (tmp_path / "figures" / f"fig_family_inventory.{suffix}").stat().st_size > 10_000
    drawn = (tmp_path / "figures" / "fig_family_inventory.svg").read_text()
    assert "Date" not in drawn.split("</metadata>")[0] or "<dc:date>" not in drawn, "the figure must regenerate byte for byte"

