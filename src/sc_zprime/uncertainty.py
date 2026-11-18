"""Uncertainty and sensitivity for the headline numbers.

Runs are not independent. Three repeats share a configuration (one model in
one harness), and configurations share a provider and a model family. Treating
273 runs as 273 observations would understate every interval. So:

- **Intervals** come from a cluster bootstrap that resamples whole
  configurations with replacement, keeping all of a configuration's runs
  together. They are 95% percentile intervals from a fixed seed.
- **Leave-one-provider-out** recomputes each number with every run from one
  provider removed, and reports the lowest and highest value. With four
  providers a bootstrap over providers would be meaningless, so this is the
  honest check that no single provider drives a result.
- **Sensitivity** recomputes results under other reasonable choices of every
  threshold the analysis fixed in advance: the edge scales, the dead-readout
  cut-off, the cluster size, and how Z-prime is defined.

The six tasks are fixed, not sampled: they are examples the benchmark authors
chose. Nothing here is an interval for the benchmark as a whole.

Read the intervals as approximate, and probably too narrow:

- A percentile bootstrap over 16 configurations, or 8 or fewer for the rates
  on one method, covers the truth less often than its nominal 95%.
  `scripts/interval_coverage.py` simulates clusters sized like these.
- Configurations are resampled as if independent. Many share a recipe, and
  with it an answer, across models and providers.
- When every configuration agrees, a bootstrap returns the same value every
  time, which is not an interval. Those rows carry an exact one-sided bound
  counted in configurations instead.
- When fewer than three configurations stand behind a number, no interval is
  reported.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import metrics

N_BOOT = 10000
SEED = 20261117
MIN_UNITS = 3  # configurations needed behind a number before an interval is reported


def agreement_bound(units: int) -> float:
    """Exact one-sided 97.5% bound for a rate when all `units` units agree.

    If each of k independent configurations shows an outcome, a true rate
    below 0.025 ** (1 / k) would produce that less than 2.5% of the time
    (the Clopper-Pearson bound for k successes in k trials).
    """
    return float(0.025 ** (1.0 / units))


def _ratio_boot(num: np.ndarray, den: np.ndarray, rng: np.random.Generator, n_boot: int) -> np.ndarray:
    """Bootstrap a ratio of sums over resampled units."""
    idx = rng.integers(0, len(num), size=(n_boot, len(num)))
    d = den[idx].sum(axis=1).astype(float)
    n = num[idx].sum(axis=1).astype(float)
    return np.divide(n, d, out=np.full(n_boot, np.nan), where=d > 0)


def _interval(values: np.ndarray) -> tuple[float | None, float | None, float]:
    ok = ~np.isnan(values)
    if not ok.any():
        return None, None, 0.0
    lo, hi = np.percentile(values[ok], [2.5, 97.5])
    return float(lo), float(hi), float(ok.mean())


def ratio_row(frame: pd.DataFrame, num: str, den: str, rng, n_boot: int) -> dict:
    """Point estimate, cluster-bootstrap interval and leave-one-provider-out
    range for sum(num) / sum(den). `frame` has one row per configuration with
    a `provider` column."""
    n, d = frame[num].to_numpy(float), frame[den].to_numpy(float)
    total = d.sum()
    est = float(n.sum() / total) if total > 0 else None
    with_data = int((d > 0).sum())
    lo, hi, defined = _interval(_ratio_boot(n, d, rng, n_boot)) if total > 0 else (None, None, 0.0)
    bound, note = None, ""
    if total > 0 and n.sum() in (0.0, total):
        # Resampling units that all agree returns one value every time. Report a bound instead.
        lo = hi = None
        bound = agreement_bound(with_data) if n.sum() == total else 1 - agreement_bound(with_data)
        note = "all units agree"
    elif total > 0 and with_data < MIN_UNITS:
        lo = hi = None
        note = f"fewer than {MIN_UNITS} units"
    lopo = []
    for provider in sorted(frame["provider"].unique()):
        rest = frame[frame["provider"] != provider]
        if rest[den].sum() > 0:
            lopo.append(float(rest[num].sum() / rest[den].sum()))
    return {
        "estimate": est, "ci_low": lo, "ci_high": hi, "interval_note": note, "one_sided_bound": bound,
        "numerator": int(n.sum()), "denominator": int(total),
        "units_with_data": with_data, "units": int(len(frame)),
        "share_of_resamples_defined": round(defined, 3),
        "lopo_min": min(lopo) if lopo else None, "lopo_max": max(lopo) if lopo else None,
    }


def zprime_row(traced: pd.DataFrame, trap_method: str, rng, n_boot: int) -> dict:
    """Z-prime between the intended control and one named trap method, with a
    cluster-bootstrap interval that resamples configurations.

    A resample that draws fewer than three runs for either control cannot
    compute Z-prime and is left out; `share_of_resamples_defined` says how
    often that happened. No interval is reported when either control comes
    from fewer than `MIN_UNITS` configurations.
    """
    pos_by, neg_by = [], []
    for _, g in traced.groupby("config", sort=True):
        pos_by.append(g[g["tier"] == "intended"]["value"].dropna().to_numpy(float))
        neg_by.append(g[g["method"] == trap_method]["value"].dropna().to_numpy(float))
    pos, neg = np.concatenate(pos_by), np.concatenate(neg_by)
    pos_units, neg_units = sum(len(a) > 0 for a in pos_by), sum(len(a) > 0 for a in neg_by)
    est = metrics.classic_zprime(pos, neg)
    vals = np.full(n_boot, np.nan)
    for b in range(n_boot):
        pick = rng.integers(0, len(pos_by), size=len(pos_by))
        value = metrics.classic_zprime(np.concatenate([pos_by[i] for i in pick]), np.concatenate([neg_by[i] for i in pick]))
        if value is not None and np.isfinite(value):
            vals[b] = value
    lo, hi, defined = _interval(vals)
    below = float(np.mean(vals[~np.isnan(vals)] < 0)) if defined > 0 else None
    note = ""
    if min(pos_units, neg_units) < MIN_UNITS:
        lo = hi = below = None
        note = f"fewer than {MIN_UNITS} units"
    elif lo is not None and hi - lo < 0.005:
        # Runs of one method that all submit one value leave nothing to resample.
        lo = hi = None
        note = "no spread"

    def z(frame):
        return metrics.classic_zprime(frame[frame["tier"] == "intended"]["value"].dropna(),
                                      frame[frame["method"] == trap_method]["value"].dropna())

    lopo = []
    for provider in sorted(traced["provider"].unique()):
        value = z(traced[traced["provider"] != provider])
        if value is not None and np.isfinite(value):
            lopo.append(value)
    return {
        "estimate": est, "ci_low": lo, "ci_high": hi, "interval_note": note, "one_sided_bound": None,
        "numerator": None, "denominator": None, "units_with_data": None, "units": int(traced["config"].nunique()),
        "positive_control_runs": int(len(pos)), "negative_control_runs": int(len(neg)),
        "positive_control_units": int(pos_units), "negative_control_units": int(neg_units),
        "share_of_resamples_defined": round(defined, 3),
        "lopo_min": min(lopo) if lopo else None, "lopo_max": max(lopo) if lopo else None,
        "share_of_resamples_below_zero": below,
    }


def uncertainty(bench, sweep: pd.DataFrame, cells: pd.DataFrame, traced: pd.DataFrame,
                n_boot: int = N_BOOT, seed: int = SEED) -> pd.DataFrame:
    """One row per headline number: estimate, 95% interval, leave-one-provider-out range."""
    rng = np.random.default_rng(seed)
    provider = bench.runs.drop_duplicates("config").set_index("config")["provider"]
    rows = []

    def add(scope, statistic, row):
        rows.append({"scope": scope, "statistic": statistic, **row})

    runs = bench.runs.copy()
    near = sweep[sweep["scale"].isin([metrics.EDGE_INNER, metrics.EDGE_OUTER])]
    runs["edge"] = runs["run_id"].map(near.groupby("run_id")["flipped"].any()).fillna(False)
    per = runs.groupby("config").agg(runs=("regraded_pass", "size"), passes=("regraded_pass", "sum"), edge=("edge", "sum")).reset_index()
    per["provider"] = per["config"].map(provider)
    add("ALL", "pass rate", ratio_row(per, "passes", "runs", rng, n_boot))
    add("ALL", "share of verdicts that are edge-decided", ratio_row(per, "edge", "runs", rng, n_boot))

    c = cells.groupby("config").agg(cells=("split", "size"), split=("split", "sum")).reset_index()
    c["provider"] = c["config"].map(provider)
    add("ALL", "share of task x configuration cells with split repeats", ratio_row(c, "split", "cells", rng, n_boot))

    for task, g in traced.groupby("task", sort=False):
        g = g.assign(
            trap=(g["tier"] == "trap"), intended=(g["tier"] == "intended"),
            trap_pass=(g["tier"] == "trap") & g["run_passed"],
            intended_pass=(g["tier"] == "intended") & g["run_passed"],
        )
        p = g.groupby("config").agg(trap=("trap", "sum"), trap_pass=("trap_pass", "sum"), intended=("intended", "sum"),
                                    intended_pass=("intended_pass", "sum"), passes=("run_passed", "sum")).reset_index()
        p["provider"] = p["config"].map(provider)
        add(task, "trap-method runs that pass", ratio_row(p, "trap_pass", "trap", rng, n_boot))
        add(task, "share of passes that come from trap methods", ratio_row(p, "trap_pass", "passes", rng, n_boot))
        add(task, "intended-method runs that pass", ratio_row(p, "intended_pass", "intended", rng, n_boot))
        for method, t in g[g["tier"] == "trap"].groupby("method", sort=False):
            if len(t) >= metrics.MIN_CONTROL and int(g["intended"].sum()) >= metrics.MIN_CONTROL:
                add(task, f"Z-prime, intended against: {method}", zprime_row(g, method, rng, n_boot))

    # Per-task pass rates use their own random stream, so adding them cannot shift any interval above.
    extra = np.random.default_rng([seed, 1])
    by_task = bench.runs.groupby(["task", "config"], sort=False).agg(
        runs=("regraded_pass", "size"), passes=("regraded_pass", "sum")).reset_index()
    by_task["provider"] = by_task["config"].map(provider)
    for task, g in by_task.groupby("task", sort=False):
        add(task, "pass rate", ratio_row(g, "passes", "runs", extra, n_boot))

    out = pd.DataFrame(rows)
    for col in ("estimate", "ci_low", "ci_high", "one_sided_bound", "lopo_min", "lopo_max", "share_of_resamples_below_zero"):
        if col in out:
            out[col] = out[col].astype(float).round(3)
    for col in ("numerator", "denominator", "units_with_data", "positive_control_runs", "negative_control_runs",
                "positive_control_units", "negative_control_units"):
        if col in out:
            out[col] = out[col].astype("Int64")
    order = ["scope", "statistic", "estimate", "ci_low", "ci_high", "interval_note", "one_sided_bound", "numerator",
             "denominator", "units_with_data", "units", "positive_control_runs", "negative_control_runs",
             "positive_control_units", "negative_control_units", "share_of_resamples_defined", "lopo_min", "lopo_max",
             "share_of_resamples_below_zero"]
    return out[[c for c in order if c in out]]


def configuration_level(traced: pd.DataFrame) -> pd.DataFrame:
    """The same method findings counted in configurations, not runs."""
    rows = []
    for task, g in traced.groupby("task", sort=False):
        for tier, t in g.groupby("tier", sort=False):
            by = t.groupby("config")["run_passed"].agg(["size", "sum"])
            rows.append({
                "task": task, "tier": tier, "runs": int(len(t)), "runs_passed": int(t["run_passed"].sum()),
                "configurations": int(len(by)), "configurations_with_a_pass": int((by["sum"] > 0).sum()),
                "configurations_passing_every_time": int((by["sum"] == by["size"]).sum()),
                "providers": int(t["provider"].nunique()),
            })
    return pd.DataFrame(rows)


def sensitivity(bench, traced: pd.DataFrame) -> pd.DataFrame:
    """Recompute results under other reasonable analysis choices."""
    rows = []

    def add(analysis, setting, scope, value, baseline=False):
        ok = value is not None and not (isinstance(value, float) and np.isnan(value))
        rows.append({"analysis": analysis, "setting": setting, "scope": scope,
                     "value": round(float(value), 3) if ok else None, "baseline": baseline})

    for inner, outer in ((0.95, 1.05), (0.9, 1.1), (0.8, 1.25), (0.67, 1.5), (0.5, 2.0)):
        sweep = metrics.tolerance_sweep(bench, scales=(inner, 1.0, outer))
        flipped = sweep[sweep["scale"] != 1.0].groupby("run_id")["flipped"].any()
        add("edge-decided share of verdicts", f"tolerance x{inner} or x{outer}", "ALL", flipped.mean(),
            baseline=(inner, outer) == (metrics.EDGE_INNER, metrics.EDGE_OUTER))

    pass_rate = bench.fields.groupby(["task", "field"])["passed"].mean()
    for cut in (0.90, 0.95, 1.00):
        add("dead readouts (count of fields)", f"passed by at least {cut:.0%} of runs", "ALL", int((pass_rate >= cut).sum()),
            baseline=cut == metrics.DEAD_THRESHOLD)

    numeric = bench.fields[bench.fields["margin"].notna()]
    sizes = numeric.assign(key=numeric["value"].round(6)).groupby(["task", "field", "key"])["run_id"].transform("size")
    for k in (2, 3, 5):
        add("share of numeric answers in a cluster of identical values", f"cluster of at least {k}", "ALL",
            (sizes >= k).mean(), baseline=k == metrics.MIN_CLUSTER)

    for task, g in traced.groupby("task", sort=False):
        pos = g[g["tier"] == "intended"]["value"].dropna()
        neg = g[g["tier"] == "trap"]["value"].dropna()
        part = g[g["tier"] == "partial"]["value"].dropna()
        for method, t in g[g["tier"] == "trap"].groupby("method", sort=False):
            add("Z-prime", f"per trap method (the reported form): {method}", task,
                metrics.classic_zprime(pos, t["value"].dropna()), baseline=True)
        add("Z-prime", "all trap methods pooled, mean and SD", task, metrics.classic_zprime(pos, neg))
        add("Z-prime", "all trap methods pooled, median and MAD", task, metrics.robust_zprime(pos, neg))
        if len(part):
            add("Z-prime", "pooled, mean and SD, partial tier counted as a negative control", task,
                metrics.classic_zprime(pos, pd.concat([neg, part])))
        runs_by = g.groupby("tier")["run_passed"].agg(["sum", "size"])
        if "trap" in runs_by.index:
            add("share of trap-method runs that pass", "as labelled", task, runs_by.loc["trap", "sum"] / runs_by.loc["trap", "size"], baseline=True)
            if "partial" in runs_by.index:
                both = runs_by.loc[["trap", "partial"]].sum()
                add("share of trap-method runs that pass", "partial tier counted as a trap", task, both["sum"] / both["size"])
        for provider in sorted(g["provider"].unique()):
            rest = g[(g["provider"] != provider) & (g["tier"] == "trap")]
            if len(rest):
                add("share of trap-method runs that pass", f"without {provider}", task, rest["run_passed"].mean())
    return pd.DataFrame(rows)
