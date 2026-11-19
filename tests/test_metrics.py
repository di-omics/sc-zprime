import numpy as np
import pandas as pd
import pytest
from scipy import stats

from sc_zprime import metrics


def test_classic_zprime_matches_the_textbook_formula():
    pos, neg = np.array([100.0, 102, 98, 101, 99]), np.array([10.0, 12, 8, 11, 9])
    expected = 1 - 3 * (pos.std(ddof=1) + neg.std(ddof=1)) / abs(pos.mean() - neg.mean())
    assert metrics.classic_zprime(pos, neg) == pytest.approx(expected)
    assert metrics.classic_zprime(pos, neg) > 0.5


def test_zprime_is_one_for_two_distinct_point_clusters():
    assert metrics.classic_zprime([5, 5, 5], [9, 9, 9, 9]) == 1.0
    assert metrics.robust_zprime([5, 5, 5], [9, 9, 9, 9]) == 1.0


def test_zprime_is_negative_when_controls_overlap():
    assert metrics.classic_zprime([10, 11, 12, 13], [8, 11, 14, 17, 20]) < 0


def test_zprime_needs_three_values_in_each_control():
    assert metrics.classic_zprime([1, 2], [5, 6, 7]) is None
    assert metrics.robust_zprime([1, 2, 3], [5, 6]) is None


def test_zprime_is_minus_infinity_when_the_centres_coincide():
    """The worst case must not read as missing."""
    assert metrics.classic_zprime([3, 3, 3], [3, 3, 3]) == float("-inf")
    assert metrics.robust_zprime([10, 10, 10, 11], [10, 10, 10, 30]) is None  # tied majority: spread not estimable
    assert metrics.robust_zprime([9, 10, 11], [9, 10, 11]) == float("-inf")


def test_robust_zprime_refuses_a_tied_majority():
    """With more than half of a control tied, the MAD is zero whatever the
    rest did. The old behaviour returned exactly 1.0 for this input."""
    tied_but_scattered = [5, 5, 5, 5, 5, 5, 40, 41, 42]
    assert metrics.robust_zprime([1, 1, 1, 1], tied_but_scattered) is None
    assert metrics.classic_zprime([1, 1, 1, 1], tied_but_scattered) < 0.5


def traced_frame():
    return pd.DataFrame({
        "task": ["t"] * 8,
        "tier": ["intended", "intended", "intended", "trap", "trap", "trap", "trap", "partial"],
        "method": ["good"] * 3 + ["shortcut a"] * 3 + ["shortcut b", "half"],
        "config": ["c1", "c2", "c3", "c1", "c2", "c3", "c4", "c4"],
        "provider": ["p", "p", "q", "p", "p", "q", "q", "q"],
        "value": [10.0, 10.0, 11.0, 6.0, 6.0, 6.0, 20.0, 12.0],
        "margin": [0.0, 0.0, 0.2, -0.8, -0.8, -0.8, 2.0, 0.4],
        "band_lower": [5.0] * 8, "band_upper": [5.0] * 8,
        "run_passed": [True, True, True, True, True, False, False, False],
    })


def test_method_separation_reports_the_window_as_a_test_of_method():
    row = metrics.method_separation(traced_frame()).iloc[0]
    assert row["window_sensitivity"] == 1.0
    assert row["window_specificity"] == 0.5
    assert row["trap_pass"] == 2 and row["trap_runs"] == 4
    assert row["passes_from_trap_methods"] == 2 and row["passes"] == 5
    assert row["intended_span_in_tolerance_widths"] == 0.2
    assert row["trap_runs_inside_intended_span"] == 0
    assert row["nearest_trap_gap_in_tolerance_widths"] == 0.8


def test_each_trap_method_is_its_own_negative_control():
    table = metrics.separation_by_trap(traced_frame()).set_index("trap_method")
    assert list(table.index) == ["shortcut a", "shortcut b"]
    assert table.loc["shortcut a", "runs_passed"] == 2 and table.loc["shortcut a", "configurations_with_a_pass"] == 2
    assert table.loc["shortcut a", "zprime_against_intended"] == pytest.approx(1 - 3 * np.std([10, 10, 11], ddof=1) / abs(31 / 3 - 6), abs=0.01)
    assert pd.isna(table.loc["shortcut b", "zprime_against_intended"])
    assert "at least 3" in table.loc["shortcut b", "zprime_note"]


def test_method_separation_survives_a_field_without_a_margin():
    frame = traced_frame().assign(margin=None, band_lower=None, band_upper=None)
    row = metrics.method_separation(frame).iloc[0]
    assert row["window_specificity"] == 0.5 and row["nearest_trap_gap_in_tolerance_widths"] is None
    assert len(metrics.separation_by_trap(frame)) == 2


def test_implied_split_share_is_exact_for_three_repeats():
    """Simulate a benchmark, publish only accuracy and its interval, and check
    that the split share recovered from those two numbers is the real one."""
    rng = np.random.default_rng(7)
    n_tasks, repeats = 195, 3
    for _ in range(50):
        p = rng.beta(0.35, 0.35, n_tasks)
        outcomes = rng.random((n_tasks, repeats)) < p[:, None]
        means = outcomes.mean(axis=1)
        passes = outcomes.sum(axis=1)
        truth = float(((passes > 0) & (passes < repeats)).mean())
        half = stats.t.ppf(0.975, n_tasks - 1) * means.std(ddof=1) / np.sqrt(n_tasks)
        est = metrics.implied_split_share(100 * means.mean(), 100 * (means.mean() - half), 100 * (means.mean() + half), n_tasks)
        assert est == pytest.approx(truth, abs=1e-9)


def test_implied_split_share_survives_two_decimal_rounding():
    rng = np.random.default_rng(11)
    worst = 0.0
    for _ in range(200):
        outcomes = rng.random((195, 3)) < rng.beta(0.35, 0.35, 195)[:, None]
        means, passes = outcomes.mean(axis=1), outcomes.sum(axis=1)
        truth = float(((passes > 0) & (passes < 3)).mean())
        half = stats.t.ppf(0.975, 194) * means.std(ddof=1) / np.sqrt(195)
        acc, lo, hi = (round(100 * v, 2) for v in (means.mean(), means.mean() - half, means.mean() + half))
        worst = max(worst, abs(metrics.implied_split_share(acc, lo, hi, 195) - truth))
    assert worst < 0.01


def test_implied_split_share_is_zero_for_perfectly_repeatable_tasks():
    means = np.array([1.0] * 100 + [0.0] * 95)
    half = stats.t.ppf(0.975, 194) * means.std(ddof=1) / np.sqrt(195)
    m = means.mean()
    assert metrics.implied_split_share(100 * m, 100 * (m - half), 100 * (m + half), 195) == pytest.approx(0.0, abs=0.02)


def test_implied_split_share_rejects_impossible_inputs():
    """An interval far too narrow for the accuracy means the three-repeat
    assumption is wrong for that row; the result must not be reported."""
    assert metrics.implied_split_share(50.0, 49.9, 50.1, 195) is None


def test_leaderboard_without_intervals_returns_no_summary():
    table = pd.DataFrame({"model_name": ["a", "b"], "harness": ["h", "h"], "Accuracy (%)": [50.0, 40.0],
                          "ci_lower": [None, None], "ci_upper": [None, None], "N": [10, 10]})
    rows, summary = metrics.leaderboard(table)
    assert summary is None and len(rows) == 2


def test_leaderboard_counts_others_not_the_leader():
    table = pd.DataFrame({"model_name": ["a", "b", "c"], "harness": ["h"] * 3, "Accuracy (%)": [60.0, 55.0, 30.0],
                          "ci_lower": [54.0, 49.0, 24.0], "ci_upper": [66.0, 61.0, 36.0], "N": [195] * 3})
    _, summary = metrics.leaderboard(table)
    assert summary["others_overlapping_the_leader"] == 1 and summary["others"] == 2


def test_leaderboard_tells_apart_by_a_test_of_the_difference_not_by_overlap():
    """b's interval overlaps the leader's, yet the two differ by more than 1.96 combined standard errors."""
    table = pd.DataFrame({"model_name": ["a", "b", "c"], "harness": ["h"] * 3, "Accuracy (%)": [60.0, 50.0, 58.0],
                          "ci_lower": [54.0, 44.0, 52.0], "ci_upper": [66.0, 56.0, 64.0], "N": [195] * 3})
    rows, summary = metrics.leaderboard(table)
    assert summary["others_overlapping_the_leader"] == 2
    assert summary["others_not_told_apart_from_the_leader"] == 1
    assert (summary["pairs"], summary["pairs_overlapping"], summary["pairs_not_told_apart"]) == (3, 3, 2)
    told = dict(zip(rows["config"], rows["told_apart_from_leader"]))
    assert told["a / h"] is None and told["b / h"] is True and told["c / h"] is False


def test_a_window_percentage_never_gives_away_a_reference_of_zero():
    """A blank or infinite width would say the reference is exactly zero. Wide windows all read the same."""
    from sc_zprime import metrics

    assert metrics._window_pct(5, 0) == ">200" == metrics._window_pct(5, 2)
    assert metrics._window_pct(5, 10) == 50.0
    assert metrics._window_pct(0, 0) == 0.0 == metrics._window_pct(0, 7)


def test_a_window_percentage_is_withheld_where_margins_fall_on_a_grid():
    """Whole-number reference and a small whole-number tolerance: the grid gives the tolerance, so the width must not."""
    from sc_zprime import metrics

    assert metrics._on_a_grid(12, 3, 3) and metrics._on_a_grid(0, 2, 2) and metrics._on_a_grid(40.0, 99, 5)
    assert not metrics._on_a_grid(12, 100, 100), "at two decimals a tolerance of 100 or more cannot be read off the grid"
    assert not metrics._on_a_grid(12.5, 3, 3) and not metrics._on_a_grid(12, 2.5, 2.5)
    assert not metrics._on_a_grid(12, 0, 0), "an exact-match field has no width to withhold"
