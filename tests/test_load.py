"""Loader behaviour on small synthetic checkouts built in a temp directory."""

import json

import pytest

from sc_zprime import load, metrics, report


def make(root, tasks, runs, task_dir="evals"):
    """tasks: {task: grader}; runs: [(task, config, rep, answer, published_pass)]."""
    for task, grader in tasks.items():
        path = root / task_dir / "cat" / f"{task}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"id": task, "grader": grader, "metadata": {"task": "cat", "kit": "kit"}}))
    for task, config, rep, answer, published in runs:
        d = root / "trajectories" / task / "prov" / config / "harness" / rep
        d.mkdir(parents=True, exist_ok=True)
        (d / "result.json").write_text(json.dumps({"result": {"agent_answer": answer, "passed": published,
                                                              "grader_result": {"metrics": {}}}}))
        (d / "trajectory.json").write_text("[]")
    return root


NUMERIC = {"type": "numeric_tolerance", "config": {"ground_truth": {"x": 10}, "tolerances": {"x": {"type": "absolute", "value": 2}}}}


def test_a_path_that_is_not_a_checkout_is_named_in_the_error(tmp_path):
    with pytest.raises(load.NoBenchmarkFound, match="not a benchmark checkout"):
        load.load_latch_layout(tmp_path)


def test_unsupported_grader_types_are_skipped_and_reported(tmp_path):
    root = make(tmp_path, {"a": NUMERIC, "b": {"type": "multiple_choice", "config": {}}},
                [("a", "m1", "r1", {"x": 11}, True), ("b", "m1", "r1", {"y": "A"}, True)])
    bench = load.load_latch_layout(root)
    assert list(bench.runs["task"]) == ["a"]
    assert any(s["task"] == "b" and "multiple_choice" in s["reason"] for s in bench.skipped)
    assert any("1 run(s)" in s["reason"] for s in bench.skipped)


def test_report_runs_on_a_benchmark_with_no_method_spec_and_a_skipped_task(tmp_path):
    root = make(tmp_path / "bench", {"a": NUMERIC, "b": {"type": "rubric", "config": {}}},
                [("a", "m1", f"r{k}", {"x": v}, v <= 12) for k, v in ((1, 11), (2, 13), (3, 11))]
                + [("a", "m2", f"r{k}", {"x": 30}, False) for k in (1, 2, 3)])
    summary = report.run(root, tmp_path / "out")
    assert summary["reproduce"]["runs_agree"] == 6
    assert summary["method_tracing"] is None and summary["leaderboard"] is None
    assert summary["skipped"] and (tmp_path / "out" / "validation_cards" / "a.md").exists()


def test_incomplete_cells_are_left_out_of_repeatability(tmp_path):
    root = make(tmp_path, {"a": NUMERIC},
                [("a", "m1", "r1", {"x": 11}, True), ("a", "m1", "r2", {"x": 30}, False), ("a", "m1", "r3", {"x": 11}, True),
                 ("a", "m2", "r1", {"x": 11}, True), ("a", "m3", "r1", {"x": 11}, True), ("a", "m3", "r2", {"x": 11}, True),
                 ("a", "m3", "r3", {"x": 11}, True)])
    summary = metrics.repeatability_summary(metrics.repeatability(load.load_latch_layout(root)))
    row = summary[summary["task"] == "ALL"].iloc[0]
    assert (row["cells"], row["incomplete_cells"], row["split"], row["all_pass"]) == (2, 1, 1, 1)


def test_a_broken_grader_config_fails_closed_and_is_counted(tmp_path):
    broken = {"type": "numeric_tolerance", "config": {"ground_truth": {"x": 10}, "tolerances": {"x": []}}}
    root = make(tmp_path, {"a": NUMERIC, "c": broken},
                [("a", "m1", "r1", {"x": 11}, True), ("c", "m1", "r1", {"x": 10}, False)])
    bench = load.load_latch_layout(root)
    row = bench.runs[bench.runs["task"] == "c"].iloc[0]
    assert not row["regraded_pass"] and row["config_error"]


def test_task_files_under_example_evals_are_read_the_same_way(tmp_path):
    """SpatialBench keeps its task files in example_evals/ rather than evals/."""
    runs = [("a", "m1", "r1", {"x": 11}, True), ("a", "m1", "r2", {"x": 30}, False)]
    one = load.load_latch_layout(make(tmp_path / "one", {"a": NUMERIC}, runs))
    two = load.load_latch_layout(make(tmp_path / "two", {"a": NUMERIC}, runs, task_dir="example_evals"))
    assert list(two.runs["regraded_pass"]) == list(one.runs["regraded_pass"]) == [True, False]
    from sc_zprime import provenance
    assert provenance.input_fingerprint(tmp_path / "two")["files"] == provenance.input_fingerprint(tmp_path / "one")["files"] == 5
