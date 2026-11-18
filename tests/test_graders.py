import math

import pytest

from sc_zprime import graders


def cfg(tol, ref=10.0):
    return {"ground_truth": {"x": ref}, "tolerances": {"x": tol}}


def passed(value, tol, ref=10.0, scale=1.0):
    return graders.grade_numeric_tolerance({"x": value}, cfg(tol, ref), scale).passed


def test_symmetric_window_is_inclusive_at_both_edges():
    tol = {"type": "absolute", "value": 2}
    assert passed(8, tol) and passed(12, tol)
    assert not passed(7.999, tol) and not passed(12.001, tol)


def test_asymmetric_window():
    tol = {"type": "absolute", "lower": 10, "upper": 1}
    assert passed(0, tol) and passed(11, tol)
    assert not passed(-0.01, tol) and not passed(11.01, tol)


def test_relative_min_and_max():
    assert passed(11, {"type": "relative", "value": 0.1})
    assert not passed(11.2, {"type": "relative", "value": 0.1})
    assert passed(5, {"type": "min", "value": 5}) and not passed(4.9, {"type": "min", "value": 5})
    assert passed(5, {"type": "max", "value": 5}) and not passed(5.1, {"type": "max", "value": 5})


def test_relative_against_zero_reference_never_passes():
    assert not passed(0, {"type": "relative", "value": 0.5}, ref=0.0)


def test_missing_tolerance_means_exact_match():
    config = {"ground_truth": {"x": 3}, "tolerances": {}}
    assert graders.grade_numeric_tolerance({"x": 3}, config).passed
    assert not graders.grade_numeric_tolerance({"x": 3.0001}, config).passed


def test_shared_top_level_tolerance():
    config = {"ground_truth": {"a": 10, "b": 20}, "tolerances": {"type": "absolute", "value": 1}}
    assert graders.grade_numeric_tolerance({"a": 10.5, "b": 19.2}, config).passed
    assert not graders.grade_numeric_tolerance({"a": 10.5, "b": 22}, config).passed


@pytest.mark.parametrize("value,ok", [("10.5", True), ("ten", False), (True, False), (None, False),
                                      (float("nan"), False), (float("inf"), False), ([10], False)])
def test_coercion_matches_upstream(value, ok):
    assert passed(value, {"type": "absolute", "value": 2}) is ok


def test_boolean_is_read_as_zero_or_one():
    assert passed(True, {"type": "absolute", "value": 0}, ref=1)


def test_missing_field_and_non_object_answers_fail():
    tol = {"type": "absolute", "value": 2}
    assert not graders.grade_numeric_tolerance({"y": 10}, cfg(tol)).passed
    assert not graders.grade_numeric_tolerance([10], cfg(tol)).passed
    assert not graders.grade_numeric_tolerance(None, cfg(tol)).passed


def test_dotted_names_are_paths_and_never_literal_keys():
    config = {"ground_truth": {"a.b": 1}, "tolerances": {}}
    assert graders.grade_numeric_tolerance({"a": {"b": 1}}, config).passed
    assert not graders.grade_numeric_tolerance({"a.b": 1}, config).passed
    assert graders.grade_numeric_tolerance({"a.b": 9, "a": {"b": 1}}, config).passed


def test_every_field_must_pass_and_score_is_the_fraction():
    config = {"ground_truth": {"a": 1, "b": 2}, "tolerances": {}}
    result = graders.grade_numeric_tolerance({"a": 1, "b": 3}, config)
    assert not result.passed and result.score == 0.5


def test_signed_margin_uses_the_width_on_its_own_side():
    band = graders.band_for(10.0, {"type": "absolute", "lower": 4, "upper": 2})
    assert graders.signed_margin(8.0, 10.0, band) == pytest.approx(-0.5)
    assert graders.signed_margin(12.0, 10.0, band) == pytest.approx(1.0)
    assert graders.signed_margin(10.0, 10.0, band) == 0


def test_exact_fields_have_no_margin():
    band = graders.band_for(3.0, {"type": "absolute", "value": 0})
    assert band.exact and graders.signed_margin(3.0, 3.0, band) is None


def test_one_sided_checks_are_their_own_kind():
    low = graders.band_for(1.0, {"type": "min", "value": 90})
    high = graders.band_for(1.0, {"type": "max", "value": 120})
    assert (low.kind, high.kind) == ("min", "max")
    assert not low.exact and low.lower is None and graders.signed_margin(95.0, 1.0, low) is None


def test_edge_decisions_use_the_upstream_form_of_the_comparison():
    """abs(1.1 - 1) is 0.10000000000000009 in floating point, so a symmetric
    tolerance of 0.1 rejects 1.1 even though 1 + 0.1 == 1.1."""
    assert abs(1.1 - 1) > 0.1 and 1 + 0.1 == 1.1
    assert not passed(1.1, {"type": "absolute", "value": 0.1}, ref=1)
    assert passed(1.1, {"type": "absolute", "lower": 0.1, "upper": 0.1}, ref=1)
    assert passed(0.3, {"type": "absolute", "value": 0.7}, ref=1) == (abs(0.3 - 1) <= 0.7)


@pytest.mark.parametrize("config", [
    {"ground_truth": {"x": 1.0}, "tolerances": {"x": []}},
    {"ground_truth": {"x": 1.0}, "tolerances": {"x": {"type": "fuzzy", "value": 1}}},
    {"ground_truth": {"x": 1.0}, "tolerances": {"x": {"type": "absolute", "lower": 1}}},
    {"ground_truth": {"x": 1.0}, "tolerances": {"x": {"type": "absolute", "value": -1}}},
    {"ground_truth": {"x": 1.0}, "tolerances": {"x": {"type": "relative"}}},
    {"ground_truth": {"x": True}, "tolerances": {}},
    {"ground_truth": {"x": float("nan")}, "tolerances": {}},
    {"ground_truth": {}, "tolerances": {}},
    {"ground_truth": {"x": 1.0}, "tolerances": []},
    "not a config",
])
def test_invalid_configs_fail_closed(config):
    result = graders.grade_numeric_tolerance({"x": 1.0}, config)
    assert not result.passed and result.config_error


def test_an_oversized_integer_fails_the_field_instead_of_crashing():
    result = graders.grade_numeric_tolerance({"x": int("9" * 400)}, cfg({"type": "absolute", "value": 0.1}, 1.0))
    assert not result.passed and result.config_error is None


def test_a_floor_at_zero_is_not_moved_when_tolerances_are_scaled():
    """Reference 0.2 with a lower arm of 0.2 puts the floor at zero. Tightening
    by 20% must not lift the floor and fail an answer near zero."""
    tol = {"type": "absolute", "lower": 0.2, "upper": 0.1}
    assert passed(0.01, tol, ref=0.2) and passed(0.01, tol, ref=0.2, scale=0.8)
    assert passed(0.29, tol, ref=0.2) and not passed(0.29, tol, ref=0.2, scale=0.8)
    assert graders.band_for(0.2, tol).lower_pinned_at_zero
    assert not graders.band_for(10.0, {"type": "absolute", "value": 2}).lower_pinned_at_zero


def test_scale_tightens_and_widens_the_window():
    tol = {"type": "absolute", "value": 2}
    assert passed(11.9, tol) and not passed(11.9, tol, scale=0.8)
    assert not passed(12.4, tol) and passed(12.4, tol, scale=1.25)


def test_unknown_grader_type_is_refused():
    with pytest.raises(NotImplementedError):
        graders.grade({}, {"type": "rubric", "config": {}})
    assert math.isfinite(graders.grade({"x": 1}, {"type": "numeric_tolerance", "config": cfg({"value": 1}, 1)}).score)
