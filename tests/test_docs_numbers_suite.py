"""The numbers in docs/SUITE.md must match the committed tables.

Same idea as test_docs_numbers_family.py: each check rebuilds a table row or
a sentence from `results/suite` (the snapshot of benchmarks.bio written by
`scripts/site_boards.py`) and `results/family`, and requires it to appear,
word for word, in the document. These checks read only files in this
repository. The live site is never contacted.
"""

import json
import re
import shutil
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results"
README, SUITE = "README.md", "docs/SUITE.md"
LEVELS = ("validates the public runs", "grades the public runs once", "counts what is public")


def text(relative):
    return " ".join((ROOT / relative).read_text().split())


@pytest.fixture(scope="module")
def data():
    return {"boards": pd.read_csv(RES / "suite" / "boards.csv").astype(object).fillna(""),
            "site": json.loads((RES / "suite" / "site.json").read_text()),
            "inventory": pd.read_csv(RES / "family" / "inventory.csv").astype(object).fillna("").set_index("benchmark"),
            "family": json.loads((RES / "family" / "summary.json").read_text())}


def level(row):
    def yes(value):
        return str(value).strip().lower() == "true"

    return 0 if yes(row["can_reproduce_verdicts"]) else 1 if yes(row["can_grade_from_transcripts"]) else 2


def listed(names):
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


def claims(data):
    boards, site, inv, fam = data["boards"], data["site"], data["inventory"], data["family"]
    n = len(boards)
    out = []

    def say(document, sentence):
        out.append((document, sentence))

    # Every board is matched to exactly 1 repository of the inventory, and none is a biosecurity board.
    assert sorted(boards["repository"]) == sorted(inv.index) and n == site["boards_read"] == fam["benchmarks"]
    assert not boards["board"].str.contains("biosec", case=False).any()
    assert n + site["biosecurity_boards_left_out"] == site["leaderboards"]
    assert site["capability_benchmarks"] + site["scored_apart_as_safeguards"] == site["leaderboards"]
    evaluations = int(boards["evaluations"].astype(int).sum())
    assert evaluations == site["evaluations_on_the_boards_read"]

    # Section 1: the table, row by row, and its totals.
    at = [0, 0, 0]
    for _, b in boards.iterrows():
        row = inv.loc[b["repository"]]
        at[level(row)] += 1
        say(SUITE, f"| [{b['board']}]({b['board_page']}) | {b['area']} | {b['horizon']} | {int(b['evaluations'])} | "
                   f"[{b['repository']}](https://github.com/latchbio/{b['repository']}) | {int(row['public_tasks'])} | "
                   f"{int(row['tasks_with_a_public_grader'])} | {int(row['runs_with_a_published_verdict'])} | "
                   f"{LEVELS[level(row)]} |")
    assert at[0] == len(fam["can_reproduce_verdicts"]) and at[1] == len(fam["can_grade_from_transcripts_only"])
    say(SUITE, f"lists {site['leaderboards']} boards.")
    say(SUITE, f"its data date of {site['data_updated']}")
    say(SUITE, f"the {n} repositories at the commits pinned")
    say(SUITE, f"The {site['biosecurity_boards_left_out']} biosecurity boards are left out on purpose")
    say(SUITE, f"In all: {n} boards outside biosecurity, with {evaluations} evaluations in their current sets. Their "
               f"repositories publish {fam['public_tasks']} tasks. This tool validates the public runs of {at[0]} boards, "
               f"grades the public runs of {at[1]} more once, and counts what is public for the other {at[2]}.")
    kept_out = int(re.search(r"and (\d+) \(oncologybench", text("docs/FAMILY.md")).group(1))
    say(SUITE, f"and {kept_out} repositories say theirs are not part of the benchmark")
    say(README, f"these are {n} of the {site['leaderboards']} boards: all but the {site['biosecurity_boards_left_out']} "
                f"biosecurity boards, which are left out on purpose. The {n} boards score {evaluations} evaluations in "
                f"their current sets. Their repositories publish {fam['public_tasks']} public tasks on GitHub, as examples "
                "that are not always drawn from the board's set.")

    # Section 2: boards whose current set is not the one in the original study.
    moved = boards[(boards["original_study_evaluations"] != "")]
    moved = moved[moved["original_study_evaluations"].astype(int) != moved["evaluations"].astype(int)]
    assert len(moved) == site["boards_read_whose_current_set_differs_from_the_original_study"]
    say(SUITE, f"{len(moved)} of the {n} board pages say their current evaluation set is not the one in the original study:")
    for _, b in moved.iterrows():
        say(SUITE, f"| {b['board']} | {int(b['original_study_evaluations'])} | {int(b['evaluations'])} |")
    size = dict(zip(boards["board"], boards["evaluations"].astype(int)))
    scbench_table = int(re.search(r"On the published (\d+)-task table", text(README)).group(1))
    spatial_table = int(re.search(r"On the (\d+)-task table in the repository", text("docs/SPATIALBENCH.md")).group(1))
    assert scbench_table == size["scBench"] and spatial_table != size["SpatialBench"]
    say(SUITE, f"use the {scbench_table}-task summary table in the scBench repository, which is the size of the current board.")
    say(SUITE, f"use the {spatial_table}-task summary table in the SpatialBench repository, which is not the "
               f"{size['SpatialBench']}-evaluation set the board now scores.")

    # Section 3: what the site says about scoring.
    say(SUITE, f"{site['leaderboards']} leaderboards. The site counts {site['capability_benchmarks']} as capability "
               f"benchmarks and scores {site['scored_apart_as_safeguards']} apart, as safeguards.")
    here = site["boards_read_that_count_toward_the_overall_score"]
    there = site["biosecurity_boards_that_count_toward_the_overall_score"]
    assert here == int((boards["counts_toward_overall_score"].astype(str) == "True").sum())
    assert here + there == site["contribute_to_the_overall_score"]
    say(SUITE, f"{site['contribute_to_the_overall_score']} of the {site['capability_benchmarks']} contribute to its overall "
               f"score: {here} of the {n} boards above and {there} biosecurity boards. A configuration may miss at most "
               f"{site['missing_boards_allowed_in_the_overall_score']} of the {site['contribute_to_the_overall_score']}.")
    weighted = boards[boards["overall_weight"] != ""]
    odd = weighted[weighted["overall_weight"].astype(int) != weighted["evaluations"].astype(int)]
    assert (odd["overall_weight"].astype(int) == odd["original_study_evaluations"].astype(int)).all()
    say(SUITE, f"It does for {len(odd)} boards, where the weight is the size in the original study: "
               + listed([f"{b['board']} (weight {int(b['overall_weight'])}, set {int(b['evaluations'])})" for _, b in odd.iterrows()])
               + ".")
    rule = {r: list(g["board"]) for r, g in boards[boards["refusal_rule_stated"] != ""].groupby("refusal_rule_stated", sort=False)}
    stated = sum(len(v) for v in rule.values())
    assert stated == site["boards_read_that_state_a_refusal_rule"] and set(rule) == {"a failure", "stays in the denominator", "leaves the denominator"}
    against = len(rule["a failure"]) + len(rule["stays in the denominator"])
    say(SUITE, f"{stated} of the {n} board pages say how a refusal is scored. On {listed(rule['a failure'])} a refusal is a "
               f"failure, and on {listed(rule['stays in the denominator'])} it stays in the denominator, so on all {against} "
               f"it counts against the score. On {listed(rule['leaves the denominator'])} it is not graded and leaves the "
               f"denominator. The other {n - stated} pages do not say.")
    answers = int(inv.loc["spatialbench-long", "runs_with_an_answer_file"])
    say(SUITE, f"The {answers} published answers of spatialbench-long also serve in the test of the answer recovery")
    unlinked = "The plain-text page of TissueMicroscopyBench links no repository."
    say(SUITE, unlinked)

    # Section 4.
    say(SUITE, f"It does not cover the biosecurity boards: {site['biosecurity_boards_left_out']} boards with "
               f"{site['biosecurity_evaluations_left_out']} evaluations.")
    return out


def test_every_suite_number_in_the_documents_matches_the_tables(data):
    checked = claims(data)
    assert len(checked) > 30
    missing = [(doc, sentence) for doc, sentence in checked if sentence not in text(doc)]
    assert not missing, missing


def test_the_suite_table_holds_board_level_facts_only(data):
    """No result of any model: the snapshot has no score, no model name and no rank."""
    boards, site = data["boards"], data["site"]
    assert list(boards.columns) == ["board", "area", "horizon", "evaluations", "original_study_evaluations",
                                    "counts_toward_overall_score", "overall_weight", "refusal_rule_stated", "repository",
                                    "board_page", "data_updated"]
    blob = (RES / "suite" / "boards.csv").read_text() + json.dumps(site) + (ROOT / SUITE).read_text()
    assert "%" not in blob
    for name in ("Claude", "GPT", "Gemini", "Grok", "LSVP"):
        assert name not in blob, name


def test_the_figure_of_the_boards_draws_from_the_committed_tables(tmp_path):
    from sc_zprime import figures

    suite = tmp_path / "suite"
    suite.mkdir()
    shutil.copy(RES / "suite" / "boards.csv", suite / "boards.csv")
    figures.draw_suite(suite, RES / "family")
    drawn = (suite / "figures" / "fig_suite_boards.svg").read_text()
    assert (suite / "figures" / "fig_suite_boards.png").stat().st_size > 10_000
    for board in pd.read_csv(suite / "boards.csv")["board"]:
        assert board in drawn, board
