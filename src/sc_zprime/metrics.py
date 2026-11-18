"""Validation metrics for a benchmark, read as an assay.

Every function takes the tidy tables from `load.py` and returns a DataFrame or
a plain dict. Nothing here writes files.

Vocabulary, borrowed from assay development:

margin       signed distance of an answer from the reference, in units of the
             tolerance width. 0 is the reference, +/-1 the edges of the pass
             window.
dead readout a graded field that at least 95% of runs pass. It rarely or never
             decides a verdict; the count of verdicts it did decide is reported.
edge-decided a verdict that flips if the tolerance is made 20% tighter or 25%
             wider.
split        a (task, configuration) cell whose repeats do not all agree.
Z-prime      the screening-assay separation statistic, computed between runs
             that used the intended method (positive control) and runs that
             used one named trap method (negative control).
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from . import graders

SWEEP_SCALES = (0.5, 0.75, 0.8, 0.9, 1.0, 1.1, 1.25, 1.5, 2.0)
EDGE_INNER = 0.8
EDGE_OUTER = 1.25
DEAD_THRESHOLD = 0.95
MIN_CLUSTER = 3


def reproduce(bench) -> dict:
    """How often the independent grader agrees with the published verdicts."""
    runs, fields = bench.runs, bench.fields
    known = fields[fields["published_passed"].notna()]
    return {
        "runs": int(len(runs)),
        "runs_agree": int((runs["published_pass"] == runs["regraded_pass"]).sum()),
        "fields": int(len(known)),
        "fields_agree": int((known["passed"] == known["published_passed"].astype(bool)).sum()),
        "tasks": int(runs["task"].nunique()),
        "configurations": int(runs["config"].nunique()),
        "grader_versions": sorted(str(v) for v in runs["grader_version"].dropna().unique()),
    }


def readouts(bench) -> pd.DataFrame:
    """One row per graded field: how wide the window is and what it decides."""
    fields, runs = bench.fields, bench.runs
    failed_fields = fields[~fields["passed"]].groupby("run_id")["field"].agg(list)
    rows = []
    for (task, name), g in fields.groupby(["task", "field"], sort=False):
        ref = g["reference"].iloc[0]
        lower, upper = g["band_lower"].iloc[0], g["band_upper"].iloc[0]
        task_runs = runs[runs["task"] == task]
        failing = task_runs[~task_runs["regraded_pass"]]["run_id"]
        failed_here = [name in failed_fields.get(r, []) for r in failing]
        sole = [failed_fields.get(r, []) == [name] for r in failing]
        counts = g["value"].round(6).value_counts(dropna=True)
        has_width = lower is not None and upper is not None and not pd.isna(lower) and not pd.isna(upper)
        rows.append({
            "task": task,
            "field": name,
            "kind": g["kind"].iloc[0],
            "window_lower_pct_of_reference": round(100 * lower / abs(ref)) if has_width and ref != 0 else None,
            "window_upper_pct_of_reference": round(100 * upper / abs(ref)) if has_width and ref != 0 else None,
            "lower_edge_at_zero": bool(g["lower_pinned_at_zero"].iloc[0]),
            "runs": int(len(g)),
            "pass_rate": round(float(g["passed"].mean()), 3),
            "distinct_answers": int(len(counts)),
            "largest_cluster_share": round(float(counts.iloc[0] / len(g)), 3) if len(counts) else None,
            "dead": bool(g["passed"].mean() >= DEAD_THRESHOLD),
            "task_failures": int(len(failing)),
            "failures_involving_field": int(sum(failed_here)),
            "failures_from_field_alone": int(sum(sole)),
        })
    return pd.DataFrame(rows)


def margin_bins(bench) -> pd.DataFrame:
    """Where answers land relative to the pass window, per numeric field."""
    f = bench.fields[bench.fields["margin"].notna()].copy()
    a = f["margin"].abs()
    f["zone"] = np.select(
        [a <= EDGE_INNER, a <= 1.0, a <= EDGE_OUTER],
        ["pass, clear of the edge", "pass, near the edge", "fail, near the edge"],
        default="fail, clear of the edge",
    )
    out = f.groupby(["task", "field", "zone"]).size().unstack(fill_value=0)
    for zone in ["pass, clear of the edge", "pass, near the edge", "fail, near the edge", "fail, clear of the edge"]:
        if zone not in out:
            out[zone] = 0
    return out.reset_index()


def tolerance_sweep(bench, scales=SWEEP_SCALES) -> pd.DataFrame:
    """Regrade every run with each tolerance width multiplied by a scale.

    A window floor that sits at zero for a positive reference is a natural
    limit, not a tolerance, and is not moved (see `graders.within`).
    """
    rows = []
    base = {r.run_id: r.regraded_pass for r in bench.runs.itertuples()}
    answers = bench.answers
    for scale in scales:
        for r in bench.runs.itertuples():
            result = graders.grade(answers[r.run_id], bench.graders[r.task], scale)
            rows.append({"task": r.task, "config": r.config, "run_id": r.run_id, "scale": scale,
                         "passed": result.passed, "flipped": result.passed != base[r.run_id]})
    return pd.DataFrame(rows)


def sweep_summary(sweep: pd.DataFrame) -> pd.DataFrame:
    per_task = sweep.groupby(["task", "scale"]).agg(runs=("passed", "size"), pass_rate=("passed", "mean"), flips=("flipped", "sum")).reset_index()
    overall = sweep.groupby("scale").agg(runs=("passed", "size"), pass_rate=("passed", "mean"), flips=("flipped", "sum")).reset_index()
    overall.insert(0, "task", "ALL")
    out = pd.concat([per_task, overall], ignore_index=True)
    out["pass_rate"] = out["pass_rate"].round(3)
    return out


def edge_decided(sweep: pd.DataFrame) -> pd.DataFrame:
    """Runs whose verdict flips at 0.8x or 1.25x tolerance."""
    near = sweep[sweep["scale"].isin([EDGE_INNER, EDGE_OUTER])]
    flagged = near.groupby(["task", "run_id"])["flipped"].any().reset_index()
    out = flagged.groupby("task").agg(runs=("flipped", "size"), edge_decided=("flipped", "sum")).reset_index()
    total = pd.DataFrame([{"task": "ALL", "runs": out["runs"].sum(), "edge_decided": out["edge_decided"].sum()}])
    out = pd.concat([out, total], ignore_index=True)
    out["share"] = (out["edge_decided"] / out["runs"]).round(3)
    return out


def clusters(bench, min_size: int = MIN_CLUSTER) -> pd.DataFrame:
    """Groups of runs that submitted the identical value for a field.

    Identical answers from different models are deterministic pipelines
    landing on the same number, so each cluster is one analysis recipe. The
    table reports each cluster's margin, never its value.
    """
    f = bench.fields[bench.fields["margin"].notna()].copy()
    f["key"] = f["value"].round(6)
    rows = []
    for (task, name), g in f.groupby(["task", "field"], sort=False):
        n = len(g)
        for _, c in g.groupby("key"):
            if len(c) < min_size:
                continue
            m = float(c["margin"].iloc[0])
            if not math.isfinite(m):
                continue
            rows.append({
                "task": task, "field": name, "field_is_dead": bool(g["passed"].mean() >= DEAD_THRESHOLD),
                "runs": int(len(c)), "share_of_runs": round(len(c) / n, 3),
                "configurations": int(c["config"].nunique()), "providers": int(c["provider"].nunique()),
                "margin": round(m, 2), "field_passed": bool(c["passed"].iloc[0]),
                "near_edge": bool(EDGE_INNER < abs(m) <= EDGE_OUTER),
            })
    out = pd.DataFrame(rows)
    if len(out):
        out = out.sort_values(["task", "field", "runs"], ascending=[True, True, False]).reset_index(drop=True)
    return out


def repeatability(bench, expected_repeats: int | None = None) -> pd.DataFrame:
    """Agreement between repeats of the same configuration on the same task.

    Answers are compared after rounding to six decimals, so the same result
    printed with different float noise counts as identical. A cell with fewer
    repeats than expected is marked incomplete and left out of the summary.
    """
    answers = bench.fields.groupby("run_id").apply(
        lambda g: tuple(sorted((r.field, None if pd.isna(r.value) else round(r.value, 6)) for r in g.itertuples())),
        include_groups=False,
    )
    runs = bench.runs.assign(answer=bench.runs["run_id"].map(answers))
    cells = runs.groupby(["task", "config"]).agg(
        repeats=("regraded_pass", "size"), passes=("regraded_pass", "sum"),
        distinct_answers=("answer", "nunique"),
    ).reset_index()
    if expected_repeats is None:
        expected_repeats = int(cells["repeats"].mode().iloc[0])
    cells["complete"] = cells["repeats"] == expected_repeats
    cells["split"] = cells["complete"] & (cells["passes"] > 0) & (cells["passes"] < cells["repeats"])
    cells["identical_answers"] = cells["complete"] & (cells["distinct_answers"] == 1)
    return cells


def repeatability_summary(cells: pd.DataFrame) -> pd.DataFrame:
    def agg(g):
        full = g[g["complete"]]
        n = len(full)
        return pd.Series({
            "cells": n, "incomplete_cells": int((~g["complete"]).sum()),
            "all_pass": int((full["passes"] == full["repeats"]).sum()),
            "all_fail": int((full["passes"] == 0).sum()), "split": int(full["split"].sum()),
            "split_share": round(float(full["split"].mean()), 3) if n else None,
            "identical_answer_share": round(float(full["identical_answers"].mean()), 3) if n else None,
        })
    per_task = cells.groupby("task").apply(agg, include_groups=False).reset_index()
    overall = agg(cells).to_frame().T
    overall.insert(0, "task", "ALL")
    return pd.concat([per_task, overall], ignore_index=True)


def credit(bench) -> pd.DataFrame:
    """Strict pass rate against partial credit, with and without dead fields."""
    ro = readouts(bench)
    dead = set(zip(ro[ro["dead"]]["task"], ro[ro["dead"]]["field"]))
    f = bench.fields.assign(dead=[(t, n) in dead for t, n in zip(bench.fields["task"], bench.fields["field"])])
    rows = []
    for task, g in f.groupby("task", sort=False):
        per_run = g.groupby("run_id")["passed"].mean()
        live = g[~g["dead"]]
        live_run = live.groupby("run_id")["passed"].mean() if len(live) else pd.Series(dtype=float)
        strict = bench.runs[bench.runs["task"] == task]["regraded_pass"].mean()
        rows.append({
            "task": task, "fields": int(g["field"].nunique()), "dead_fields": int(g[g["dead"]]["field"].nunique()),
            "strict_pass_rate": round(float(strict), 3), "partial_credit": round(float(per_run.mean()), 3),
            "partial_credit_live_fields_only": round(float(live_run.mean()), 3) if len(live_run) else None,
        })
    return pd.DataFrame(rows)


MIN_CONTROL = 3


def classic_zprime(pos, neg) -> float | None:
    """Z-prime as defined for screening assays (Zhang, Chung, Oldenburg 1999):

        Z' = 1 - 3 (sd_pos + sd_neg) / |mean_pos - mean_neg|

    By convention 1 is ideal, 0.5 or above is an excellent assay, 0 to 0.5 is
    marginal, and below 0 the 3-sd bands of the two controls overlap.

    The statistic was built for roughly normal scatter around two means and a
    one-sided hit threshold. Benchmark answers are often neither: runs that
    use one recipe submit one identical value, and a pass window has two
    edges. So treat it as a rough summary. A method whose answers fall in
    several clusters on both sides of the other control gets a large SD and a
    negative Z-prime even when no answer of one group lies among the answers
    of the other, and two controls with no spread score exactly 1 however
    close together they sit. Read it next to the margins, never alone.

    Returns None with fewer than three values in either control, and -inf
    when the two means coincide.
    """
    pos, neg = np.asarray(pos, float), np.asarray(neg, float)
    if len(pos) < MIN_CONTROL or len(neg) < MIN_CONTROL:
        return None
    gap = abs(pos.mean() - neg.mean())
    if gap == 0:
        return float("-inf")
    return float(1 - 3 * (pos.std(ddof=1) + neg.std(ddof=1)) / gap)


def robust_zprime(pos, neg) -> float | None:
    """Z-prime from medians and scaled MADs.

    Kept for the sensitivity table only. When more than half of a control
    submits the identical value its MAD is zero whatever the rest did, so the
    statistic is not estimable and None is returned unless the control really
    is constant.
    """
    pos, neg = np.asarray(pos, float), np.asarray(neg, float)
    if len(pos) < MIN_CONTROL or len(neg) < MIN_CONTROL:
        return None

    def spread(v):
        s = 1.4826 * np.median(np.abs(v - np.median(v)))
        return None if s == 0 and len(np.unique(v)) > 1 else s

    s_pos, s_neg = spread(pos), spread(neg)
    if s_pos is None or s_neg is None:
        return None
    gap = abs(np.median(pos) - np.median(neg))
    if gap == 0:
        return float("-inf")
    return float(1 - 3 * (s_pos + s_neg) / gap)


def _width(frame: pd.DataFrame) -> float | None:
    """Mean of the two tolerance widths of the traced field, in answer units."""
    if "band_lower" not in frame or frame["band_lower"].isna().all():
        return None
    return float((frame["band_lower"].iloc[0] + frame["band_upper"].iloc[0]) / 2)


def method_separation(traced: pd.DataFrame) -> pd.DataFrame:
    """Per task: does the pass window tell an intended method from a trap?

    The pass window is treated as a test of method. Sensitivity is the share
    of intended-method runs that pass and specificity is the share of
    trap-method runs that fail, both at the level of the whole run (every
    graded field), since that is what the benchmark scores.

    The span and gap describe the traced readout alone: how wide a band the
    intended answers occupy, whether any trap answer falls inside it, and how
    close the nearest one comes, in tolerance widths.
    """
    rows = []
    for task, g in traced.groupby("task", sort=False):
        pos, neg, part = g[g["tier"] == "intended"], g[g["tier"] == "trap"], g[g["tier"] == "partial"]
        passes = g[g["run_passed"]]
        width = _width(g)
        span = inside = gap = None
        pv, nv = pos["value"].dropna(), neg["value"].dropna()
        if len(pv) and width:
            lo, hi = pv.min(), pv.max()
            span = round(float((hi - lo) / width), 2)
            if len(nv):
                inside = int(((nv >= lo) & (nv <= hi)).sum())
                dist = nv.apply(lambda v: 0.0 if lo <= v <= hi else min(abs(v - lo), abs(v - hi)))
                gap = round(float(dist.min() / width), 2)
        sens = float(pos["run_passed"].mean()) if len(pos) else None
        spec = float(1 - neg["run_passed"].mean()) if len(neg) else None
        rows.append({
            "task": task, "runs": int(len(g)),
            "intended_runs": int(len(pos)), "intended_pass": int(pos["run_passed"].sum()),
            "partial_runs": int(len(part)), "partial_pass": int(part["run_passed"].sum()),
            "trap_runs": int(len(neg)), "trap_pass": int(neg["run_passed"].sum()),
            "other_runs": int((g["tier"] == "other").sum()),
            "passes": int(len(passes)),
            "passes_from_trap_methods": int((passes["tier"] == "trap").sum()),
            "window_sensitivity": None if sens is None else round(sens, 3),
            "window_specificity": None if spec is None else round(spec, 3),
            "intended_span_in_tolerance_widths": span,
            "trap_runs_inside_intended_span": inside,
            "nearest_trap_gap_in_tolerance_widths": gap,
        })
    return pd.DataFrame(rows)


def separation_by_trap(traced: pd.DataFrame) -> pd.DataFrame:
    """One row per named trap method: where its answers land and whether the
    readout separates it from the intended method.

    Each trap method is its own negative control, as each control compound is
    on a plate. Pooling different traps into one population would mix answers
    that are designed to miss on opposite sides of the window.
    """
    rows = []
    for task, g in traced.groupby("task", sort=False):
        pos = g[g["tier"] == "intended"]["value"].dropna()
        for method, t in g[g["tier"] == "trap"].groupby("method", sort=False):
            z = classic_zprime(pos, t["value"].dropna())
            m = pd.to_numeric(t["margin"], errors="coerce").dropna()
            rows.append({
                "task": task, "trap_method": method, "runs": int(len(t)),
                "configurations": int(t["config"].nunique()), "providers": int(t["provider"].nunique()),
                "runs_passed": int(t["run_passed"].sum()),
                "configurations_with_a_pass": int(t.groupby("config")["run_passed"].any().sum()),
                "lowest_margin": round(float(m.min()), 2) if len(m) else None,
                "median_margin": round(float(m.median()), 2) if len(m) else None,
                "highest_margin": round(float(m.max()), 2) if len(m) else None,
                "distinct_answers": int(t["value"].round(6).nunique()),
                "zprime_against_intended": None if z is None else (z if math.isinf(z) else round(z, 2)),
                "zprime_note": ("" if z is not None else
                                f"needs at least {MIN_CONTROL} runs in each control"),
            })
    return pd.DataFrame(rows)


def implied_split_share(accuracy_pct: float, ci_low_pct: float, ci_high_pct: float, n_tasks: int, repeats: int = 3) -> float | None:
    """Infer, from a published accuracy and its confidence interval, the
    share of tasks whose three repeats are not unanimous.

    A per-task mean m of three pass or fail runs is 0, 1/3, 2/3 or 1, and
    m (1 - m) is 2/9 for the two split outcomes and 0 for the two unanimous
    ones. Since mean(m (1 - m)) equals p (1 - p) - V, with p the accuracy and
    V the population variance of the per-task means, the split share is
    exactly 4.5 (p (1 - p) - V).

    The algebra is exact. Applying it to a published table assumes that:

    - every run is scored pass or fail, with no partial credit;
    - the accuracy is the plain mean of per-task means;
    - every task has exactly three runs;
    - the interval is a t-interval over tasks built from the sample standard
      deviation of the per-task means, so that its width gives V.

    The result is an inference under those assumptions, not a measurement.
    A value outside 0 to 1 means they do not hold for the row, and None is
    returned.
    """
    from scipy import stats

    if any(v is None or (isinstance(v, float) and math.isnan(v)) for v in (accuracy_pct, ci_low_pct, ci_high_pct)):
        return None
    if repeats != 3:
        raise NotImplementedError("the split-share identity used here is specific to three repeats")
    p = accuracy_pct / 100.0
    half = (ci_high_pct - ci_low_pct) / 200.0
    se = half / stats.t.ppf(0.975, n_tasks - 1)
    v_population = se * se * (n_tasks - 1)
    share = 4.5 * (p * (1 - p) - v_population)
    if share < -0.02 or share > 1.0:
        return None
    return float(max(0.0, share))


def leaderboard(table: pd.DataFrame) -> tuple[pd.DataFrame, dict | None]:
    """Read a published leaderboard: who can be told apart, and how noisy are repeats.

    Two readings are reported. The first is an unpaired test of each
    difference: every standard error is recovered from the published
    interval (a t-interval over tasks), and two configurations count as told
    apart when their accuracies differ by more than 1.96 combined standard
    errors. That is the 5% level with no adjustment for the number of pairs.
    The second, overlap of the two intervals, is a looser criterion than
    that test and is kept for reference only: intervals can overlap while
    the difference is significant.

    Every configuration ran the same tasks, so a paired comparison would
    resolve more than either reading. It needs per-task results.
    """
    from scipy import stats

    t = table.rename(columns={"Accuracy (%)": "accuracy", "model_name": "model"}).copy()
    t["config"] = t["model"] + " / " + t["harness"]
    t["implied_split_share"] = [
        implied_split_share(r.accuracy, r.ci_lower, r.ci_upper, int(r.N)) for r in t.itertuples()
    ]
    t["implied_split_share"] = t["implied_split_share"].astype(float).round(3)
    cols = ["config", "accuracy", "ci_lower", "ci_upper", "implied_split_share"]
    with_ci = t.dropna(subset=["ci_lower", "ci_upper"]).sort_values("accuracy", ascending=False, kind="stable")
    t["told_apart_from_leader"] = None
    cols.append("told_apart_from_leader")
    if with_ci.empty:
        return t[cols], None
    top = with_ci.iloc[0]
    others = with_ci.iloc[1:]
    acc = with_ci["accuracy"].to_numpy(float)
    se = ((with_ci["ci_upper"] - with_ci["ci_lower"]) / 2 / stats.t.ppf(0.975, with_ci["N"] - 1)).to_numpy(float)
    critical = float(stats.norm.ppf(0.975))

    def apart(i: int, j: int) -> bool:
        return bool(abs(acc[i] - acc[j]) > critical * math.hypot(se[i], se[j]))

    pairs = overlap = together = 0
    recs = list(with_ci.itertuples())
    for i in range(len(recs)):
        for j in range(i + 1, len(recs)):
            pairs += 1
            overlap += int(recs[i].ci_lower <= recs[j].ci_upper and recs[j].ci_lower <= recs[i].ci_upper)
            together += int(not apart(i, j))
    from_leader = [apart(0, j) for j in range(1, len(recs))]
    t.loc[with_ci.index[1:], "told_apart_from_leader"] = from_leader
    implied = with_ci["implied_split_share"].dropna()
    summary = {
        "configurations": int(len(t)),
        "with_interval": int(len(with_ci)),
        "tasks": int(t["N"].iloc[0]),
        "median_half_width_points": round(float(((with_ci["ci_upper"] - with_ci["ci_lower"]) / 2).median()), 2),
        "comparison": "unpaired test of each difference at the 5% level, no adjustment for the number of pairs",
        "others": int(len(others)),
        "others_not_told_apart_from_the_leader": int(len(from_leader) - sum(from_leader)),
        "others_overlapping_the_leader": int((others["ci_upper"] >= top["ci_lower"]).sum()),
        "pairs": pairs,
        "pairs_not_told_apart": together,
        "pairs_overlapping": overlap,
        "implied_split_share_median": round(float(implied.median()), 3) if len(implied) else None,
        "implied_split_share_min": round(float(implied.min()), 3) if len(implied) else None,
        "implied_split_share_max": round(float(implied.max()), 3) if len(implied) else None,
        "implied_single_rerun_disagreement_median": round(float(implied.median() * 2 / 3), 3) if len(implied) else None,
    }
    return t[cols], summary
