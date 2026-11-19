"""The SpatialBench numbers in the documents must match the committed tables.

Same idea as test_docs_numbers.py: each check rebuilds a sentence from
`results/spatialbench` (or from the closing-message count in `validation/`)
and requires it to appear, word for word, in the document.

These checks need no benchmark data: they read only files in this repository.
"""

import json
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results" / "spatialbench"
README, FINDINGS = "README.md", "docs/SPATIALBENCH.md"
DONOR_TASKS = ["NORM01_batch_correction", "DR01_batch_confounded_clustering"]


def text(relative):
    return " ".join((ROOT / relative).read_text().split())


def pct(share):
    return f"{round(100 * float(share))}%"


@pytest.fixture(scope="module")
def data():
    d = {name: pd.read_csv(RES / f"{name}.csv") for name in
         ["method_separation", "method_trace", "method_by_trap", "repeatability", "tasks", "readouts", "edge_decided",
          "repeat_cells"]}
    d["summary"] = json.loads((RES / "summary.json").read_text())
    d["closing"] = pd.read_csv(ROOT / "validation" / "spatialbench_closing_messages.csv").set_index("task")
    sc = ROOT / "results" / "scbench"
    d["sc_repeatability"] = pd.read_csv(sc / "repeatability.csv")
    d["sc_edge"] = pd.read_csv(sc / "edge_decided.csv")
    return d


def some_pass(repeatability, edge):
    """Edge and split counts over the tasks that at least 1 run passed."""
    rep = repeatability[repeatability["task"] != "ALL"]
    tasks = rep[rep["all_fail"] < rep["cells"]]["task"]
    e = edge[edge["task"].isin(tasks)]
    r = rep[rep["task"].isin(tasks)]
    return len(tasks), int(e["edge_decided"].sum()), int(e["runs"].sum()), int(r["split"].sum()), int(r["cells"].sum())


def claims(data):
    s, sep, trace, closing = data["summary"], data["method_separation"], data["method_trace"], data["closing"]
    rep, edge, rpt, dead, board, tracing = (s["reproduce"], s["edge"], s["repeatability"], s["readouts"],
                                            s["leaderboard"], s["method_tracing"])
    out = []

    def say(document, sentence):
        out.append((document, sentence))

    assert s["upstream_commit"].startswith("baa9841") and not s["skipped"]
    say(README, f"runs for {rep['tasks']} example tasks")
    say(FINDINGS, f"| Tasks | {rep['tasks']} public example tasks,")
    say(FINDINGS, f"| Runs | {rep['runs']} graded runs with full transcripts |")
    say(FINDINGS, f"| Configurations | {rep['configurations']} model and harness pairs,")
    say(FINDINGS, f"| Cells | {rpt['cells']} task and configuration pairs, each with 3 repeats |")
    say(FINDINGS, f"numeric tolerance on all {int((data['tasks']['grader_type'] == 'numeric_tolerance').sum())} tasks")

    say(README, f"An independent grader agrees on {rep['runs_agree']} of {rep['runs']} runs.")
    say(FINDINGS, f"agrees on {rep['runs_agree']} of {rep['runs']} run verdicts and {rep['fields_agree']} of "
                  f"{rep['fields']} field-level verdicts.")
    passes = round(s["pass_rate"] * rep["runs"])
    never = int((data["repeatability"].query("task != 'ALL'")["all_fail"] == 16).sum())
    say(FINDINGS, f"{passes} of {rep['runs']} ({pct(s['pass_rate'])}). {never} of the {rep['tasks']} tasks were not "
                  f"passed by any run.")
    for document in (README, FINDINGS):
        say(document, f"{edge['edge_decided_runs']} of {edge['runs']} verdicts ({pct(edge['share'])}) flip if "
                      f"every tolerance is made 20% tighter or 25% wider.")
        say(document, f"In {rpt['split']} of {rpt['cells']} pairs ({pct(rpt['split_share'])}) the 3 repeats did "
                      f"not get the same verdict.")
    ro = data["readouts"]
    exact, pinned = int((ro["kind"] == "exact").sum()), int(ro["lower_edge_at_zero"].sum())
    say(FINDINGS, f"{exact} of the {len(ro)} graded fields are exact-match and cannot flip. On {pinned} whose lower edge "
                  f"is at or below zero, only the upper edge moves.")
    cells = data["repeat_cells"]
    say(FINDINGS, f"In {int((~cells['identical_answers']).sum())} of {len(cells)} they did not submit the same answer.")
    d = ro[ro["dead"]]
    d_exact = int((d["kind"] == "exact").sum())
    d_pinned = int(((d["kind"] != "exact") & d["lower_edge_at_zero"]).sum())
    say(FINDINGS, f"{dead['dead_fields']} of {dead['fields']} graded fields are passed by at least 95% of runs: {d_exact} "
                  f"exact-match answers that nearly every run got right, {d_pinned} ceiling checks whose lower edge is at "
                  f"or below zero, and {len(d) - d_exact - d_pinned} two-sided windows.")
    say(FINDINGS, f"On the {board['tasks']}-task table in the repository, {board['others_not_told_apart_from_the_leader']} "
                  f"of the {board['others']} other configurations cannot be told apart from the leader by an unpaired "
                  f"test at the 5% level, with no adjustment for {board['others']} comparisons.")
    n, e, er, sp, sc = some_pass(data["repeatability"], data["edge_decided"])
    n2, e2, er2, sp2, sc2 = some_pass(data["sc_repeatability"], data["sc_edge"])
    assert never == rep["tasks"] - n and n2 == 6
    say(FINDINGS, f"because {never} of the {rep['tasks']} tasks were failed by every run. On the {n} tasks that at least 1 "
                  f"run passed, {sp} of {sc} pairs split ({pct(sp / sc)}), against {sp2} of {sc2} on the scBench sample "
                  f"({pct(sp2 / sc2)}).")
    say(FINDINGS, f"on those {n} tasks {e} of {er} verdicts flip ({pct(e / er)}), against {e2} of {er2} ({pct(e2 / er2)}) on scBench.")

    # The three batch-correction tasks.
    runs, intended = int(sep["runs"].sum()), int(sep["intended_runs"].sum())
    traps, trap_pass, other = int(sep["trap_runs"].sum()), int(sep["trap_pass"].sum()), int(sep["other_runs"].sum())
    all_pass = int(sep["passes"].sum())
    other_pass = all_pass - trap_pass
    assert len(sep) == 3 and tracing["unresolved"] == 0
    say(README, f"Not measurable on the {len(sep)} tasks traced: {intended} of {runs} runs submitted an answer from it.")
    ovary_task = sep[~sep["task"].isin(DONOR_TASKS)].iloc[0]
    assert trap_pass == 1 and int(sep.set_index("task").loc[DONOR_TASKS, "trap_pass"].sum()) == 0
    assert ovary_task["task"].startswith("curio_ovary") and int(ovary_task["trap_pass"]) == 1
    say(README, f"Almost always: {traps - trap_pass} of {traps} runs fail. The {trap_pass} pass is on the ovary task and "
                f"is not a correction.")
    say(README, f"{len(sep)} of the {rep['tasks']} tasks test one decision")
    say(README, f"{traps} of {runs} runs clustered with no sample handling and {other} chose variable genes per sample")
    say(README, f"show that an uncorrected pipeline fails ({runs - all_pass} of {runs} runs).")
    say(FINDINGS, f"| A batch-correction method before clustering (the intended method) | {intended} of {runs} | n/a |")
    say(FINDINGS, f"| No sample handling (the notes' first named trap) | {traps} of {runs} | {trap_pass} |")
    say(FINDINGS, f"| Variable genes chosen per sample, nothing else corrected | {other} of {runs} | {other_pass} |")
    assert other - other_pass == 1 and intended == 0
    say(FINDINGS, f"Of the {traps} runs with no sample handling, {traps - trap_pass} fail. Of the {other} that chose "
                  f"variable genes per sample, {other - other_pass} fails. No run in either group submitted a corrected answer.")
    # The donor-share field keeps its margins as numbers. The cluster-count field is a count with a small
    # tolerance, so the tables give each of its answers a zone and nothing finer.
    share, count = (trace[trace["task"] == task]["margin"] for task in DONOR_TASKS)
    lowest = pd.to_numeric(share).min()
    assert lowest > 1 and set(count) == {"above, clear of the edge"}
    say(FINDINGS, f"On the donor-share task every answer sits at least {lowest:.1f} tolerance widths above the reference.")
    say(FINDINGS, "On the cluster-count task every answer is above the window and clear of its edge")
    say(FINDINGS, f"The {len(sep)} windows reject {runs - all_pass} of the {runs} uncorrected answers")
    printed = int(trace["source"].isin(["printed", "printed_by_script"]).sum())
    fallback = trace[trace["source"] == "fallback"]
    on_count_task = int((fallback["task"] == DONOR_TASKS[1]).sum())
    assert on_count_task == int((trace["task"] == DONOR_TASKS[1]).sum())
    say(FINDINGS, f"For {printed} runs that is the step that printed the submitted number. For {len(fallback)}, among "
                  f"them all {on_count_task} on the cluster-count task, it is the last classifiable step")
    say(FINDINGS, f"{tracing['labels_set_by_reading']} were labelled by reading.")
    say(FINDINGS, f"and the {tracing['labels_set_by_reading']} the rules could not label, whose labels were set by reading")
    say(FINDINGS, f"the only corrected answers anywhere in the {runs} transcripts")
    assert tracing["ran_intended_but_submitted_other"] == 2
    say(FINDINGS, "**2 runs ran a correction, then submitted the uncorrected number.**")
    say(README, f"Separately, {tracing['ran_intended_but_submitted_other']} runs ran a correction method and then "
                f"submitted the uncorrected number.")
    say(README, f"Of the {runs} traced SpatialBench runs, {printed}, {len(fallback)} and {tracing['labels_set_by_reading']}.")
    say(FINDINGS, f"All {on_count_task} labels there come from the last classifiable step.")
    donor = sep.set_index("task").loc[DONOR_TASKS]
    ovary = sep[~sep["task"].isin(DONOR_TASKS)].iloc[0]
    assert int(donor["passes"].sum()) == 0
    say(FINDINGS, f"The 2 donor tasks failed all {int(donor['runs'].sum())} of them, and the ovary task failed "
                  f"{int(ovary['runs'] - ovary['passes'])} of {int(ovary['runs'])}.")
    say(FINDINGS, f"{len(sep)} of {rep['tasks']} tasks are traced.")

    # Last stored messages (scripts/closing_messages.py).
    a, b = closing.loc[DONOR_TASKS[0]], closing.loc[DONOR_TASKS[1]]
    named = int(a["last_text_names_a_batch_effect"] + b["last_text_names_a_batch_effect"])
    both = int(a["runs"] + b["runs"])

    def from_provider(row, provider, column):
        counts = dict(part.rsplit(" ", 1) for part in str(row[column]).split("; ") if part)
        return int(counts.get(provider, 0))

    def count(provider, column):
        return sum(from_provider(row, provider, column) for row in (a, b))

    anthropic = count("anthropic", "of_those_by_provider")
    providers = sorted({part.rsplit(" ", 1)[0] for row in (a, b) for part in str(row["runs_by_provider"]).split("; ")})
    all_runs = {name: count(name, "runs_by_provider") for name in providers}
    with_text = {name: count(name, "with_any_assistant_text_by_provider") for name in providers}
    others = [name for name in providers if name != "anthropic"]
    assert sum(all_runs.values()) == both and a["runs_with_any_assistant_text"] == b["runs_with_any_assistant_text"]
    assert all_runs["anthropic"] == with_text["anthropic"], "the page says every Anthropic run stores assistant text"
    say(FINDINGS, f"the last stored message of {a['last_text_names_a_batch_effect']} of {a['runs']} runs on one and "
                  f"{b['last_text_names_a_batch_effect']} of {b['runs']} on the other names a batch effect")
    stored = int(a["runs_with_any_assistant_text"] + b["runs_with_any_assistant_text"])
    assert stored == sum(with_text.values()) and anthropic <= named
    say(FINDINGS, f"{stored} of the {both} runs store any assistant text")

    def medians(row):
        return [int(part.rsplit(" ", 1)[1]) for part in str(row["median_chars_of_last_text_by_provider"]).split("; ")]

    lengths = medians(a) + medians(b)
    assert min(lengths) < 100 and max(lengths) > 700
    say(FINDINGS, "ranges from under 100 to over 700 characters by provider")
    say(FINDINGS, f"so the {b['last_text_names_a_batch_effect']} matches on it are not an echo of the prompt")
    say(README, "They have not been through the blind re-rating described below, and no person has checked them.")
    say(FINDINGS, f"By a keyword count, {named} of the {both} runs on the donor tasks name a batch effect in their last "
                  f"stored message, and all {named} submitted an uncorrected number.")
    assert intended == 0, "every run on the donor tasks submitted an uncorrected number"
    say(README, f"the last stored message of {named} of {both} runs names one: {a['last_text_names_a_batch_effect']} on a "
                f"task whose prompt explains how to read the number, and {b['last_text_names_a_batch_effect']} on a task "
                f"whose prompt does not mention batch effects.")
    return out


def test_every_spatialbench_number_matches_the_tables(data):
    documents, missing = {}, []
    for document, sentence in claims(data):
        body = documents.setdefault(document, text(document))
        if sentence not in body:
            missing.append(f"{document}: {sentence}")
    assert not missing, "not found word for word:\n" + "\n".join(missing)


def test_closing_message_count_regenerates_from_the_checkout(data):
    import importlib.util
    import os

    upstream = Path(os.environ.get("SC_ZPRIME_UPSTREAM", ROOT.parent / "upstream")) / "spatialbench"
    if not (upstream / "trajectories").exists():
        pytest.skip("no SpatialBench checkout")
    spec = importlib.util.spec_from_file_location("closing_messages", ROOT / "scripts" / "closing_messages.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    fresh = pd.DataFrame(module.count(upstream)).set_index("task")
    assert fresh.astype(str).equals(data["closing"].loc[fresh.index, fresh.columns].astype(str))
