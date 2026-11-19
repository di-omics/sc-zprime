"""Checks against a real benchmark checkout. Skipped when none is present.

Point SC_ZPRIME_UPSTREAM at a directory holding the upstream checkouts, or
put them in ../upstream next to this repository (see scripts/fetch_upstream.sh).
"""

import os
from pathlib import Path

import pytest

from sc_zprime import load, metrics, tracing

ROOT = Path(os.environ.get("SC_ZPRIME_UPSTREAM", Path(__file__).resolve().parents[2] / "upstream"))
SCBENCH = ROOT / "scbench"
pytestmark = pytest.mark.skipif(not (SCBENCH / "trajectories").exists(), reason="no upstream checkout")


@pytest.fixture(scope="module")
def bench():
    return load.load_latch_layout(SCBENCH, "scbench")


def test_every_published_verdict_is_reproduced(bench):
    r = metrics.reproduce(bench)
    assert r["runs"] > 0
    assert r["runs_agree"] == r["runs"]
    assert r["fields_agree"] == r["fields"]


def test_tightening_only_removes_passes_and_widening_only_adds_them(bench):
    sweep = metrics.tolerance_sweep(bench, scales=(0.8, 1.0, 1.25))
    wide = sweep.pivot(index="run_id", columns="scale", values="passed")
    assert not (wide[0.8] & ~wide[1.0]).any()
    assert not (wide[1.0] & ~wide[1.25]).any()


def test_every_traced_run_gets_a_method(bench):
    traced = tracing.trace(bench)
    assert len(traced) > 0
    assert not traced["method"].isin(["unresolved", "ambiguous"]).any()


def test_split_share_identity_holds_on_real_runs(bench):
    """On the public runs the split share is known, so the identity used for
    the leaderboard can be checked directly, configuration by configuration."""
    import numpy as np
    from scipy import stats

    cells = metrics.repeatability(bench)
    for config, g in cells[cells["repeats"] == 3].groupby("config"):
        means = (g["passes"] / 3).to_numpy()
        if len(means) < 3 or means.std(ddof=1) == 0:
            continue
        half = stats.t.ppf(0.975, len(means) - 1) * means.std(ddof=1) / np.sqrt(len(means))
        est = metrics.implied_split_share(100 * means.mean(), 100 * (means.mean() - half), 100 * (means.mean() + half), len(means))
        assert est == pytest.approx(float(g["split"].mean()), abs=1e-9), config


def test_tracer_agrees_with_the_blind_rerating(bench):
    """Every traced label, and every ran-intended-elsewhere flag, must match
    the independently adjudicated table in validation/."""
    import pandas as pd

    from sc_zprime.methods.scbench import FAMILY

    repo = Path(__file__).resolve().parents[1]
    truth = pd.read_csv(repo / "validation" / "blind_rerating.csv", dtype=str).set_index("run_id")
    traced = tracing.trace(bench).set_index("run_id")
    assert set(traced.index) == set(truth.index)
    family = traced["method"].map(FAMILY)
    assert family.notna().all()
    wrong = family[family != truth.loc[family.index, "adjudicated_method"]]
    assert wrong.empty, wrong.to_dict()
    flag = traced["ran_intended_method_elsewhere"].map({True: "1", False: "0"})
    wrong = flag[flag != truth.loc[flag.index, "adjudicated_ran_intended_elsewhere"]]
    assert wrong.empty, wrong.to_dict()


def test_published_accuracies_are_whole_numbers_of_passes():
    """Support for the split-share inference. With three pass or fail runs on
    every task, accuracy x tasks x 3 is a whole number, up to the two-decimal
    rounding of the published table."""
    import pandas as pd

    table = pd.read_csv(SCBENCH / "results" / "model_results.csv")
    passes = table["Accuracy (%)"] / 100 * table["N"] * 3
    slack = 0.005 / 100 * table["N"] * 3
    assert ((passes - passes.round()).abs() <= slack + 1e-9).all()


SPATIALBENCH = ROOT / "spatialbench"
needs_spatial = pytest.mark.skipif(not (SPATIALBENCH / "trajectories").exists(), reason="no SpatialBench checkout")


@pytest.fixture(scope="module")
def spatial():
    return load.load_latch_layout(SPATIALBENCH, "spatialbench")


@needs_spatial
def test_every_published_spatialbench_verdict_is_reproduced(spatial):
    r = metrics.reproduce(spatial)
    assert r["runs"] > 0 and not spatial.skipped
    assert r["runs_agree"] == r["runs"]
    assert r["fields_agree"] == r["fields"]


@needs_spatial
def test_every_batch_task_run_gets_a_method(spatial):
    traced = tracing.trace(spatial)
    assert traced["task"].nunique() == 3
    assert not traced["method"].isin(["unresolved", "ambiguous"]).any()


@needs_spatial
def test_answer_recovery_matches_the_committed_measurement():
    """Recovery from transcripts, measured on every run whose answer file is published."""
    import importlib.util

    import pandas as pd

    if not (ROOT / "spatialbench-long" / "trajectories").exists():
        pytest.skip("no SpatialBench-Long checkout")
    repo = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location("answer_recovery_check", repo / "scripts" / "answer_recovery_check.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    fresh = pd.DataFrame(module.measure(ROOT)).astype(str)
    committed = pd.read_csv(repo / "validation" / "answer_recovery.csv", keep_default_na=False).astype(str)
    assert fresh.to_dict("records") == committed.to_dict("records")
    numbers = pd.read_csv(repo / "validation" / "answer_recovery.csv")
    total = numbers[["runs", "answers_recovered", "equal_to_the_published_answer"]].sum()
    assert total["equal_to_the_published_answer"] >= 0.98 * total["answers_recovered"]
    assert total["answers_recovered"] >= 0.9 * total["runs"]
    assert int(numbers.loc[numbers["harness"] == "pi", "runs"].sum()) > 0, "the pi harness must be in the test set"


needs_family = pytest.mark.skipif(not (ROOT / "variantbench" / "trajectories").exists()
                                  or not (ROOT / "txbench-pp" / "trajectories").exists(),
                                  reason="no VariantBench or TxBench-PP checkout")


@needs_family
@pytest.mark.parametrize("name", ["variantbench", "txbench-pp"])
def test_transcript_only_benchmarks_are_graded_without_a_configuration_error(name):
    from sc_zprime import regrade

    tasks, runs, fields = regrade.regrade(ROOT / name, name)
    assert not runs["verdict_published"].any(), "these checkouts publish no verdicts; if that changes, use `run`"
    assert runs["gradable"].all() and tasks["gradable"].all()
    graded = runs[runs["graded"]]
    assert len(graded) >= 0.9 * len(runs)
    assert set(fields["reason"].fillna("")) <= {"", "missing", "wrong_type", "count", "value"}
    assert (graded["n_fields"] > 0).all()


def test_every_pinned_commit_is_the_one_checked_out_and_dated_as_the_pages_say():
    """docs/FAMILY.md: 15 benchmark repositories read at pinned commits dated November 2026.
    docs/SPATIALBENCH.md: the evaluation tool at commit 0d79831, dated 30 September 2026."""
    import re
    import subprocess

    script = (Path(__file__).resolve().parents[1] / "scripts" / "fetch_upstream.sh").read_text()
    pins = dict(re.findall(r"^fetch (\S+) ([0-9a-f]{40})$", script, re.M))
    tool = pins.pop("latch-eval-tools")
    assert len(pins) == 15 and tool.startswith("0d79831")
    if not all((ROOT / name / ".git").exists() for name in list(pins) + ["latch-eval-tools"]):
        pytest.skip("not every pinned checkout is a git clone")

    def head(name):
        return subprocess.run(["git", "-C", str(ROOT / name), "-c", "core.hooksPath=/dev/null", "log", "-1", "--format=%H %cs"],
                              capture_output=True, text=True, check=True).stdout.split()

    for name, commit in pins.items():
        shown = head(name)
        assert shown[0] == commit and shown[1].startswith("2026-11"), (name, shown)
    assert head("latch-eval-tools") == [tool, "2026-09-30"]
    # docs/RUNNING_THE_BENCHMARK.md names the version of the tool at that commit.
    version = re.search(r'^version\s*=\s*"([^"]+)"', (ROOT / "latch-eval-tools" / "pyproject.toml").read_text(), re.M).group(1)
    running = " ".join((Path(__file__).resolve().parents[1] / "docs" / "RUNNING_THE_BENCHMARK.md").read_text().split())
    assert f"The commit read here (`{tool[:7]}`, version {version}, 30 September 2026)" in running


def test_what_the_family_page_says_the_repositories_say_about_themselves():
    """4 READMEs say their public tasks are not part of the benchmark, and the task files of 2 repositories say
    the full evaluation set is available to qualified partners (docs/FAMILY.md, section 1)."""
    import json
    import re

    kept_out = {
        "oncologybench": "not in the benchmark",
        "rarediseasebench": "removed from the benchmark",
        "tissuemicroscopybench": "not selected for the benchmark",
        "txBench-antibody-development": "DO NOT APPEAR in the benchmark",
    }
    readme = {name: (ROOT / name / "README.md") for name in kept_out}
    if not all(path.exists() for path in readme.values()):
        pytest.skip("no checkout of those repositories")
    for name, phrase in kept_out.items():
        assert phrase in readme[name].read_text(), name
    # No other README uses one of these phrases. VariantBench says something similar, in other words, of 2 of
    # its 8 (section 3).
    says_so = re.compile("|".join(re.escape(phrase) for phrase in kept_out.values()), re.I)
    others = set()
    for repo in sorted(p for p in ROOT.iterdir() if p.is_dir() and not p.name.startswith("biosecbench-")):
        text = (repo / "README.md").read_text(errors="replace") if (repo / "README.md").exists() else ""
        if repo.name not in kept_out and says_so.search(text):
            others.add(repo.name)
    assert others == set(), others
    family = " ".join((Path(__file__).resolve().parents[1] / "docs" / "FAMILY.md").read_text().split())
    assert (f"and {len(kept_out)} ({', '.join(kept_out)}) say in their READMEs that their public tasks are not part "
            "of the benchmark but are built like its tasks.") in family
    partners = set()
    for repo in sorted(p for p in ROOT.iterdir() if p.is_dir() and not p.name.startswith("biosecbench-")):
        for path in repo.rglob("*.json"):
            if "trajectories" in path.parts or ".git" in path.parts:
                continue
            match = re.search(r'"data_availability"\s*:\s*("(?:[^"\\\\]|\\\\.)*"|\{.*?\})', path.read_text(errors="replace"), re.S)
            if match and re.search(r"qualified partners", match.group(1)):
                partners.add(repo.name)
    assert partners == {"txbench-antibody-discovery", "txbench-oligo-discovery"}, partners
