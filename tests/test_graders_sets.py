"""The set, choice and composite graders, on small hand-built cases.

No public run graded with a published config of these types carries a
verdict, so they cannot be checked the way the numeric grader is. Each test
pins one rule read from the upstream source, except where a test says it pins
this module's own choice: forms that are not re-implemented fail closed, and a
list of graders is read strictly. Upstream's own unit tests for these graders
were read and not ported.
"""

from sc_zprime import graders


def jaccard(labels, threshold=1.0, **extra):
    return {"ground_truth_labels": labels, "answer_field": "x", "scoring": {"pass_threshold": threshold}, **extra}


def markers(reference, precision, recall, **extra):
    return {"canonical_markers": reference, "answer_field": "g",
            "scoring": {"pass_thresholds": {"precision_at_k": precision, "recall_at_k": recall}}, **extra}


def one(result):
    (field,) = result.fields.values()
    return field


def test_label_sets_compare_exact_text_and_need_a_list():
    config = jaccard(["NO"])
    assert graders.grade_label_set_jaccard({"x": ["NO"]}, config).passed
    lower = graders.grade_label_set_jaccard({"x": ["no"]}, config)
    assert not lower.passed and one(lower).reason == "value" and one(lower).near_miss == "case_or_spacing"
    bare = graders.grade_label_set_jaccard({"x": "NO"}, config)
    assert not bare.passed and one(bare).reason == "wrong_type" and one(bare).near_miss == "scalar_not_list"
    assert one(graders.grade_label_set_jaccard({}, config)).reason == "missing"


def test_label_set_threshold_is_inclusive_and_order_and_duplicates_do_not_matter():
    config = jaccard(["a", "b", "c", "d"], threshold=0.5)
    half = graders.grade_label_set_jaccard({"x": ["b", "a", "a"]}, config)
    assert half.passed and one(half).score == 0.5 and one(half).gap == 0.0
    assert not graders.grade_label_set_jaccard({"x": ["a", "z", "y"]}, config).passed


def test_a_synonym_list_passes_on_one_match_only_if_the_threshold_allows_it():
    """Ten accepted spellings and a low threshold: one of them alone clears it, two extra labels do not."""
    spellings = [f"name {i}" for i in range(10)]
    assert graders.grade_label_set_jaccard({"x": ["name 3"]}, jaccard(spellings, 0.09)).passed
    assert not graders.grade_label_set_jaccard({"x": ["name 3", "other", "another"]}, jaccard(spellings, 0.09)).passed


def test_an_exact_count_rule_fails_duplicates_and_wrong_lengths():
    config = jaccard(["a", "b"], threshold=0.5, expected_count=2)
    assert graders.grade_label_set_jaccard({"x": ["a", "b"]}, config).passed
    short = graders.grade_label_set_jaccard({"x": ["a"]}, config)
    assert not short.passed and one(short).reason == "count"
    assert not graders.grade_label_set_jaccard({"x": ["a", "a"]}, config).passed


def test_marker_lists_ignore_case_and_count_precision_over_everything_submitted():
    config = markers(["GENE1", "GENE2", "GENE3", "GENE4"], precision=0.75, recall=0.5)
    two = graders.grade_marker_gene_precision_recall({"g": ["gene1", "Gene2"]}, config)
    assert two.passed and one(two).gap == 0.0
    padded = graders.grade_marker_gene_precision_recall({"g": ["GENE1", "GENE2", "OTHER"]}, config)
    assert not padded.passed and one(padded).reason == "value"
    repeated = graders.grade_marker_gene_precision_recall({"g": ["GENE1", "GENE1", "GENE2", "GENE2"]}, config)
    assert not repeated.passed, "duplicates count against precision"


def test_full_recall_with_a_low_precision_floor_admits_a_long_list():
    """A threshold pair of full recall and one in ten precision passes any list that
    holds every reference name and is at most ten times as long."""
    reference = [f"G{i}" for i in range(4)]
    config = markers(reference, precision=0.1, recall=1.0)
    assert graders.grade_marker_gene_precision_recall({"g": reference + [f"X{i}" for i in range(36)]}, config).passed
    assert not graders.grade_marker_gene_precision_recall({"g": reference + [f"X{i}" for i in range(37)]}, config).passed
    assert not graders.grade_marker_gene_precision_recall({"g": reference[:3]}, config).passed


def test_marker_list_shapes_that_fail():
    config = markers(["A1"], 0.5, 0.5)
    assert one(graders.grade_marker_gene_precision_recall({"g": "A1"}, config)).reason == "wrong_type"
    assert one(graders.grade_marker_gene_precision_recall({"g": ["A1", ""]}, config)).reason == "wrong_type"
    assert one(graders.grade_marker_gene_precision_recall({"other": []}, config)).reason == "missing"
    assert not graders.grade_marker_gene_precision_recall({"g": []}, config).passed
    per_type = graders.grade_marker_gene_precision_recall({"g": ["A1"]}, markers({"T": ["A1"]}, 0.5, 0.5))
    assert not per_type.passed and "not re-implemented" in per_type.config_error


def test_multiple_choice_reads_the_answer_key_and_ignores_case_and_number_form():
    assert graders.grade_multiple_choice({"answer": " b "}, {"correct_answer": "B"}).passed
    assert graders.grade_multiple_choice({"answer": 6.0}, {"correct_answer": "6"}).passed
    assert graders.grade_multiple_choice({"answer": "c"}, {"correct_answers": ["B", "C"]}).passed
    assert one(graders.grade_multiple_choice({"answer": "A"}, {"correct_answer": "B"})).reason == "value"
    assert one(graders.grade_multiple_choice({"choice": "B"}, {"correct_answer": "B"})).reason == "missing"
    assert one(graders.grade_multiple_choice({"answer": ["B"]}, {"correct_answer": "B"})).reason == "wrong_type"
    assert graders.grade_multiple_choice({"answer": "B"}, {"correct_answer": "B", "correct_answers": ["B"]}).config_error


NUMERIC = {"type": "numeric_tolerance", "config": {"ground_truth": {"n": 10}, "tolerances": {"n": {"type": "absolute", "value": 2}}}}
LABEL = {"type": "label_set_jaccard", "config": jaccard(["NO"])}


def test_all_of_needs_every_child_and_keeps_every_field():
    grader = {"type": "all_of", "config": {"children": [NUMERIC, LABEL], "pass_rule": "all"}}
    good = graders.grade({"n": 11, "x": ["NO"]}, grader)
    assert good.passed and set(good.fields) == {"n", "x"}
    half = graders.grade({"n": 11, "x": ["YES"]}, grader)
    assert not half.passed and half.score == 0.5
    assert graders.gradable(grader) and not graders.supported(grader)
    assert graders.describe(grader) == "all_of(label_set_jaccard + numeric_tolerance)"


def test_all_of_fails_closed_where_upstream_does():
    for children in ([], [{"type": "rubric", "config": {}}], [dict(NUMERIC, role="gate")]):
        result = graders.grade({"n": 10}, {"type": "all_of", "config": {"children": children}})
        assert not result.passed and result.config_error, children


def test_a_predicate_leaf_fails_closed_here_though_upstream_would_evaluate_it():
    """This module's own choice: predicate leaves are not re-implemented, so nothing is passed on a guess."""
    result = graders.grade({"n": 10}, {"type": "all_of", "config": {"children": [{"predicate": {}, "role": "gate"}]}})
    assert not result.passed and result.config_error
    partial = graders.grade({"n": 10}, {"type": "all_of", "config": {"children": [NUMERIC], "pass_rule": "any"}})
    assert not partial.passed and partial.config_error
    assert not graders.gradable({"type": "all_of", "config": {"children": [{"type": "rubric", "config": {}}]}})


def test_a_list_of_graders_is_read_strictly():
    """This module's own choice: the public tool does not say how a list of graders becomes one verdict."""
    grader = {"type": "list_of", "config": {"children": [NUMERIC, {"type": "multiple_choice", "config": {"correct_answer": "B"}}]}}
    assert graders.grade({"n": 10, "answer": "B"}, grader).passed
    assert not graders.grade({"n": 10, "answer": "A"}, grader).passed
    assert graders.describe(grader) == "list_of(multiple_choice + numeric_tolerance)"


def test_text_where_a_number_is_wanted_fails_and_a_number_inside_it_is_noted():
    sentence = graders.grade({"n": "about 11 units (interval 3 to 40)"}, NUMERIC)
    assert not sentence.passed and one(sentence).reason == "wrong_type" and one(sentence).near_miss == "number_in_text"
    off = graders.grade({"n": "roughly 50"}, NUMERIC)
    assert not off.passed and one(off).near_miss == ""
    assert graders.grade({"n": "11"}, NUMERIC).passed, "text that is only a number is read as that number"


def test_an_exact_count_on_a_marker_list_scores_only_the_first_k_names():
    """Upstream rule: with expected_count, k is that count and the list is cut to its first k names before scoring."""
    config = markers(["A1", "B1", "C1", "D1"], precision=0.5, recall=0.5, expected_count=2)
    assert graders.grade_marker_gene_precision_recall({"g": ["a1", "b1"]}, config).passed
    long = graders.grade_marker_gene_precision_recall({"g": ["A1", "B1", "X9"]}, config)
    assert not long.passed and one(long).reason == "count", "similar enough on the first 2, but 3 names were submitted"
    late = graders.grade_marker_gene_precision_recall({"g": ["X9", "Y9", "A1", "B1"]}, config)
    assert not late.passed and one(late).reason == "value", "hits after the first k names do not count"


def test_labels_that_are_numbers_or_booleans_are_compared_as_text():
    """Upstream rule: every label is cast to text, so 1 and "1" are the same label and True reads "True"."""
    config = jaccard([1, "b", True])
    assert graders.grade_label_set_jaccard({"x": ["1", "b", "True"]}, config).passed
    assert not graders.grade_label_set_jaccard({"x": ["1", "b", "true"]}, config).passed
    assert one(graders.grade_label_set_jaccard({"x": ["1", ["b"]]}, config)).reason == "wrong_type"


def test_defaults_when_a_set_grader_config_leaves_them_out():
    """Upstream defaults: threshold 0.90 and field cell_types_predicted for label sets; 0.60 and 0.50 and
    top_marker_genes for marker lists."""
    ten = [f"L{i}" for i in range(10)]
    labels = {"ground_truth_labels": ten}
    assert graders.grade_label_set_jaccard({"cell_types_predicted": ten}, labels).passed
    assert graders.grade_label_set_jaccard({"cell_types_predicted": ten[:9]}, labels).passed
    assert not graders.grade_label_set_jaccard({"cell_types_predicted": ten[:8]}, labels).passed
    genes = {"canonical_markers": ["G1", "G2", "G3", "G4"]}
    assert graders.grade_marker_gene_precision_recall({"top_marker_genes": ["G1", "G2", "X1"]}, genes).passed
    assert not graders.grade_marker_gene_precision_recall({"top_marker_genes": ["G1", "X1", "X2"]}, genes).passed


def test_a_broken_child_config_stops_the_whole_composite_here():
    """This module's own choice. Upstream counts such a run as failed; here it is left ungraded and reported."""
    broken = {"type": "numeric_tolerance", "config": {"ground_truth": {"n": "ten"}}}
    result = graders.grade({"n": 10, "x": ["NO"]}, {"type": "all_of", "config": {"children": [LABEL, broken]}})
    assert not result.passed and result.config_error and not result.fields
