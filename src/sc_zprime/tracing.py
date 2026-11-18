"""Run the method tracer over every task that has a method spec."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from . import methods, trajectory


PACKAGED_ANNOTATIONS = Path(__file__).resolve().parent / "annotations"


def trace(bench, annotations_dir: str | Path | None = None) -> pd.DataFrame:
    """Label the method behind every run of every task that has a spec.

    Reviewed labels ship inside the package, so an installed copy gives the
    same result as a source checkout.
    """
    specs = methods.registry()
    annotations_dir = Path(annotations_dir) if annotations_dir else PACKAGED_ANNOTATIONS
    rows = []
    for task, spec in specs.items():
        fields = bench.fields[(bench.fields["task"] == task) & (bench.fields["field"] == spec.field)]
        if fields.empty:
            continue
        overrides = methods.load_overrides(annotations_dir / f"{task}.csv") if annotations_dir else {}
        run_info = bench.runs.set_index("run_id")
        for f in fields.itertuples():
            run = run_info.loc[f.run_id]
            a = methods.attribute(f.run_id, run["dir"], f.value, spec, overrides)
            ran_intended = False
            if a.tier != "intended":
                # Looser than the label rule on purpose: a script that sweeps
                # several pipelines still ran the intended one if its code is
                # there, so any intended-tier match counts, single or not.
                for step in trajectory.load_steps(Path(run["dir"]) / "trajectory.json"):
                    if any(h.tier == "intended" for h in methods.classify_any(step.command, spec)):
                        ran_intended = True
                        break
            rows.append({
                "task": task, "run_id": f.run_id, "provider": f.provider, "model": f.model,
                "harness": f.harness, "config": f.config, "rep": f.rep, "field": spec.field,
                "method": a.label, "tier": a.tier, "source": a.source, "evidence": a.evidence,
                "value": f.value, "band_lower": f.band_lower, "band_upper": f.band_upper,
                "margin": None if f.margin is None or pd.isna(f.margin) else round(float(f.margin), 2),
                "field_passed": bool(f.passed), "run_passed": bool(run["regraded_pass"]),
                "ran_intended_method_elsewhere": ran_intended,
            })
    return pd.DataFrame(rows)


def by_method(traced: pd.DataFrame) -> pd.DataFrame:
    if traced.empty:
        return traced
    g = traced.groupby(["task", "tier", "method"], sort=False)
    out = g.agg(runs=("run_passed", "size"), passes=("run_passed", "sum"),
                configurations=("config", "nunique"),
                median_margin=("margin", "median")).reset_index()
    out["pass_rate"] = (out["passes"] / out["runs"]).round(3)
    out["median_margin"] = out["median_margin"].round(2)
    order = {"intended": 0, "partial": 1, "trap": 2, "other": 3}
    out["_o"] = out["tier"].map(order)
    return out.sort_values(["task", "_o", "runs"], ascending=[True, True, False]).drop(columns="_o").reset_index(drop=True)
