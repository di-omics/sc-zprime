"""The repository must not contain benchmark answers. Skipped without a checkout.

Every reference value, tolerance and submitted answer with four or more
significant digits is looked for, as a standalone number, in every tracked
text file outside the generated result tables. The canary identifiers and the
task prompts are looked for everywhere.
"""

import json
import os
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
ROOT = Path(os.environ.get("SC_ZPRIME_UPSTREAM", REPO.parent / "upstream"))
SCBENCH = ROOT / "scbench"
pytestmark = pytest.mark.skipif(not (SCBENCH / "evals").exists(), reason="no upstream checkout")


ANALYSED = ("scbench", "spatialbench", "variantbench", "txbench-pp")


def task_files():
    """Task files of every analysed benchmark checkout that is present, in any layout."""
    from sc_zprime import inventory

    for name in ANALYSED:
        if (ROOT / name).is_dir():
            yield from (t["path"] for t in inventory.find_tasks(ROOT / name))


def answer_files():
    for name in ("scbench", "spatialbench"):
        yield from (ROOT / name / "trajectories").glob("*/*/*/*/*/eval_answer.json")

TEXT = {".md", ".py", ".sh", ".toml", ".csv", ".json", ".svg", ".txt", ".cfg"}
SKIP_DIRS = {".git", ".venv", "__pycache__", ".pytest_cache", "build", "dist"}


def tracked_text(include_results: bool):
    for path in REPO.rglob("*"):
        if not path.is_file() or path.suffix not in TEXT:
            continue
        parts = set(path.relative_to(REPO).parts)
        if parts & SKIP_DIRS or any(p.endswith(".egg-info") for p in parts):
            continue
        if not include_results and "results" in parts:
            continue
        yield path


def significant(value) -> str | None:
    """Canonical text of a number, or None if it is too short or too round to identify anything."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    text = repr(float(value)).rstrip("0").rstrip(".") if float(value) != int(value) else str(int(value))
    digits = re.sub(r"[^0-9]", "", text).lstrip("0")
    if len(digits.rstrip("0")) <= 1:
        # Round numbers such as 1000 or 0.05 identify nothing and appear everywhere.
        return None
    return text if len(digits) >= 4 else None


def numbers_in(obj):
    if isinstance(obj, dict):
        for v in obj.values():
            yield from numbers_in(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from numbers_in(v)
    else:
        yield obj


def forbidden_numbers() -> set[str]:
    out = set()
    for spec_path in task_files():
        spec = json.loads(spec_path.read_text())
        for key in ("grader", "graders"):
            out.update(filter(None, (significant(v) for v in numbers_in(spec.get(key, {})))))
    for answer_path in answer_files():
        text = answer_path.read_text()
        try:
            answer = json.loads(text)
        except ValueError:
            # An agent occasionally writes an answer file that is not valid JSON. Its numbers still count.
            answer = [float(t) if "." in t else int(t) for t in re.findall(r"-?\d+(?:\.\d+)?", text)]
        out.update(filter(None, (significant(v) for v in numbers_in(answer))))
    return out


def test_no_benchmark_number_outside_the_result_tables():
    forbidden = forbidden_numbers()
    assert len(forbidden) > 50
    token = re.compile(r"(?<![\w.])-?\d+(?:\.\d+)?(?![\w]|\.\d)")
    leaks = []
    for path in tracked_text(include_results=False):
        found = {t.lstrip("-") for t in token.findall(path.read_text(errors="ignore"))}
        hits = sorted(found & forbidden)
        if hits:
            leaks.append((str(path.relative_to(REPO)), hits))
    assert not leaks, leaks


def test_no_canary_or_prompt_text_anywhere():
    needles = []
    for spec_path in task_files():
        spec = json.loads(spec_path.read_text())
        guid = re.search(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", spec.get("canary", ""))
        if guid:
            needles.append(guid.group(0))
        sentences = [s.strip() for s in re.split(r"(?<=[.?!])\s+", spec.get("task", "")) if len(s.strip()) > 60]
        needles.extend(sentences[:6])
    assert needles
    for path in tracked_text(include_results=True):
        text = path.read_text(errors="ignore")
        for needle in needles:
            assert needle not in text, (str(path.relative_to(REPO)), needle[:50])


def reference_labels() -> set[str]:
    """Labels and names that a set grader holds as its reference, long enough to identify something."""
    found: set[str] = set()

    def walk(node):
        if isinstance(node, dict):
            for key, value in node.items():
                if key in ("ground_truth_labels", "canonical_markers") and isinstance(value, list):
                    found.update(str(v) for v in value if isinstance(v, str) and len(v) >= 6)
                else:
                    walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    for spec_path in task_files():
        spec = json.loads(spec_path.read_text())
        walk(spec.get("grader"))
        walk(spec.get("graders"))
    return found


def test_no_reference_label_anywhere():
    labels = reference_labels()
    if not labels:
        pytest.skip("no checkout with a set grader")
    leaks = []
    for path in tracked_text(include_results=True):
        text = path.read_text(errors="ignore")
        hits = sorted(label for label in labels if label in text)
        if hits:
            leaks.append((str(path.relative_to(REPO)), hits[:5]))
    assert not leaks, leaks


def _numeric_truth(name):
    """(task, field) -> (reference, lower arm, upper arm) for every numeric field of one benchmark checkout."""
    truth = {}
    for spec_path in task_files():
        if ROOT / name not in spec_path.parents:
            continue
        spec = json.loads(spec_path.read_text())
        grader = spec.get("grader") if isinstance(spec, dict) else None
        if not (isinstance(grader, dict) and grader.get("type") == "numeric_tolerance"):
            continue
        config = grader.get("config") or {}
        for field, value in (config.get("ground_truth") or {}).items():
            tol = (config.get("tolerances") or {}).get(field) or {}
            base = tol.get("value")
            lower, upper = tol.get("lower", base), tol.get("upper", base)
            if all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in (value, lower, upper)):
                truth[(spec.get("id") or spec_path.stem, field)] = (value, lower, upper)
    return truth


def _rows(name, table):
    import csv

    path = REPO / "results" / name / table
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _number(text):
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


@pytest.mark.parametrize("name", ["scbench", "spatialbench"])
def test_the_committed_tables_do_not_give_a_reference_away(name):
    """Repeat, on the committed tables, every way a review has found to work a reference out.

    1. A width written as ">200" next to a floor flag that is off said the reference was zero.
    2. For a whole-number field, margins fall on a grid whose spacing is 1 divided by the tolerance. The smallest whole
       tolerance that fits the published margins was the true one for 5 fields, and a window percentage or the floor
       flag then gave the reference of 3 and narrowed others to a few whole numbers.
    3. Z-prime computed from raw answers and written to 3 decimals, with the margins and cluster sizes, left 3 whole
       tolerances for 1 field.
    So: the flag is on wherever the floor is at or below zero, the percentage is withheld for whole-number fields with
    a tolerance under 100, no margin is published as a number for those with a tolerance under 10, for every field
    that still has numeric margins the grid attack must not land on the true tolerance and at least 18 whole
    tolerances must fit, and Z-prime of a whole-number field is written to 1 decimal.
    """
    if not (ROOT / name).is_dir():
        pytest.skip(f"no {name} checkout")
    truth = _numeric_truth(name)
    assert truth, name

    def whole(*values):
        return all(float(v).is_integer() for v in values)

    coarse = {key for key, (ref, lo, hi) in truth.items() if whole(ref, lo, hi) and 0 < max(lo, hi) < 100}
    fine = {key for key, (ref, lo, hi) in truth.items() if whole(ref, lo, hi) and 0 < max(lo, hi) < 10}
    assert fine, "the sample has whole-number fields with a small tolerance; if not, this test checks nothing"

    readouts = {(row["task"], row["field"]): row for row in _rows(name, "readouts.csv")}
    for key, row in readouts.items():
        width = (row["window_lower_pct_of_reference"], row["window_upper_pct_of_reference"])
        if ">200" in width:
            assert row["lower_edge_at_zero"] == "True", ("a wide window with the floor flag off says the reference is zero", key)
        if key in coarse:
            assert width == ("withheld", "withheld"), ("the width would turn a tolerance into the reference", key)
        if key in truth and truth[key][0] >= 0 and truth[key][0] - truth[key][1] <= 0:
            assert row["lower_edge_at_zero"] == "True", ("a reference of zero must read like a small positive one", key)

    traced_field = {row["task"]: row["field"] for row in _rows(name, "method_trace.csv")}
    fine_tasks = {task for task, field in traced_field.items() if (task, field) in fine}
    margins: dict[tuple, set] = {}
    for table, columns in (("answer_clusters.csv", ["margin"]), ("method_trace.csv", ["margin"]),
                           ("method_by_trap.csv", ["lowest_margin", "median_margin", "highest_margin"]),
                           ("method_by_tier.csv", ["median_margin"])):
        for row in _rows(name, table):
            key = (row["task"], row.get("field") or traced_field.get(row["task"]))
            for column in columns:
                value = _number(row[column])
                if key in fine or row["task"] in fine_tasks and "field" not in row:
                    assert value is None, ("a margin on a visible grid is published as a number", table, key, column)
                elif value is not None and "median" not in column:
                    margins.setdefault(key, set()).add(value)
    for row in _rows(name, "method_separation.csv"):
        if row["task"] in fine_tasks:
            for column in ("intended_span_in_tolerance_widths", "nearest_trap_gap_in_tolerance_widths"):
                assert _number(row[column]) is None, (row["task"], column)

    recovered, narrowed = [], []
    for key, seen in margins.items():
        if key not in truth:
            continue
        ref, lower, upper = truth[key]
        if not whole(ref, lower, upper):
            continue
        fits = [t for t in range(1, 100) if all(abs(m * t - round(m * t)) <= 0.005 * t + 1e-9 for m in seen)]
        if len(seen) >= 2 and fits and fits[0] in (lower, upper):
            recovered.append(key)
        if key in coarse and len(fits) < 18:      # a tolerance of 100 or more is not among these candidates at all
            narrowed.append((key, len(fits)))
    assert not recovered, ("the grid attack lands on the true tolerance", recovered)
    assert not narrowed, ("fewer than 18 whole tolerances fit the published margins", narrowed)

    # A statistic of a whole-number field must add nothing to its margins: Z-prime is written to 1 decimal there.
    coarse_tasks = {task for task, field in traced_field.items() if (task, field) in coarse}
    for row in _rows(name, "sensitivity.csv"):
        if row["analysis"] == "Z-prime" and row["scope"] in coarse_tasks and _number(row["value"]) is not None:
            assert round(float(row["value"]), 1) == float(row["value"]), ("Z-prime finer than 1 decimal", row["scope"], row["setting"])
    for row in _rows(name, "uncertainty.csv"):
        if row["scope"] in coarse_tasks and row["statistic"].startswith("Z-prime"):
            for column in ("estimate", "ci_low", "ci_high", "lopo_min", "lopo_max"):
                value = _number(row[column])
                assert value is None or round(value, 1) == value, ("Z-prime finer than 1 decimal", row["scope"], column)
    for row in _rows(name, "method_by_trap.csv"):
        value = _number(row["zprime_against_intended"])
        if row["task"] in coarse_tasks and value is not None:
            assert round(value, 1) == value, ("Z-prime finer than 1 decimal", row["task"])


def test_committed_tables_never_leave_a_window_percentage_blank():
    """Needs no checkout: a blank width on a field with a tolerance would reveal a reference of zero."""
    import csv

    for path in sorted((REPO / "results").glob("*/readouts.csv")):
        with open(path, newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                assert row["window_lower_pct_of_reference"] != "" and row["window_upper_pct_of_reference"] != "", (path.name, row["field"])
