"""Independent re-implementation of the graders the public tasks use.

Written after reading the upstream graders' source, in separate code, without
importing or copying it, so that agreement between the two is evidence rather
than a tautology.

The numeric tolerance grader is checked against every published verdict
(`tests/test_upstream.py`), and `tests/test_graders.py` pins the edge cases
where the two could plausibly differ. The set, choice and composite graders
further down have no published verdicts to be checked against: no benchmark
that uses them publishes its per-run verdicts. They follow a reading of the
upstream source and are pinned by unit tests only. Results that rest on them
say so.

A grader config looks like::

    {"ground_truth": {"field": 10.0},
     "tolerances": {"field": {"type": "absolute", "value": 2.0}}}

Supported tolerance types: absolute (symmetric, or asymmetric via lower and
upper), relative, min, max. A missing tolerance entry means exact equality. An
invalid configuration fails closed: nothing passes and the reason is recorded.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Any

KINDS = ("absolute", "relative", "min", "max")


@dataclass(frozen=True)
class Band:
    """Accepted interval for one field, plus the distance to each edge.

    `lower` and `upper` are the distances from the reference to each edge and
    are what the signed margin is normalised by. For one-sided `min` and `max`
    checks they are None: there is no width to measure against.
    """

    lo: float
    hi: float
    lower: float | None
    upper: float | None
    kind: str

    @property
    def exact(self) -> bool:
        return self.kind == "exact"

    @property
    def lower_pinned_at_zero(self) -> bool:
        """True when the window floor sits at or below zero for a reference
        that is zero or positive: the floor is a natural limit, not a
        tolerance. A reference of zero counts. Leaving it out would let the
        published flag tell a reference of zero from a small positive one."""
        return self.lower is not None and self.lo <= 0 <= self.lo + self.lower


@dataclass
class FieldResult:
    """One graded field.

    `kind` is numeric, label_set, marker_list or choice. For the set kinds
    `score` is the similarity that was thresholded and `gap` is that score
    minus its threshold (for a marker list, the smaller of the precision and
    recall gaps), so a gap of zero or more is a pass on similarity. `reason`
    is empty, or one of missing, wrong_type, count, value.
    `near_miss` names a change of form alone that would have turned a failure
    into a pass.
    """

    name: str
    passed: bool
    value: float | None
    margin: float | None
    reason: str = ""
    kind: str = "numeric"
    score: float | None = None
    gap: float | None = None
    near_miss: str = ""


@dataclass
class GradeResult:
    passed: bool
    fields: dict[str, FieldResult] = field(default_factory=dict)
    config_error: str | None = None

    @property
    def score(self) -> float:
        if not self.fields:
            return 0.0
        return sum(f.passed for f in self.fields.values()) / len(self.fields)


def finite_number(x: Any) -> bool:
    """A JSON number that is finite and fits in a float. Booleans are not numbers."""
    if isinstance(x, bool) or not isinstance(x, (int, float)):
        return False
    try:
        return math.isfinite(float(x))
    except OverflowError:
        return False


def _entry_problem(entry: Any, where: str) -> str | None:
    if not isinstance(entry, dict):
        return f"{where} must be an object"
    kind = entry.get("type", "absolute")
    if not isinstance(kind, str) or kind not in KINDS:
        return f"{where}.type must be one of {', '.join(KINDS)}"
    value_given, lower_given, upper_given = "value" in entry, "lower" in entry, "upper" in entry
    if kind == "absolute":
        if lower_given != upper_given:
            return f"{where} must give lower and upper together"
        if lower_given:
            for key in ("lower", "upper"):
                if not finite_number(entry[key]) or float(entry[key]) < 0:
                    return f"{where}.{key} must be a finite non-negative number"
            return None
        if not value_given:
            return None
    elif lower_given or upper_given:
        return f"{where}: lower and upper apply to absolute tolerances only"
    if not value_given:
        return f"{where}.value is required for a {kind} tolerance"
    if not finite_number(entry["value"]):
        return f"{where}.value must be a finite number"
    if kind in ("absolute", "relative") and float(entry["value"]) < 0:
        return f"{where}.value must not be negative"
    return None


def tolerance_block(config: dict) -> Any:
    """The tolerance block, under either of the two keys the benchmark uses."""
    for key in ("tolerances", "tolerance"):
        if key in config:
            return config[key]
    return {}


def config_problem(config: Any) -> str | None:
    """Reason a grader config is invalid, or None. Invalid configs fail closed."""
    if not isinstance(config, dict):
        return "the grader config is not a JSON object"
    reference = config.get("ground_truth", {})
    tolerances = tolerance_block(config)
    if not isinstance(reference, dict) or not reference:
        return "no reference values are given"
    for name, value in reference.items():
        if not isinstance(name, str) or not name.strip():
            return "a reference field has an empty or non-text name"
        if not finite_number(value):
            return f"ground_truth[{name!r}] must be a finite number"
    if not isinstance(tolerances, dict):
        return "the tolerance block is not a JSON object"
    if not tolerances:
        return None
    if "type" in tolerances:
        return _entry_problem(tolerances, "tolerances")
    for name, entry in tolerances.items():
        if not isinstance(name, str) or not name.strip():
            return "a tolerance entry has an empty or non-text name"
        problem = _entry_problem(entry, f"tolerances[{name!r}]")
        if problem:
            return problem
    return None


def tolerance_entry(tolerances: dict, name: str) -> dict:
    """Resolve the tolerance for one field.

    A single shared tolerance may be written at the top level
    ({"type": ..., "value": ...}) instead of one entry per field.
    """
    entry = tolerances.get(name, {"type": "absolute", "value": 0})
    own = tolerances.get(name, {})
    if "type" in tolerances and not (isinstance(own, dict) and "value" in own):
        return tolerances
    return entry


def _arms(reference: float, tol: dict) -> tuple[str, float | None, float | None]:
    kind = tol.get("type", "absolute")
    value = tol.get("value", 0)
    if kind == "absolute":
        return kind, float(tol.get("lower", value)), float(tol.get("upper", value))
    if kind == "relative":
        width = abs(reference) * float(value) if reference != 0 else None
        return kind, width, width
    return kind, None, None


def band_for(reference: float, tolerance: dict | None) -> Band:
    """Accepted interval for a reference value and its tolerance entry."""
    tol = tolerance or {"type": "absolute", "value": 0}
    kind, lower, upper = _arms(reference, tol)
    if kind == "min":
        return Band(float(tol["value"]), math.inf, None, None, kind)
    if kind == "max":
        return Band(-math.inf, float(tol["value"]), None, None, kind)
    if lower is None or upper is None:
        # Relative tolerance against a zero reference: nothing can pass.
        return Band(math.inf, -math.inf, None, None, "relative")
    if lower == 0 and upper == 0:
        return Band(reference, reference, 0.0, 0.0, "exact")
    return Band(reference - lower, reference + upper, lower, upper, kind)


def coerce(value: Any) -> tuple[Any, str]:
    """Coerce a submitted value the way the upstream grader does.

    Strings that parse as floats are accepted, booleans become 0 or 1, and
    None, NaN, infinities, oversized integers and containers are rejected.
    The number is returned uncoerced beyond that, so integers stay exact.
    """
    if isinstance(value, str):
        try:
            value = float(value)
        except (OverflowError, ValueError):
            return None, "not a number"
    if isinstance(value, bool):
        value = int(value)
    if value is None:
        return None, "null"
    if not finite_number(value):
        return None, "not a finite number"
    return value, ""


def within(value, reference, tol: dict, scale: float = 1.0) -> bool:
    """The pass test for one field.

    At scale 1 the comparisons are written exactly as upstream writes them,
    because floating-point results at a window edge depend on the form: a
    symmetric absolute tolerance tests |value - reference| <= tolerance, which
    is not always the same as reference - tolerance <= value <= reference +
    tolerance.

    `scale` multiplies the tolerance, to ask what would change if a window had
    been tighter or wider. A lower edge that sits at or below zero for a
    positive reference is a natural floor rather than a tolerance, so it is
    left where it is and only the other edge moves.
    """
    kind = tol.get("type", "absolute")
    if kind == "min":
        return value >= tol["value"]
    if kind == "max":
        return value <= tol["value"]
    if kind == "relative":
        if reference == 0:
            return False
        return abs(value - reference) / abs(reference) <= tol["value"] * scale
    base = tol.get("value", 0)
    lower, upper = tol.get("lower", base), tol.get("upper", base)
    asymmetric = "lower" in tol and "upper" in tol
    pinned = reference >= 0 and reference - lower <= 0
    if scale == 1.0 or not pinned:
        if asymmetric:
            return (reference - lower * scale) <= value <= (reference + upper * scale)
        return abs(value - reference) <= base * scale
    return (reference - lower) <= value <= (reference + upper * scale)


def signed_margin(value: float, reference: float, band: Band) -> float | None:
    """Signed distance from the reference in units of the tolerance width.

    0 is the reference, +1 and -1 are the band edges, and |margin| <= 1 is a
    pass up to floating-point rounding at the edge itself. Exact-match fields
    and one-sided checks have no width, so the margin is undefined.
    """
    if band.lower is None or band.upper is None or band.exact:
        return None
    delta = value - reference
    if delta >= 0:
        return delta / band.upper if band.upper > 0 else (0.0 if delta == 0 else math.inf)
    return delta / band.lower if band.lower > 0 else -math.inf


def lookup(answer: Any, name: str) -> tuple[Any, bool]:
    """Fetch a field. A name without a dot is a plain key. A dotted name is
    walked as a path and is never read as a literal key."""
    if not isinstance(answer, dict):
        return None, False
    if "." not in name:
        return answer.get(name), name in answer
    node: Any = answer
    for part in name.split("."):
        if not isinstance(node, dict) or part not in node:
            return None, False
        node = node[part]
    return node, True


_NUMBER_IN_TEXT = re.compile(r"(?<![\w.])[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?(?![\w]|\.\d)")


def grade_numeric_tolerance(answer: Any, config: Any, scale: float = 1.0) -> GradeResult:
    """Grade an answer. Every field must pass for the run to pass."""
    problem = config_problem(config)
    if problem:
        return GradeResult(False, {}, problem)
    reference = config["ground_truth"]
    tolerances = tolerance_block(config)
    if not isinstance(answer, dict):
        return GradeResult(False, {
            name: FieldResult(name, False, None, None, "wrong_type") for name in reference
        })
    out: dict[str, FieldResult] = {}
    for name, ref in reference.items():
        raw, found = lookup(answer, name)
        if not found:
            out[name] = FieldResult(name, False, None, None, "missing")
            continue
        value, why = coerce(raw)
        tol = tolerance_entry(tolerances, name)
        if value is None:
            # Text where a number was wanted fails. Note, without changing
            # that, when a number written inside the text would have passed.
            inside = [float(t) for t in _NUMBER_IN_TEXT.findall(raw)] if isinstance(raw, str) else []
            near = "number_in_text" if any(within(v, ref, tol, scale) for v in inside) else ""
            out[name] = FieldResult(name, False, None, None, "wrong_type", near_miss=near)
            continue
        band = band_for(float(ref), tol)
        ok = bool(within(value, ref, tol, scale))
        out[name] = FieldResult(name, ok, float(value), signed_margin(float(value), float(ref), band),
                                "" if ok else "value")
    return GradeResult(all(f.passed for f in out.values()), out)


# --- Set, choice and composite graders -------------------------------------
#
# Not checked against published verdicts: see the module docstring.

def _fraction(value: Any) -> bool:
    return finite_number(value) and 0.0 <= float(value) <= 1.0


def _expected_count(config: dict) -> tuple[int | None, str | None]:
    """An optional exact-length rule: the list and its distinct items must both have this length."""
    count = config.get("expected_count")
    if count is None:
        return None, None
    if isinstance(count, bool) or not isinstance(count, int) or count < 0:
        return None, "expected_count must be a non-negative whole number"
    return count, None


def _scalar_labels(value: Any) -> list[str] | None:
    """A list of JSON scalars as text, compared exactly as written. None if it is not such a list."""
    if not isinstance(value, list):
        return None
    out = []
    for item in value:
        if not isinstance(item, (str, int, float, bool)) or (isinstance(item, float) and not math.isfinite(item)):
            return None
        out.append(str(item))
    return out


def _jaccard(a: set, b: set) -> float:
    union = a | b
    return len(a & b) / len(union) if union else 0.0


def _fold(label: str) -> str:
    return " ".join(label.split()).casefold()


def grade_label_set_jaccard(answer: Any, config: Any, scale: float = 1.0) -> GradeResult:
    """Jaccard similarity between a submitted list of labels and the reference list.

    Labels are compared as exact text: case and spacing count. A submitted
    value that is not a list fails, even if it is the right label as a bare
    string.
    """
    if not isinstance(config, dict):
        return GradeResult(False, {}, "the grader config is not a JSON object")
    reference = _scalar_labels(config.get("ground_truth_labels"))
    if not reference:
        return GradeResult(False, {}, "ground_truth_labels must be a non-empty list of scalars")
    scoring = config.get("scoring", {})
    if not isinstance(scoring, dict):
        return GradeResult(False, {}, "scoring must be an object")
    threshold = scoring.get("pass_threshold", 0.90)
    if not _fraction(threshold):
        return GradeResult(False, {}, "pass_threshold must be a number from 0 to 1")
    name = config.get("answer_field", "cell_types_predicted")
    if not isinstance(name, str) or not name.strip():
        return GradeResult(False, {}, "answer_field must be a non-empty string")
    count, problem = _expected_count(config)
    if problem:
        return GradeResult(False, {}, problem)

    def fail(reason: str, near: str = "") -> GradeResult:
        return GradeResult(False, {name: FieldResult(name, False, None, None, reason, "label_set", near_miss=near)})

    if not isinstance(answer, dict) or name not in answer:
        return fail("missing")
    submitted = _scalar_labels(answer[name])
    truth = set(reference)
    if submitted is None:
        raw = answer[name]
        as_list = [str(raw)] if isinstance(raw, (str, int, float, bool)) else None
        near = "scalar_not_list" if as_list and count in (None, 1) and _jaccard(truth, set(as_list)) >= threshold else ""
        return fail("wrong_type", near)
    score = _jaccard(truth, set(submitted))
    count_ok = count is None or (len(submitted) == count and len(set(submitted)) == count)
    passed = score >= float(threshold) and count_ok
    near = ""
    if not passed and count_ok and _jaccard({_fold(x) for x in truth}, {_fold(x) for x in submitted}) >= threshold:
        near = "case_or_spacing"
    reason = "" if passed else ("count" if score >= float(threshold) else "value")
    return GradeResult(passed, {name: FieldResult(name, passed, None, None, reason, "label_set", round(score, 6),
                                                  round(score - float(threshold), 6), near)})


def grade_marker_gene_precision_recall(answer: Any, config: Any, scale: float = 1.0) -> GradeResult:
    """Precision and recall of a submitted list against a reference list.

    Names are compared without regard to case. Precision is counted over
    everything submitted, duplicates included. Only the flat-list form is
    re-implemented; a per-cell-type reference fails closed.
    """
    if not isinstance(config, dict):
        return GradeResult(False, {}, "the grader config is not a JSON object")
    reference = config.get("canonical_markers", config.get("ground_truth_labels"))
    if isinstance(reference, dict):
        return GradeResult(False, {}, "the per-cell-type form of this grader is not re-implemented")
    if not isinstance(reference, list) or not reference or any(not isinstance(g, str) or not g.strip() for g in reference):
        return GradeResult(False, {}, "canonical_markers must be a non-empty list of non-empty strings")
    scoring = config.get("scoring", {})
    thresholds = scoring.get("pass_thresholds", {}) if isinstance(scoring, dict) else None
    if not isinstance(thresholds, dict):
        return GradeResult(False, {}, "scoring.pass_thresholds must be an object")
    need_precision, need_recall = thresholds.get("precision_at_k", 0.60), thresholds.get("recall_at_k", 0.50)
    if not _fraction(need_precision) or not _fraction(need_recall):
        return GradeResult(False, {}, "precision and recall thresholds must be numbers from 0 to 1")
    name = config.get("answer_field", "top_marker_genes")
    if not isinstance(name, str) or not name.strip():
        return GradeResult(False, {}, "answer_field must be a non-empty string")
    count, problem = _expected_count(config)
    if problem:
        return GradeResult(False, {}, problem)

    def fail(reason: str) -> GradeResult:
        return GradeResult(False, {name: FieldResult(name, False, None, None, reason, "marker_list")})

    if not isinstance(answer, dict) or name not in answer:
        return fail("missing")
    submitted = answer[name]
    if not isinstance(submitted, list) or any(not isinstance(g, str) or not g.strip() for g in submitted):
        return fail("wrong_type")
    lowered = [g.lower() for g in submitted]
    k = count if count is not None else len(lowered)
    scored = lowered[:k] if count is not None else lowered
    truth = {g.lower() for g in reference}
    hits = len(truth & set(scored))
    precision = hits / k if k > 0 else 0.0
    recall = hits / len(truth)
    count_ok = count is None or (len(lowered) == count and len(set(lowered)) == count)
    similar = precision >= float(need_precision) and recall >= float(need_recall)
    passed = similar and count_ok
    gap = min(precision - float(need_precision), recall - float(need_recall))
    reason = "" if passed else ("count" if similar else "value")
    return GradeResult(passed, {name: FieldResult(name, passed, None, None, reason, "marker_list",
                                                  round(min(precision, recall), 6), round(gap, 6))})


def _choice(value: Any) -> str | None:
    """The comparison form of a multiple-choice answer: text ignores case and outer spaces, whole numbers lose their decimal point."""
    if isinstance(value, str):
        return value.strip().upper() or None
    if isinstance(value, bool):
        return str(value).upper()
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float) and math.isfinite(value):
        return str(int(value)) if value.is_integer() else str(value).upper()
    return None


def grade_multiple_choice(answer: Any, config: Any, scale: float = 1.0) -> GradeResult:
    """One scalar under the key `answer`, compared with the accepted choice or choices."""
    if not isinstance(config, dict):
        return GradeResult(False, {}, "the grader config is not a JSON object")
    if ("correct_answer" in config) == ("correct_answers" in config):
        return GradeResult(False, {}, "exactly one of correct_answer and correct_answers must be given")
    raw = config["correct_answers"] if "correct_answers" in config else [config["correct_answer"]]
    if not isinstance(raw, list) or not raw:
        return GradeResult(False, {}, "correct_answers must be a non-empty list")
    accepted = [_choice(v) for v in raw]
    if any(v is None for v in accepted):
        return GradeResult(False, {}, "every accepted choice must be a non-empty scalar")
    name = "answer"
    if not isinstance(answer, dict) or name not in answer:
        return GradeResult(False, {name: FieldResult(name, False, None, None, "missing", "choice")})
    chosen = _choice(answer[name])
    if chosen is None:
        return GradeResult(False, {name: FieldResult(name, False, None, None, "wrong_type", "choice")})
    ok = chosen in accepted
    return GradeResult(ok, {name: FieldResult(name, ok, None, None, "" if ok else "value", "choice")})


def grade_all_of(answer: Any, config: Any, scale: float = 1.0) -> GradeResult:
    """Every child grader must pass. Each child reads the whole answer.

    Only typed children with a re-implemented grader are handled. Predicate
    leaves, roles and partial-credit rules fail closed here, as an invalid
    configuration, so nothing is passed on a guess.
    """
    if not isinstance(config, dict) or not isinstance(config.get("children"), list):
        return GradeResult(False, {}, "an all_of config needs a list of children")
    if config.get("pass_rule", "all") != "all" or "min_passing_children" in config or "score_threshold" in config:
        return GradeResult(False, {}, "all_of supports only the rule that every child passes")
    children = config["children"]
    if not children:
        return GradeResult(False, {}, "all_of has no children")
    labels = []
    for index, child in enumerate(children):
        if not isinstance(child, dict) or "role" in child or "predicate" in child or child.get("type") == "predicate_leaf":
            return GradeResult(False, {}, f"all_of child {index} is a form that is not re-implemented")
        if child.get("type") not in GRADERS or not isinstance(child.get("config"), dict):
            return GradeResult(False, {}, f"all_of child {index} has grader type {child.get('type')!r}, which is not re-implemented")
        labels.append(str(child.get("name") or f"children[{index}].{child['type']}"))
    if len(set(labels)) != len(labels):
        return GradeResult(False, {}, "all_of child names must be unique")
    fields: dict[str, FieldResult] = {}
    passed = True
    for index, child in enumerate(children):
        result = GRADERS[child["type"]](answer, child["config"], scale)
        if result.config_error:
            return GradeResult(False, {}, f"all_of child {index}: {result.config_error}")
        passed = passed and result.passed
        for name, item in result.fields.items():
            fields[name if name not in fields else f"{name}#{index}"] = item
    return GradeResult(passed, fields)


def grade_list_of(answer: Any, config: Any, scale: float = 1.0) -> GradeResult:
    """A task's top-level list of graders, read strictly: a pass needs every one to pass.

    The public evaluation tool does not grade such a list: its task model and
    harnesses read a single `grader`. It has a helper that runs each listed
    grader on the whole answer and returns the results side by side, and its
    composite grader describes a top-level list as the place for independent,
    partial-credit scoring. How those results become one verdict or reward is
    not in the public code. Counting a pass only when all pass is this
    module's reading, and the number of fields passed is kept next to it.
    """
    return grade_all_of(answer, {"children": (config or {}).get("children")} if isinstance(config, dict) else config, scale)


GRADERS = {
    "numeric_tolerance": grade_numeric_tolerance,
    "label_set_jaccard": grade_label_set_jaccard,
    "jaccard_label_set": grade_label_set_jaccard,
    "marker_gene_precision_recall": grade_marker_gene_precision_recall,
    "multiple_choice": grade_multiple_choice,
    "all_of": grade_all_of,
    "list_of": grade_list_of,
}

# Graders whose re-implementation has been checked against published verdicts.
# The main analysis (`sc-zprime run`) is limited to these.
CHECKED = ("numeric_tolerance",)


def supported(grader: Any) -> bool:
    """True for a grader the main analysis can use: one checked against published verdicts."""
    return isinstance(grader, dict) and grader.get("type") in CHECKED


def gradable(grader: Any) -> bool:
    """True if this module can grade an answer for this grader at all, checked or not."""
    if not isinstance(grader, dict) or grader.get("type") not in GRADERS:
        return False
    if grader["type"] not in ("all_of", "list_of"):
        return True
    children = (grader.get("config") or {}).get("children")
    return isinstance(children, list) and bool(children) and all(
        isinstance(c, dict) and c.get("type") not in ("all_of", "list_of") and gradable(c) for c in children)


def describe(grader: Any) -> str:
    """A grader's type as one word, with the child types of a composite in brackets."""
    if not isinstance(grader, dict) or not grader.get("type"):
        return "not published"
    if grader["type"] not in ("all_of", "list_of"):
        return str(grader["type"])
    children = (grader.get("config") or {}).get("children") or []
    kinds = sorted({str(c.get("type")) for c in children if isinstance(c, dict)})
    return grader["type"] + "(" + " + ".join(kinds) + ")"


def grade(answer: Any, grader: dict, scale: float = 1.0) -> GradeResult:
    kind = grader.get("type")
    if kind not in GRADERS:
        raise NotImplementedError(f"grader type {kind!r} is not re-implemented yet")
    return GRADERS[kind](answer, grader.get("config", {}), scale)
