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
