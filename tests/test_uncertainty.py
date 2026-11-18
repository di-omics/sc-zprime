import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from sc_zprime import uncertainty


def frame(rows):
    return pd.DataFrame(rows, columns=["config", "provider", "num", "den"])


def test_ratio_estimate_and_interval_bracket_the_truth():
    rng = np.random.default_rng(1)
    f = frame([(f"c{i}", "p" + str(i % 4), n, 3) for i, n in enumerate([3, 3, 0, 1, 2, 3, 0, 3, 1, 2, 3, 0])])
    row = uncertainty.ratio_row(f, "num", "den", rng, 4000)
    assert row["estimate"] == pytest.approx(21 / 36)
    assert row["ci_low"] < row["estimate"] < row["ci_high"]
    assert row["numerator"] == 21 and row["denominator"] == 36 and row["units"] == 12


def test_no_interval_when_every_unit_agrees_only_a_bound():
    """Resampling units that all agree gives one value every time. That is not an interval."""
    rng = np.random.default_rng(1)
    f = frame([(f"c{i}", "p", 3, 3) for i in range(8)])
    row = uncertainty.ratio_row(f, "num", "den", rng, 500)
    assert row["ci_low"] is None and row["ci_high"] is None
    assert row["interval_note"] == "all units agree"
    assert row["one_sided_bound"] == pytest.approx(0.025 ** (1 / 8))


def test_the_bound_is_an_upper_bound_when_nothing_passes():
    f = frame([(f"c{i}", "p", 0, 3) for i in range(8)])
    row = uncertainty.ratio_row(f, "num", "den", np.random.default_rng(1), 500)
    assert row["estimate"] == 0.0 and row["one_sided_bound"] == pytest.approx(1 - 0.025 ** (1 / 8))


def test_agreement_bound_is_the_exact_binomial_bound():
    # k successes in k trials: the one-sided 97.5% Clopper-Pearson lower bound solves p ** k = 0.025.
    for k in (1, 2, 7, 13):
        assert uncertainty.agreement_bound(k) ** k == pytest.approx(0.025)


def test_no_interval_from_fewer_than_three_units():
    f = frame([("a", "p", 1, 3), ("b", "q", 2, 3), ("c", "q", 0, 0)])
    row = uncertainty.ratio_row(f, "num", "den", np.random.default_rng(1), 500)
    assert row["estimate"] == 0.5 and row["ci_low"] is None
    assert row["interval_note"] == "fewer than 3 units" and row["one_sided_bound"] is None


def test_units_without_data_do_not_break_the_ratio():
    rng = np.random.default_rng(1)
    f = frame([("a", "p", 1, 2), ("b", "q", 0, 0), ("c", "q", 0, 0)])
    row = uncertainty.ratio_row(f, "num", "den", rng, 2000)
    assert row["estimate"] == 0.5 and row["units_with_data"] == 1
    assert row["share_of_resamples_defined"] < 1.0


def test_leave_one_provider_out_range():
    rng = np.random.default_rng(1)
    f = frame([("a", "p", 2, 2), ("b", "q", 0, 2)])
    row = uncertainty.ratio_row(f, "num", "den", rng, 200)
    assert (row["lopo_min"], row["lopo_max"]) == (0.0, 1.0)


def test_same_seed_gives_the_same_interval():
    f = frame([(f"c{i}", "p" + str(i % 3), n, 3) for i, n in enumerate([3, 1, 0, 2, 3, 1])])
    a = uncertainty.ratio_row(f, "num", "den", np.random.default_rng(5), 1000)
    b = uncertainty.ratio_row(f, "num", "den", np.random.default_rng(5), 1000)
    assert a == b


def test_configuration_level_counts():
    traced = pd.DataFrame({
        "task": ["t"] * 6, "tier": ["trap"] * 6, "provider": ["p", "p", "p", "q", "q", "q"],
        "config": ["a", "a", "a", "b", "b", "b"], "run_passed": [True, True, True, False, True, False],
    })
    row = uncertainty.configuration_level(traced).iloc[0]
    assert row["configurations"] == 2 and row["configurations_with_a_pass"] == 2
    assert row["configurations_passing_every_time"] == 1 and row["providers"] == 2


def traced_frame(rows):
    return pd.DataFrame(rows, columns=["config", "provider", "tier", "method", "value"])


def test_zprime_interval_is_withheld_when_a_control_has_few_configurations():
    rows = [("a", "p", "intended", "good", v) for v in (10.0, 10.5, 11.0)] + [("b", "q", "intended", "good", 10.2)]
    rows += [(c, "q", "trap", "bad", v) for c, v in zip("cdefg", (1.0, 2.0, 3.0, 2.5, 1.5))]
    row = uncertainty.zprime_row(traced_frame(rows), "bad", np.random.default_rng(1), 300)
    assert row["estimate"] is not None and row["ci_low"] is None and row["share_of_resamples_below_zero"] is None
    assert row["interval_note"] == "fewer than 3 units"
    assert (row["positive_control_units"], row["negative_control_units"]) == (2, 5)
    assert (row["positive_control_runs"], row["negative_control_runs"]) == (4, 5)


def test_zprime_interval_is_withheld_when_neither_control_has_spread():
    rows = [(c, "p", "intended", "good", 5.0) for c in "abcd"] + [(c, "q", "trap", "bad", 9.0) for c in "efgh"]
    row = uncertainty.zprime_row(traced_frame(rows), "bad", np.random.default_rng(1), 300)
    assert row["estimate"] == 1.0 and row["ci_low"] is None and row["interval_note"] == "no spread"


def test_zprime_interval_is_reported_with_enough_configurations():
    draw = np.random.default_rng(3)
    rows = [(f"g{i}", "p", "intended", "good", 10 + draw.normal()) for i in range(6) for _ in range(2)]
    rows += [(f"b{i}", "q", "trap", "bad", 2 + draw.normal()) for i in range(6) for _ in range(2)]
    row = uncertainty.zprime_row(traced_frame(rows), "bad", np.random.default_rng(1), 400)
    assert row["ci_low"] is not None and row["ci_low"] < row["ci_high"]
    assert row["positive_control_runs"] == 12 and row["share_of_resamples_defined"] > 0.9
    assert row["interval_note"] == ""


def test_percentile_interval_undercovers_with_this_few_clusters():
    """The documents say the nominal 95% interval covers the truth about 89% of the time
    for clusters sized like these. A smaller run of the same simulation must agree."""
    path = Path(__file__).resolve().parents[1] / "scripts" / "interval_coverage.py"
    spec = importlib.util.spec_from_file_location("interval_coverage", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    covered = module.coverage(0.3, np.random.default_rng(7), simulations=1500, resamples=600)
    assert 0.86 < covered < 0.925
