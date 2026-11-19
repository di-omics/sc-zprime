"""The family numbers in the documents must match the committed tables.

Same idea as test_docs_numbers.py: each check rebuilds a sentence or a table
row from `results/family`, `results/variantbench`, `results/txbench-pp` or
`validation/answer_recovery.csv` and requires it to appear, word for word, in
the document. These checks read only files in this repository.
"""

import json
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results"
README, FAMILY = "README.md", "docs/FAMILY.md"
REGRADED = ("variantbench", "txbench-pp")
VERDICT_BENCHES = ("scbench", "spatialbench")


def text(relative):
    return " ".join((ROOT / relative).read_text().split())


@pytest.fixture(scope="module")
def data():
    d = {"inventory": pd.read_csv(RES / "family" / "inventory.csv").astype(object).fillna("").set_index("benchmark"),
         "family": json.loads((RES / "family" / "summary.json").read_text()),
         "modes": pd.read_csv(RES / "family" / "failure_modes.csv"),
         "recovery": pd.read_csv(ROOT / "validation" / "answer_recovery.csv")}
    for name in REGRADED:
        d[name] = json.loads((RES / name / "summary.json").read_text())
        d[name + ":tasks"] = pd.read_csv(RES / name / "tasks.csv")
        d[name + ":runs"] = pd.read_csv(RES / name / "regrade_runs.csv")
        d[name + ":fields"] = pd.read_csv(RES / name / "regrade_fields.csv").astype(object).fillna("")
    return d


def claims(data):
    inv, fam, modes, rec = data["inventory"], data["family"], data["modes"], data["recovery"]
    v, t = data["variantbench"], data["txbench-pp"]
    out = []

    def say(document, sentence):
        out.append((document, sentence))

    # The inventory table, row by row.
    for name, row in inv.iterrows():
        repeats = str(int(row["max_repeats"])) if int(row["transcripts"]) else "n/a"
        say(FAMILY, f"| {name} | {int(row['public_tasks'])} | {int(row['tasks_with_a_public_grader'])} | "
                    f"{int(row['transcripts'])} | {int(row['runs_with_a_published_verdict'])} | {repeats} |")
    say(FAMILY, f"In all: {fam['benchmarks']} repositories, {fam['public_tasks']} public tasks, {fam['transcripts']} transcripts.")
    say(README, f"for {fam['benchmarks']} of their repositories ({fam['public_tasks']} public tasks, {fam['transcripts']} transcripts)")
    assert fam["can_reproduce_verdicts"] == list(VERDICT_BENCHES) == fam["can_measure_repeatability"]
    assert fam["can_grade_from_transcripts_only"] == ["txbench-pp", "variantbench"]
    say(FAMILY, f"{len(fam['can_reproduce_verdicts'])} repositories publish what it takes to reproduce a verdict")
    say(FAMILY, f"{len(fam['can_grade_from_transcripts_only'])} more publish a grader config for every public task")
    graders_no_runs = [n for n, r in inv.iterrows() if int(r["tasks_with_a_public_grader"]) == int(r["public_tasks"]) and not int(r["transcripts"])]
    assert graders_no_runs == ["metagenomicsbench", "oncologybench", "rarediseasebench"]
    say(FAMILY, f"{len(graders_no_runs)} publish a grader for every public task and no runs: metagenomicsbench, oncologybench and rarediseasebench.")
    say(README, f"- {len(graders_no_runs)} publish graders and no runs, so there is nothing to grade.")
    say(FAMILY, f"{fam['publish_no_grader']} repositories publish no grader for their public tasks.")
    say(README, f"- {fam['publish_no_grader']} publish no grader for their public tasks.")
    long = inv.loc["spatialbench-long"]
    assert long["runs_with_a_published_verdict"] > 0 and long["tasks_with_a_public_grader"] == 0
    declare = fam["benchmarks_that_withhold_the_grader_and_declare_its_type"]
    say(FAMILY, f"{len(declare)} of the {fam['publish_no_grader']} that publish no grader say so in a `data_availability` field")
    say(FAMILY, f"The other {fam['publish_no_grader'] - len(declare)} (epibench, scbench-long, spatialbench-long) do not say.")
    say(README, f"{len(declare)} say in their task files that even the public tasks' graders are withheld")

    # How the repositories differ.
    numeric_only = int(inv.loc[list(VERDICT_BENCHES), "public_tasks"].sum())
    assert fam["benchmarks_that_use_only_the_numeric_grader"] == list(VERDICT_BENCHES)
    say(FAMILY, f"All {numeric_only} public tasks of scbench and spatialbench use the numeric tolerance grader alone.")
    graders = pd.concat([data[n + ":tasks"]["grader"] for n in REGRADED])
    plain, both = int((graders == "numeric_tolerance").sum()), len(graders)
    mixed = int(((graders != "numeric_tolerance") & graders.str.contains("numeric_tolerance")).sum())
    say(FAMILY, f"In variantbench and txbench-pp, {plain} of {both} public tasks use it alone. The other {both - plain} use")
    say(FAMILY, f"and {mixed} of the {both - plain} include a numeric tolerance grader among them.")
    rubric = [name for name, row in inv.iterrows() if "rubric" in row["grader_kinds"]]
    assert rubric == ["oncologybench", "rarediseasebench"]
    say(FAMILY, f"{len(rubric)} repositories with public graders use rubrics (oncologybench, rarediseasebench).")
    say(FAMILY, f"{len(declare)} repositories withhold the grader and state its type in the task metadata")
    assert int(inv.loc[list(VERDICT_BENCHES), "tasks_with_a_failure_mode_label"].sum()) == 0
    assert int(inv.loc[list(VERDICT_BENCHES), "tasks_with_design_notes"].sum()) == numeric_only
    assert all(int(inv.loc[n, "tasks_with_design_notes"]) == int(inv.loc[n, "public_tasks"]) for n in REGRADED)
    say(FAMILY, f"The {numeric_only} scbench and spatialbench tasks describe their traps in prose design notes")
    assert fam["failure_mode_taxonomy_versions"] == ["v1.1.0", "v1.2.0"]
    say(FAMILY, f"{fam['tasks_with_a_failure_mode_label']} of the {fam['public_tasks']} public tasks, in "
                f"{fam['benchmarks_with_a_failure_mode_label']} repositories, carry a label from a versioned taxonomy "
                f"(v1.1.0 and v1.2.0) with {fam['failure_mode_categories']} top-level categories among them.")
    say(README, f"({fam['tasks_with_a_failure_mode_label']} of {fam['public_tasks']} public tasks)")
    top = {m["failure_mode"]: m["tasks"] for m in fam["most_common_failure_modes"]}
    say(FAMILY, f"metric or statistic mismatch ({top['metric_statistic_mismatch']} tasks), biological interpretation "
                f"({top['biological_interpretation']}) and subset, scope or compartment ({top['subset_scope_compartment']}).")
    assert int(modes.groupby("failure_mode")["tasks"].sum().max()) == top["metric_statistic_mismatch"]

    def harness(name):
        return {part.rsplit(" ", 1)[0]: int(part.rsplit(" ", 1)[1]) for part in inv.loc[name, "harnesses"].split("; ") if part}

    say(FAMILY, f"{harness('scbench')['mini-swe-agent']} of the {int(inv.loc['scbench', 'transcripts'])} scbench runs and "
                f"{harness('spatialbench')['mini-swe-agent']} of the {int(inv.loc['spatialbench', 'transcripts'])} spatialbench runs used mini-swe-agent.")
    others = [name for name in inv.index if name not in VERDICT_BENCHES and inv.loc[name, "harnesses"]]
    pi = sum(harness(n).get("pi", 0) for n in others)
    total = sum(sum(harness(n).values()) for n in others)
    msa = sum(harness(n).get("mini-swe-agent", 0) for n in others)
    vendor = sum(harness(n).get("claude-code", 0) + harness(n).get("openai-codex", 0) for n in others)
    assert pi + msa + vendor == total
    say(FAMILY, f"In the {len(others)} other repositories with transcripts, {pi} of {total} runs used pi, {vendor} used the "
                f"vendors' own command lines (claude-code, openai-codex) and {msa} used mini-swe-agent.")
    sb = inv.loc["spatialbench"]
    assert (sb["eval_tool_versions"], inv.loc["scbench", "eval_tool_versions"],
            inv.loc["spatialbench-long", "eval_tool_versions"]) == ("0.3.7", "0.3.8; 0.3.9", "0.3.14")
    stamped, results = int(sb["result_files_with_a_tool_version"]), int(sb["runs_with_a_published_verdict"])
    say(FAMILY, f"0.3.7 on {stamped} of the {results} in spatialbench (the other {results - stamped} carry none), "
                f"0.3.8 and 0.3.9 in scbench, 0.3.14 in spatialbench-long.")

    # Answer recovery, measured where the answer is published.
    runs, found = int(rec["runs"].sum()), int(rec["answers_recovered"].sum())
    equal = int(rec["equal_to_the_published_answer"].sum())
    flagged, flagged_equal = int(rec["flagged_written_again_unseen"].sum()), int(rec["equal_among_flagged"].sum())
    say(FAMILY, f"On those {runs} runs the recovery finds an answer for {found}, and {equal} of the {found} equal the "
                f"published answer exactly. The {runs - found} not recovered")
    say(FAMILY, f"{flagged} recovered answers carry a flag that the answer file was written again without showing what was "
                f"written, and only {flagged_equal} of those {flagged} are right. So of the {found - flagged} recovered "
                f"answers without the flag, {equal - flagged_equal} were right.")
    by_harness = rec.groupby("harness")[["runs", "answers_recovered", "equal_to_the_published_answer"]].sum()
    msa_runs, pi_runs = int(by_harness.loc["mini-swe-agent", "runs"]), int(by_harness.loc["pi", "runs"])
    here = {k: v[k] + t[k] for k in ("transcripts", "answers_recovered")}
    pi_here = v["transcripts_by_harness"].get("pi", 0) + t["transcripts_by_harness"].get("pi", 0)
    say(FAMILY, f"{msa_runs} of its {runs} runs used mini-swe-agent and {pi_runs} used pi, while {pi_here} of the "
                f"{here['transcripts']} runs graded here used pi.")
    assert int(by_harness.loc["pi", "answers_recovered"]) == int(by_harness.loc["pi", "equal_to_the_published_answer"]) == pi_runs
    say(FAMILY, f"On those {pi_runs} pi runs the recovery found all {pi_runs} answers exactly")
    say(FAMILY, f"In the test set {int(rec['printed'].sum())} of the {found} answers were read from printed output and "
                f"{int(rec['written'].sum())} from a write to the answer file.")
    src = {k: v["answer_sources"].get(k, 0) + t["answer_sources"].get(k, 0) for k in ("printed", "written", "tagged", "none")}
    say(FAMILY, f"Here {src['printed']} of {here['answers_recovered']} were read from printed output, {src['written']} from "
                f"a write and {src['tagged']} from a tagged message.")
    again = v["recovered_answers_where_the_file_was_written_again_unseen"] + t["recovered_answers_where_the_file_was_written_again_unseen"]
    assert again == 0
    say(FAMILY, f"None of the {here['answers_recovered']} answers recovered here carries the written-again flag.")
    checked = int(rec.loc[rec["benchmark"].isin(VERDICT_BENCHES), "runs"].sum())
    say(FAMILY, f"The numeric grader is checked against {checked} published verdicts.")
    say(README, f"on {runs} runs it finds {found} answers, and {equal} of those equal the published answer exactly.")
    say(FAMILY, f"Recovery on runs like these is measured on {pi_runs} pi runs only.")
    say(README, f"{pi_here} of the {here['transcripts']} used pi, which the test covers with {pi_runs} runs.")
    say(FAMILY, f"{pi_here} of the {here['transcripts']} runs here are from pi")

    # The first grading.
    for row, key in (("Public tasks, all gradable", "tasks"), ("Transcripts", "transcripts"),
                     ("Configurations, 1 repeat each", "configurations"), ("Answers recovered", "answers_recovered"),
                     ("Recovered answers that pass", "runs_passed"), ("Tasks that no recovered answer passed", "tasks_no_run_passed"),
                     ("Graded fields", "fields_graded"), ("Fields that fail", "fields_failed")):
        say(FAMILY, f"| {row} | {v[key]} | {t[key]} |")
    for s in (v, t):
        assert s["tasks"] == s["tasks_gradable"] and s["max_repeats_per_configuration"] == 1
        assert s["runs_with_a_published_verdict"] == 0 and s["runs_failed_on_form_alone"] == 0
    say(README, f"{v['answers_recovered']} of {v['transcripts']} and {t['answers_recovered']} of {t['transcripts']} answers are "
                f"recovered, and {v['runs_passed']} and {t['runs_passed']} of them pass.")
    lists = data["variantbench:tasks"]
    on_lists = int(lists.loc[lists["grader"].str.startswith("list_of"), "passed"].sum())
    assert int(lists["grader"].str.startswith("list_of").sum()) == 2
    for document in (FAMILY, README):
        say(document, f"{on_lists} of the {v['runs_passed']} VariantBench passes")
    say(FAMILY, "2 VariantBench tasks give a list of graders in place of one.")
    failed = v["fields_failed"] + t["fields_failed"]
    by_value = v["failed_fields_by_reason"].get("value", 0) + t["failed_fields_by_reason"].get("value", 0)
    form = v["failed_fields_a_change_of_form_would_pass"] + t["failed_fields_a_change_of_form_would_pass"]
    assert failed - by_value == form
    fields = pd.concat([data[n + ":fields"] for n in REGRADED])
    assert set(fields.loc[fields["near_miss"] != "", "near_miss"]) == {"number_in_text"}
    assert fields.loc[fields["near_miss"] != "", ["task", "config"]].drop_duplicates().shape[0] == 1
    assert "margin" not in fields.columns
    say(FAMILY, f"Of the {failed} failing fields, {by_value} fail on value and {form} on form. The {form} are 1 run")
    say(README, f"Of the {failed} fields that fail, {by_value} fail on value and {form} on form.")
    recovered = here["answers_recovered"]
    only = v["recovered_answers_that_are_the_only_one_shown"] + t["recovered_answers_that_are_the_only_one_shown"]
    depends = v["recovered_answers_where_the_verdict_depends_on_which"] + t["recovered_answers_where_the_verdict_depends_on_which"]
    say(FAMILY, f"{only} of the {recovered} recovered answers are the only answer object their transcript shows. In the other "
                f"{recovered - only} the transcript shows several, and in {depends} of those they would not all get the same verdict.")
    transcripts = here["transcripts"]
    say(FAMILY, f"No published verdict exists for these {transcripts} runs.")
    say(FAMILY, f"{transcripts - recovered} of the {transcripts} answers were not recovered")
    labels = data["txbench-pp:tasks"]["failure_modes"].astype(str).str.split("; ").map(len)
    pairs = int(labels.sum())
    answers_rows = sum(m["answers_recovered"] for m in t["by_failure_mode"])
    say(FAMILY, f"All {t['tasks']} TxBench-PP tasks carry labels, and {int((labels > 1).sum())} carry more than 1.")
    say(FAMILY, f"they add up to {pairs} tasks and {answers_rows} answers, from {t['tasks']} tasks and {t['answers_recovered']} answers.")
    assert pairs == sum(m["tasks"] for m in t["by_failure_mode"])
    for mode in t["by_failure_mode"]:
        say(FAMILY, f"| {mode['failure_mode']} | {mode['tasks']} | {mode['answers_recovered']} | {mode['passed']} |")
    marker = lists[lists["grader"] == "marker_gene_precision_recall"]
    assert len(marker) == 2 and int(marker["answers_recovered"].sum()) == 4 and int(marker["passed"].sum()) == 0
    say(FAMILY, f"The {len(marker)} neoantigen tasks set a much higher bar for recall than for precision")
    say(FAMILY, f"None of the {int(marker['answers_recovered'].sum())} recovered answers on those tasks passes")
    assert "score_minus_threshold" not in fields.columns and "score_vs_threshold" in fields.columns
    inv = data["inventory"]
    say(FAMILY, f"and all {len(inv)} commits are dated November 2026")
    return out


def test_every_family_number_matches_the_tables(data):
    documents, missing = {}, []
    for document, sentence in claims(data):
        body = documents.setdefault(document, text(document))
        if sentence not in body:
            missing.append(f"{document}: {sentence}")
    assert not missing, "not found word for word:\n" + "\n".join(missing)
