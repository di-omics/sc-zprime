"""Independent re-implementation of the numeric tolerance grader.

Written after reading the upstream grader's source, in separate code, without
importing or copying it, so that agreement between the two is evidence rather
than a tautology. `tests/test_upstream.py` checks this module against every
published verdict, and `tests/test_graders.py` pins the edge cases where the
two could plausibly differ.

A grader config looks like::

    {"ground_truth": {"field": 10.0},
     "tolerances": {"field": {"type": "absolute", "value": 2.0}}}

Supported tolerance types: absolute (symmetric, or asymmetric via lower and
upper), relative, min, max. A missing tolerance entry means exact equality. An
invalid configuration fails closed: nothing passes and the reason is recorded.
"""

from __future__ import annotations

import math
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
        """True when the window floor sits at or below zero for a positive
        reference: the floor is a natural limit, not a tolerance."""
        return self.lower is not None and self.lo <= 0 < self.lo + self.lower


@dataclass
class FieldResult:
    name: str
    passed: bool
    value: float | None
    margin: float | None
    reason: str = ""


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
    pinned = reference > 0 and reference - lower <= 0
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


def grade_numeric_tolerance(answer: Any, config: Any, scale: float = 1.0) -> GradeResult:
    """Grade an answer. Every field must pass for the run to pass."""
    problem = config_problem(config)
    if problem:
        return GradeResult(False, {}, problem)
    reference = config["ground_truth"]
    tolerances = tolerance_block(config)
    if not isinstance(answer, dict):
        return GradeResult(False, {
            name: FieldResult(name, False, None, None, "answer is not an object") for name in reference
        })
    out: dict[str, FieldResult] = {}
    for name, ref in reference.items():
        raw, found = lookup(answer, name)
        if not found:
            out[name] = FieldResult(name, False, None, None, "missing")
            continue
        value, why = coerce(raw)
        if value is None:
            out[name] = FieldResult(name, False, None, None, why)
            continue
        tol = tolerance_entry(tolerances, name)
        band = band_for(float(ref), tol)
        out[name] = FieldResult(name, bool(within(value, ref, tol, scale)), float(value),
                                signed_margin(float(value), float(ref), band))
    return GradeResult(all(f.passed for f in out.values()), out)


GRADERS = {"numeric_tolerance": grade_numeric_tolerance}


def supported(grader: Any) -> bool:
    return isinstance(grader, dict) and grader.get("type") in GRADERS


def grade(answer: Any, grader: dict, scale: float = 1.0) -> GradeResult:
    kind = grader.get("type")
    if kind not in GRADERS:
        raise NotImplementedError(f"grader type {kind!r} is not re-implemented yet")
    return GRADERS[kind](answer, grader.get("config", {}), scale)
