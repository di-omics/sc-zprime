"""The headline numbers in the documents must match the committed tables.

Prose drifts from the data it describes. Each check below rebuilds a sentence
from `results/scbench` and requires it to appear, word for word, in the
document. A stale number, or a reworded claim that was not rechecked, fails.

These checks need no benchmark data: they read only files in this repository.
"""

import json
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results" / "scbench"

WORDS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
         "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen"]

DE, NRM, PCA = "DE01_pseudobulk_de", "NRM01_sparse_normalization", "dr_05_pca_preprocessing_sentinels"
CLUSTERING = "tapestri_ccus_clustering_12_largest_mutant_clone"
NAMES = {DE: "Differential expression", NRM: "Normalization", PCA: "PCA preprocessing"}
RANK = "per-cell rank test"
README, FINDINGS = "README.md", "docs/FINDINGS.md"


def text(relative):
    """A document with every run of whitespace collapsed to one space."""
    return " ".join((ROOT / relative).read_text().split())


def pct(share):
    return f"{round(100 * float(share))}%"


@pytest.fixture(scope="module")
def data():
    names = ["method_separation", "method_by_trap", "method_trace", "uncertainty", "repeatability", "edge_decided",
             "answer_clusters"]
    d = {name: pd.read_csv(RES / f"{name}.csv") for name in names}
    d["summary"] = json.loads((RES / "summary.json").read_text())
    d["ratings"] = pd.read_csv(ROOT / "validation" / "blind_rerating.csv")
    return d


def unc(data, scope, statistic):
    u = data["uncertainty"]
    rows = u[(u["scope"] == scope) & (u["statistic"] == statistic)]
    assert len(rows) == 1, (scope, statistic)
    return rows.iloc[0]


def claims(data):
    """(document, sentence) pairs, each built from the tables."""
    s, trap, trace = data["summary"], data["method_by_trap"], data["method_trace"]
    sep = data["method_separation"].set_index("task")
    out = []

    def say(document, sentence):
        out.append((document, sentence))

    rep, edge, rpt, dead, board, tracing = (s["reproduce"], s["edge"], s["repeatability"], s["readouts"],
                                            s["leaderboard"], s["method_tracing"])
    say(README, f"{WORDS[rep['tasks']].capitalize()} example tasks, {rep['configurations']} model and harness "
                f"configurations, {rpt['cells']} task and configuration pairs with three repeats each: "
                f"{rep['runs']} graded runs.")
    say(README, f"An independent grader agrees on {rep['runs_agree']} of {rep['runs']} runs.")
    say(FINDINGS, f"{rep['runs_agree']} of {rep['runs']} run verdicts")
    say(FINDINGS, f"{rep['fields_agree']} of {rep['fields']} field-level verdicts")

    # Sensitivity and specificity of the pass window.
    say(README, f"Yes, on all three tasks traced: {sep['intended_pass'].sum()} of {sep['intended_runs'].sum()} runs.")
    thinnest = trace[(trace["task"] == sep["intended_runs"].idxmin()) & (trace["tier"] == "intended")]
    assert thinnest["model"].nunique() == 1
    say(README, f"On one of the three that is {len(thinnest)} runs from a single model.")
    clean = sep[sep["trap_pass"] == 0]
    assert len(clean) == 2
    de = sep.loc[DE]
    fail = unc(data, DE, "trap-method runs that pass")
    spec = (f"{int(de['trap_runs'] - de['trap_pass'])} of {int(de['trap_runs'])}", pct(de["window_specificity"]),
            pct(1 - fail["ci_high"]), pct(1 - fail["ci_low"]))
    say(README, f"On two tasks, always ({clean['trap_runs'].sum()} of {clean['trap_runs'].sum()} runs). On "
                f"differential expression, only {spec[0]} runs ({spec[1]}, interval {spec[2]} to {spec[3]}).")
    by_config = trace[trace["tier"] == "trap"].groupby("task").agg(
        configs=("config", "nunique"), passing=("config", lambda c: c[trace.loc[c.index, "field_passed"]].nunique()))
    say(FINDINGS, f"| {NAMES[DE]} | {int(de['intended_pass'])} of {int(de['intended_runs'])} | {spec[0]} ({spec[1]}, interval "
                  f"{spec[2]} to {spec[3]}) | {by_config.loc[DE, 'passing']} of the {by_config.loc[DE, 'configs']} "
                  f"configurations")
    for task in (NRM, PCA):
        row = sep.loc[task]
        say(FINDINGS, f"| {NAMES[task]} | {int(row['intended_pass'])} of {int(row['intended_runs'])} | "
                      f"{int(row['trap_runs'] - row['trap_pass'])} of {int(row['trap_runs'])} | "
                      f"{by_config.loc[task, 'passing']} of {by_config.loc[task, 'configs']} |")

    # Perfect rates carry a bound counted in configurations, not an interval.
    sens = [unc(data, task, "intended-method runs that pass") for task in (DE, NRM, PCA)]
    assert all(pd.isna(u["ci_low"]) and u["estimate"] == 1.0 for u in sens)
    units = [int(u["units_with_data"]) for u in sens]
    say(FINDINGS, f"the three sensitivities are {units[0]} of {units[0]}, {units[1]} of {units[1]} and {units[2]} of "
                  f"{units[2]}, for which the exact one-sided 97.5% lower bounds are {pct(sens[0]['one_sided_bound'])}, "
                  f"{pct(sens[1]['one_sided_bound'])} and {pct(sens[2]['one_sided_bound'])}.")
    perfect = [unc(data, task, "trap-method runs that pass") for task in (NRM, PCA)]
    assert all(pd.isna(u["ci_low"]) and u["estimate"] == 0.0 for u in perfect)
    units = [int(u["units_with_data"]) for u in perfect]
    say(FINDINGS, f"The two perfect specificities are {units[0]} of {units[0]} and {units[1]} of {units[1]} "
                  f"configurations, with lower bounds of {pct(1 - perfect[0]['one_sided_bound'])} and "
                  f"{pct(1 - perfect[1]['one_sided_bound'])}.")

    # The trap that passes.
    rank = trap[(trap["task"] == DE) & (trap["trap_method"] == RANK)].iloc[0]
    passing = trace[(trace["task"] == DE) & (trace["method"] == RANK) & trace["field_passed"]]
    providers = passing["run_id"].str.split("/").str[1].nunique()
    assert len(passing) == rank["runs_passed"] and passing["config"].nunique() == rank["configurations_with_a_pass"]
    assert providers == 4 and trace["run_id"].str.split("/").str[1].nunique() == 4
    say(README, f"lands inside the pass window in {rank['runs_passed']} of {rank['runs']} runs, from "
                f"{WORDS[rank['configurations_with_a_pass']]} configurations across all four providers.")
    ttest = trap[(trap["task"] == DE) & (trap["trap_method"] == "per-cell t-test")].iloc[0]
    assert ttest["runs"] == 1 and ttest["runs_passed"] == 0
    say(FINDINGS, f"{rank['runs']} runs against {ttest['runs']}. {WORDS[rank['runs_passed']].capitalize()} of the "
                  f"{rank['runs']} passed, from {WORDS[rank['configurations_with_a_pass']]} configurations and all "
                  f"four providers.")
    # Margins of the lowest and highest pseudobulk values the task notes list, as stated in FINDINGS.
    accepted_low, accepted_high = -0.68, 0.91
    say(FINDINGS, f"run from margin {accepted_low} to +{accepted_high}")
    inside = passing[passing["margin"].between(accepted_low, accepted_high)]
    say(README, f"{WORDS[len(inside)].capitalize()} of those {WORDS[len(passing)]} sit inside the range the notes "
                f"accept")
    say(FINDINGS, f"would turn {WORDS[len(passing) - len(inside)]} of the {WORDS[len(passing)]} trap passes into "
                  f"fails. The other {WORDS[len(inside)]},")
    say(FINDINGS, f"Those {WORDS[len(inside)]} come from {WORDS[inside['config'].nunique()]} configurations.")
    assert de["trap_runs_inside_intended_span"] == 0
    say(FINDINGS, f"intended-method answers, which is {de['intended_span_in_tolerance_widths']} tolerance widths "
                  f"wide. The nearest is {de['nearest_trap_gap_in_tolerance_widths']} widths away.")

    # Z-prime, one named trap at a time.
    z = unc(data, DE, f"Z-prime, intended against: {RANK}")
    say(FINDINGS, f"| {NAMES[DE]} | {RANK} | {rank['runs']} | {rank['runs_passed']} | {z['estimate']:.2f} | "
                  f"{z['ci_low']:.2f} to {z['ci_high']:.2f} |")
    say(FINDINGS, f"rests on {int(z['positive_control_units'])} configurations for the intended control and "
                  f"{int(z['negative_control_units'])} for the trap")
    say(FINDINGS, f"Z-prime was below zero in {pct(z['share_of_resamples_below_zero'])} of the bootstrap resamples")
    say(FINDINGS, f"it stays between {z['lopo_min']:.2f} and {z['lopo_max']:.2f} when any one provider is left out")
    say(FINDINGS, f"the rank-test Z-prime is {z['estimate']:.2f}, yet no rank-test answer lies among the "
                  f"intended-method answers")
    for method in ("genes scaled, depth not regressed", "PCA with neither step"):
        row = trap[(trap["task"] == PCA) & (trap["trap_method"] == method)].iloc[0]
        zp = unc(data, PCA, f"Z-prime, intended against: {method}")
        assert pd.isna(zp["ci_low"]) and zp["interval_note"] == "fewer than 3 units"
        say(FINDINGS, f"| {NAMES[PCA]} | {method} | {row['runs']} | {row['runs_passed']} | {zp['estimate']:.2f} | "
                      f"none: the intended control comes from {WORDS[int(zp['positive_control_units'])]} "
                      f"configurations |")
    for method in ("log-normalise, then dispersion HVG", "dispersion HVG on raw counts"):
        zn = unc(data, NRM, f"Z-prime, intended against: {method}")
        assert pd.isna(zn["ci_low"]) and zn["interval_note"] == "no spread" and f"{zn['estimate']:.2f}" == "1.00"
    nearest = sep.loc[NRM, "nearest_trap_gap_in_tolerance_widths"]
    say(FINDINGS, f"The nearer trap sits only {nearest} tolerance widths from the intended answer.")

    # The normalization pass rate against the authors' prediction.
    rate = unc(data, NRM, "pass rate")
    say(FINDINGS, f"The measured rate is {pct(rate['estimate'])} ({int(rate['numerator'])} of "
                  f"{int(rate['denominator'])} runs, interval {pct(rate['ci_low'])} to {pct(rate['ci_high'])} over "
                  f"configurations)")

    # Edges, repeats, dead readouts.
    e = unc(data, "ALL", "share of verdicts that are edge-decided")
    by_task = data["edge_decided"].set_index("task")
    one_recipe = int(by_task.loc[NRM, "edge_decided"])
    clusters = data["answer_clusters"]
    assert one_recipe in set(clusters[clusters["task"] == NRM]["runs"])
    say(README, f"{edge['edge_decided_runs']} of {edge['runs']} verdicts ({pct(edge['share'])}) flip")
    say(README, f"{one_recipe} of them are one recipe that the task notes place there on purpose.")
    say(FINDINGS, f"{edge['edge_decided_runs']} of {edge['runs']} verdicts ({100 * edge['share']:.1f}%, interval "
                  f"{pct(e['ci_low'])} to {pct(e['ci_high'])}) flip")
    say(FINDINGS, f"Of the {edge['edge_decided_runs']}, {one_recipe} are one recipe on the normalization task")
    r = unc(data, "ALL", "share of task x configuration cells with split repeats")
    say(README, f"In {rpt['split']} of {rpt['cells']} pairs ({pct(rpt['split_share'])}) the three repeats did not "
                f"agree.")
    say(FINDINGS, f"| Split | {rpt['split']} ({pct(rpt['split_share'])}, interval {pct(r['ci_low'])} to "
                  f"{pct(r['ci_high'])}) |")
    per_task = data["repeatability"].set_index("task").drop(index="ALL")
    low, high = per_task["split_share"].idxmin(), per_task["split_share"].idxmax()
    assert (low, high) == (PCA, CLUSTERING)
    say(FINDINGS, f"from {pct(per_task.loc[low, 'split_share'])} ({int(per_task.loc[low, 'split'])} of "
                  f"{int(per_task.loc[low, 'cells'])} cells, PCA preprocessing) to "
                  f"{pct(per_task.loc[high, 'split_share'])} ({int(per_task.loc[high, 'split'])} of "
                  f"{int(per_task.loc[high, 'cells'])}, clustering)")
    say(README, f"{dead['dead_fields']} of {dead['fields']} graded fields are passed by at least 95% of runs.")
    c = s["clusters"]
    say(FINDINGS, f"{pct(c['live_field_share'])} of answers ({c['live_field_answers_in_clusters']} of "
                  f"{c['live_field_answers']})")

    # Leaderboard.
    same, others = board["others_not_told_apart_from_the_leader"], board["others"]
    say(README, f"On the published {board['tasks']}-task table, {same} of the {others} other configurations cannot "
                f"be told apart from the leader by an unpaired test of the difference.")
    say(FINDINGS, f"Of its {board['configurations']} configurations, {board['with_interval']} have an interval.")
    say(FINDINGS, f"Median half-width: {board['median_half_width_points']:.1f} percentage points.")
    say(FINDINGS, f"{same} of the other {others} configurations cannot be told apart from the leader, and "
                  f"{board['pairs_not_told_apart']} of {board['pairs']} pairs cannot be told apart from each other.")
    say(FINDINGS, f"gives {board['others_overlapping_the_leader']} of {others} and {board['pairs_overlapping']} of "
                  f"{board['pairs']}.")
    say(FINDINGS, f"median of {pct(board['implied_split_share_median'])}, range "
                  f"{pct(board['implied_split_share_min'])} to {pct(board['implied_split_share_max'])}")
    say(FINDINGS, f"about {pct(board['implied_single_rerun_disagreement_median'])}, or one task in seven")

    # Tracing and its validation.
    say(README, f"Of {tracing['runs_traced']} traced runs, {tracing['traced_from_printed_value']} are labelled from "
                f"the printed value, {tracing['traced_by_fallback']} from the last classifiable step and "
                f"{tracing['labels_set_by_reading']} by reading.")
    ratings = data["ratings"]
    n_ratings = int(ratings["rater_a"].notna().sum() + ratings["rater_b"].notna().sum())
    say(README, f"re-labelled all {len(ratings)} traced runs from the raw transcripts: {n_ratings} ratings")
    say(FINDINGS, f"That is {n_ratings} ratings, and every one agreed with the tool: {len(ratings)} of "
                  f"{len(ratings)}.")
    say(FINDINGS, f"{WORDS[tracing['ran_intended_but_submitted_other']].capitalize()} traced runs executed an "
                  f"intended method")
    return out


def test_every_headline_number_matches_the_tables(data):
    documents = {}
    missing = []
    for document, sentence in claims(data):
        body = documents.setdefault(document, text(document))
        if sentence not in body:
            missing.append(f"{document}: {sentence}")
    assert not missing, "not found word for word:\n" + "\n".join(missing)


def test_blind_ratings_agree_with_the_published_labels(data):
    """Every rating equals the adjudicated label, which is what the documents claim."""
    ratings = data["ratings"]
    assert (ratings["rater_a"] == ratings["adjudicated_method"]).all()
    second = ratings[ratings["rater_b"].notna()]
    assert (second["rater_b"] == second["adjudicated_method"]).all()
    assert len(ratings) == data["summary"]["method_tracing"]["runs_traced"]
