"""Run every analysis and write tables, validation cards, and a summary.

Outputs carry tolerance-normalised quantities only: margins, rates, counts.
No reference value, submitted value, or task prompt is written. See
docs/DATA_POLICY.md.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from . import __version__, load, methods, metrics, provenance, tracing, uncertainty


def _md_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "_none_\n"
    cols = [str(c) for c in df.columns]
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for row in df.itertuples(index=False):
        cells = []
        for v in row:
            if v is None or (isinstance(v, float) and pd.isna(v)):
                cells.append("n/a")
            elif isinstance(v, bool):
                cells.append("yes" if v else "no")
            elif isinstance(v, float):
                cells.append(f"{v:g}")
            else:
                cells.append(str(v))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


def _pct(x) -> str:
    return "n/a" if x is None or pd.isna(x) else f"{100 * float(x):.0f}%"


def _unc(unc: pd.DataFrame, scope: str, statistic: str):
    if unc is None or not len(unc):
        return None
    hit = unc[(unc["scope"] == scope) & (unc["statistic"] == statistic)]
    return hit.iloc[0] if len(hit) else None


def task_flags(task: str, ro: pd.DataFrame, cl: pd.DataFrame, rep: pd.DataFrame, sep: pd.DataFrame,
               by_config: pd.DataFrame | None = None, by_trap: pd.DataFrame | None = None) -> list[str]:
    """Plain-language flags. Each prompts a look; none is a verdict on the task."""
    flags = []
    r = ro[ro["task"] == task]
    dead = r[r["dead"]]
    if len(dead):
        decided = int(dead["failures_from_field_alone"].sum())
        flags.append(f"DEAD_READOUT: {len(dead)} of {len(r)} graded fields are passed by at least 95% of runs; "
                     f"between them they decided {decided} verdict(s) on their own")
    c = cl[(cl["task"] == task) & cl["near_edge"]] if len(cl) else cl
    if len(c):
        flags.append(f"EDGE_CLUSTER: {len(c)} cluster(s) of identical answers, {int(c['runs'].sum())} runs in all, "
                     "sit within 20% inside or 25% outside a window edge")
    s = rep[rep["task"] == task]
    if len(s) and s["cells"].iloc[0] and int(s["split"].iloc[0]) / int(s["cells"].iloc[0]) >= 0.2:
        flags.append(f"UNSTABLE_REPEATS: {int(s['split'].iloc[0])} of {int(s['cells'].iloc[0])} configurations gave different verdicts across repeats")
    m = sep[sep["task"] == task] if len(sep) else sep
    if len(m) and int(m.iloc[0]["trap_pass"]) > 0:
        row = m.iloc[0]
        flags.append(f"TRAP_PASSES: {int(row['trap_pass'])} of {int(row['trap_runs'])} runs that used a method the task notes name as incorrect passed")
    thin = []
    if by_config is not None and len(by_config):
        t = by_config[(by_config["task"] == task) & (by_config["tier"] == "intended")]
        if len(t):
            thin.append(("intended-method control", t.iloc[0]))
    if by_trap is not None and len(by_trap):
        for _, row in by_trap[by_trap["task"] == task].iterrows():
            thin.append((f"control for the trap '{row['trap_method']}'", row))
    for name, row in thin:
        if int(row["configurations"]) < uncertainty.MIN_UNITS or int(row["providers"]) < 2:
            flags.append(f"THIN_CONTROL: the {name} rests on {int(row['runs'])} run(s) from "
                         f"{int(row['configurations'])} configuration(s) and {int(row['providers'])} provider(s). "
                         "This describes the published runs, not the task")
    return flags


def validation_card(task: str, bench, ro, cl, cells, rep, edge, sep, bym, traced, unc=None, by_config=None, by_trap=None) -> str:
    t = bench.tasks[bench.tasks["task"] == task].iloc[0]
    runs = bench.runs[bench.runs["task"] == task]
    lines = [f"# Validation card: {task}", ""]
    lines += [f"- Benchmark: {bench.name}", f"- Category: {t['category']}", f"- Platform: {t['platform']}",
              f"- Grader: {t['grader_type']}, {t['n_fields']} field(s), all must pass",
              f"- Evidence: {len(runs)} graded runs from {runs['config'].nunique()} configurations, {runs['rep'].nunique()} repeats each",
              f"- Pass rate: {runs['regraded_pass'].mean():.1%}",
              f"- Verdicts reproduced by the independent grader: {int((runs['published_pass'] == runs['regraded_pass']).sum())} of {len(runs)}", ""]
    flags = task_flags(task, ro, cl, rep, sep, by_config, by_trap)
    context = methods.notes_context(task)
    lines += ["## Flags", "", "A flag prompts a look. It is not a verdict on the task, and the task's own notes may "
              "already explain it. Where they do, that is said under the flag.", ""]
    for f in flags:
        lines.append(f"- {f}")
        said = context.get(f.split(":")[0])
        if said:
            lines.append(f"  - What the task notes say: {said}")
    lines += ([] if flags else ["- none"]) + [""]
    lines += ["## Readouts", "", "Window widths are a percentage of the reference value, to the nearest percent.", ""]
    cols = ["field", "kind", "window_lower_pct_of_reference", "window_upper_pct_of_reference", "lower_edge_at_zero", "pass_rate",
            "distinct_answers", "largest_cluster_share", "dead", "failures_involving_field", "failures_from_field_alone"]
    lines += [_md_table(ro[ro["task"] == task][cols])]
    if ro[ro["task"] == task]["lower_edge_at_zero"].any():
        lines += ["A window whose lower edge is zero is a ceiling check: only the upper edge can be missed. "
                  "That edge is not moved in the edge-sensitivity test below.", ""]
    lines += ["## Answer clusters", "",
              "Three or more runs that submitted the identical value for a field with a tolerance window (answers are compared "
              "after rounding to six decimals; exact-match fields are not listed). Margin is in tolerance widths: 0 is the "
              "reference, 1 is the window edge.", ""]
    c = cl[cl["task"] == task].drop(columns=["task"]) if len(cl) else cl
    lines += [_md_table(c)]
    lines += ["## Edge sensitivity", ""]
    e = edge[edge["task"] == task]
    if len(e):
        lines += [f"{int(e['edge_decided'].iloc[0])} of {int(e['runs'].iloc[0])} verdicts flip if every tolerance is made 20% tighter or 25% wider.", ""]
    lines += ["## Repeatability", ""]
    s = rep[rep["task"] == task]
    if len(s):
        s = s.iloc[0]
        lines += [f"{int(s['cells'])} configurations: {int(s['all_pass'])} passed every repeat, {int(s['all_fail'])} failed every repeat, "
                  f"{int(s['split'])} split. {int(round(float(s['identical_answer_share']) * int(s['cells'])))} submitted the identical answer on every repeat.", ""]
    if len(sep) and task in set(sep["task"]):
        spec = methods.registry()[task]
        m = sep[sep["task"] == task].iloc[0]
        lines += ["## Method separation", "", f"Traced field: `{spec.field}`. Basis for the tiers: {spec.basis}.", ""]
        for tier in ("intended", "partial", "trap", "other"):
            if tier in spec.describe:
                lines.append(f"- {tier}: {spec.describe[tier]}")
        lines += ["", "By method:", "", _md_table(bym[bym["task"] == task].drop(columns=["task"]))]
        if by_config is not None and len(by_config):
            lines += ["By configuration (one model in one harness; its three repeats are not independent):", "",
                      _md_table(by_config[by_config["task"] == task].drop(columns=["task"]))]

        def interval(statistic, flip=False):
            u = _unc(unc, task, statistic)
            if u is None:
                return ""
            if not pd.isna(u["ci_low"]):
                lo, hi = (1 - u["ci_high"], 1 - u["ci_low"]) if flip else (u["ci_low"], u["ci_high"])
                return f"; 95% interval {_pct(lo)} to {_pct(hi)}"
            units = int(u["units_with_data"])
            if not pd.isna(u["one_sided_bound"]):
                # Every configuration agrees, so resampling them cannot give an interval.
                bound = 1 - u["one_sided_bound"] if flip else u["one_sided_bound"]
                at_least = (float(u["estimate"]) == 1.0) != flip
                who = f"all {units} configurations agree" if units > 1 else "the one configuration with data agrees"
                return (f"; {who}, so there is no bootstrap interval. Counted in configurations, the exact one-sided "
                        f"97.5% bound is {'at least' if at_least else 'at most'} {_pct(bound)}")
            return f"; no interval, because fewer than {uncertainty.MIN_UNITS} configurations stand behind it"

        n_int, n_trap = int(m["intended_runs"]), int(m["trap_runs"])
        lines += ["The pass window as a test of method (whole-run verdicts):", ""]
        if n_int:
            lines.append(f"- Sensitivity, intended-method runs that pass: {int(m['intended_pass'])} of {n_int} "
                         f"({_pct(m['window_sensitivity'])}{interval('intended-method runs that pass')})")
        if n_trap:
            lines.append(f"- Specificity, trap-method runs that fail: {n_trap - int(m['trap_pass'])} of {n_trap} "
                         f"({_pct(m['window_specificity'])}{interval('trap-method runs that pass', flip=True)})")
        lines.append(f"- Passing runs that used a trap method: {int(m['passes_from_trap_methods'])} of {int(m['passes'])}"
                     f"{interval('share of passes that come from trap methods')}")
        if n_int and n_trap and m["intended_span_in_tolerance_widths"] is not None:
            lines += ["", "The traced readout on its own:", "",
                      f"- Intended-method answers span {m['intended_span_in_tolerance_widths']} tolerance widths. "
                      f"Trap-method answers inside that span: {int(m['trap_runs_inside_intended_span'])} of {n_trap}. "
                      f"Nearest trap answer: {m['nearest_trap_gap_in_tolerance_widths']} tolerance widths outside it."]
        if by_trap is not None and len(by_trap) and task in set(by_trap["task"]):
            bt = by_trap[by_trap["task"] == task].drop(columns=["task"]).copy()
            ci, defined = [], []
            for method in bt["trap_method"]:
                u = _unc(unc, task, f"Z-prime, intended against: {method}")
                if u is None:
                    ci.append("")
                    defined.append("")
                    continue
                few = min(int(u["positive_control_units"]), int(u["negative_control_units"]))
                if not pd.isna(u["ci_low"]):
                    ci.append(f"{u['ci_low']:.2f} to {u['ci_high']:.2f}")
                elif u["interval_note"] == "no spread":
                    ci.append("not reported: the answers within each method are identical or nearly so")
                else:
                    ci.append(f"not reported: a control comes from {few} configuration(s)")
                defined.append(_pct(u["share_of_resamples_defined"]))
            bt["zprime_95pct_interval"] = ci
            bt["resamples_where_zprime_is_defined"] = defined
            lines += ["", "Each named trap method as its own negative control. Z-prime is the classic mean and SD form, "
                      "computed on the traced field against the intended-method answers. It is a rough summary here: "
                      "answers come in clusters of identical values and the pass window has two edges, so a negative "
                      "value can occur with no answer of one method lying among the answers of the other, and two "
                      "controls with no spread score exactly 1 however close they are. Read it with the margins "
                      "above.", "", _md_table(bt)]
        tr = traced[traced["task"] == task]
        missed = tr[(tr["tier"] != "intended") & tr["ran_intended_method_elsewhere"]]
        lines += [f"- Runs that ran an intended method at some step but submitted a different method's number: {len(missed)}",
                  f"- Labels: {int((tr['source'].isin(['printed', 'printed_by_script'])).sum())} traced from the printed value, "
                  f"{int((tr['source'] == 'fallback').sum())} from the last classifiable step, {int((tr['source'] == 'reviewed').sum())} set by reading the transcript in full. "
                  "All were confirmed by blind AI raters (see validation/).",
                  "- Intervals are 95% cluster-bootstrap percentile intervals that resample whole configurations. "
                  "With this few configurations they are approximate and probably too narrow.", ""]
    return "\n".join(lines) + "\n"


def run(upstream: str | Path, out: str | Path, annotations: str | Path | None = None, name: str | None = None) -> dict:
    upstream, out = Path(upstream), Path(out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "validation_cards").mkdir(exist_ok=True)
    bench = load.load_latch_layout(upstream, name)

    ro = metrics.readouts(bench)
    bins = metrics.margin_bins(bench)
    sweep = metrics.tolerance_sweep(bench)
    sweep_tab = metrics.sweep_summary(sweep)
    edge = metrics.edge_decided(sweep)
    cl = metrics.clusters(bench)
    cells = metrics.repeatability(bench)
    rep = metrics.repeatability_summary(cells)
    credit = metrics.credit(bench)
    traced = tracing.trace(bench, annotations)
    bym = tracing.by_method(traced)
    sep = metrics.method_separation(traced) if len(traced) else pd.DataFrame()
    by_trap = metrics.separation_by_trap(traced) if len(traced) else pd.DataFrame()

    if not len(traced):
        traced = pd.DataFrame(columns=["task", "config", "provider", "tier", "method", "value", "margin", "run_passed"])
    unc = uncertainty.uncertainty(bench, sweep, cells, traced)
    by_config = uncertainty.configuration_level(traced)
    sens = uncertainty.sensitivity(bench, traced)
    unc.to_csv(out / "uncertainty.csv", index=False)
    sens.to_csv(out / "sensitivity.csv", index=False)
    if len(by_config):
        by_config.to_csv(out / "method_by_configuration.csv", index=False)

    board_summary = None
    board_path = upstream / "results" / "model_results.csv"
    if board_path.exists():
        board, board_summary = metrics.leaderboard(pd.read_csv(board_path))
        board.to_csv(out / "leaderboard_implied.csv", index=False)

    bench.tasks.to_csv(out / "tasks.csv", index=False)
    ro.to_csv(out / "readouts.csv", index=False)
    bins.to_csv(out / "margin_zones.csv", index=False)
    sweep_tab.to_csv(out / "tolerance_sweep.csv", index=False)
    edge.to_csv(out / "edge_decided.csv", index=False)
    cl.to_csv(out / "answer_clusters.csv", index=False)
    cells.to_csv(out / "repeat_cells.csv", index=False)
    rep.to_csv(out / "repeatability.csv", index=False)
    credit.to_csv(out / "credit.csv", index=False)
    if len(traced):
        traced.drop(columns=["provider", "value", "band_lower", "band_upper"]).to_csv(out / "method_trace.csv", index=False)
        by_trap.to_csv(out / "method_by_trap.csv", index=False)
        bym.to_csv(out / "method_by_tier.csv", index=False)
        sep.to_csv(out / "method_separation.csv", index=False)

    for task in bench.tasks["task"]:
        if task not in set(bench.runs["task"]):
            continue
        card = validation_card(task, bench, ro, cl, cells, rep, edge, sep, bym, traced, unc, by_config, by_trap)
        (out / "validation_cards" / f"{task}.md").write_text(card, encoding="utf-8")

    numeric = ro[ro["kind"] != "exact"]
    overall_rep = rep[rep["task"] == "ALL"].iloc[0]
    overall_edge = edge[edge["task"] == "ALL"].iloc[0]
    clustered = int(cl["runs"].sum()) if len(cl) else 0
    numeric_answers = int(bench.fields["margin"].notna().sum())
    dead_keys = set(zip(ro[ro["dead"]]["task"], ro[ro["dead"]]["field"]))
    live_fields = bench.fields[bench.fields["margin"].notna()]
    live_fields = live_fields[[(t, f) not in dead_keys for t, f in zip(live_fields["task"], live_fields["field"])]]
    live_clustered = int(cl[~cl["field_is_dead"]]["runs"].sum()) if len(cl) else 0
    summary = {
        "tool_version": __version__,
        "benchmark": bench.name,
        "upstream_commit": provenance.git_head(upstream),
        "inputs": provenance.input_fingerprint(upstream),
        "environment": provenance.environment(),
        "uncertainty": {"method": "cluster bootstrap over configurations, 95% percentile interval",
                        "resamples": uncertainty.N_BOOT, "seed": uncertainty.SEED,
                        "caveat": "approximate and probably too narrow with this few configurations; "
                                  "no interval when every configuration agrees or fewer than "
                                  f"{uncertainty.MIN_UNITS} stand behind a number"},
        "reproduce": metrics.reproduce(bench),
        "skipped": bench.skipped,
        "runs_with_a_configuration_error": int(bench.runs["config_error"].notna().sum()),
        "pass_rate": round(float(bench.runs["regraded_pass"].mean()), 3),
        "readouts": {
            "fields": int(len(ro)), "numeric_fields": int(len(numeric)),
            "dead_fields": int(ro["dead"].sum()),
            "tasks_with_a_dead_field": int(ro[ro["dead"]]["task"].nunique()),
        },
        "edge": {"edge_decided_runs": int(overall_edge["edge_decided"]), "runs": int(overall_edge["runs"]),
                 "share": float(overall_edge["share"])},
        "clusters": {"numeric_answers": numeric_answers, "answers_in_clusters_of_3_or_more": clustered,
                     "share": round(clustered / numeric_answers, 3) if numeric_answers else None,
                     "live_field_answers": int(len(live_fields)), "live_field_answers_in_clusters": live_clustered,
                     "live_field_share": round(live_clustered / len(live_fields), 3) if len(live_fields) else None,
                     "clusters_near_an_edge": int(cl["near_edge"].sum()) if len(cl) else 0,
                     "runs_in_clusters_near_an_edge": int(cl[cl["near_edge"]]["runs"].sum()) if len(cl) else 0},
        "repeatability": {"cells": int(overall_rep["cells"]), "split": int(overall_rep["split"]),
                          "split_share": float(overall_rep["split_share"]),
                          "identical_answer_share": float(overall_rep["identical_answer_share"])},
        "method_tracing": None,
        "leaderboard": board_summary,
    }
    if len(traced):
        passes = traced[traced["run_passed"]]
        summary["method_tracing"] = {
            "tasks_traced": int(traced["task"].nunique()), "runs_traced": int(len(traced)),
            "labels_set_by_reading": int((traced["source"] == "reviewed").sum()),
            "unresolved": int(traced["method"].isin(["unresolved", "ambiguous"]).sum()),
            "passes": int(len(passes)),
            "passes_from_trap_methods": int((passes["tier"] == "trap").sum()),
            "ran_intended_but_submitted_other": int(((traced["tier"] != "intended") & traced["ran_intended_method_elsewhere"]).sum()),
            "traced_from_printed_value": int(traced["source"].isin(["printed", "printed_by_script"]).sum()),
            "traced_by_fallback": int((traced["source"] == "fallback").sum()),
            "by_task": json.loads(sep.to_json(orient="records")),
            "by_trap_method": json.loads(by_trap.to_json(orient="records")),
        }
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary
