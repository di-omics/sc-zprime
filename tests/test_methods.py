import json

from sc_zprime import methods
from sc_zprime.methods import CallArgument, Combo, KeywordChoice
from sc_zprime.methods.scbench import HvgCall
from sc_zprime.methods import scbench

DE = scbench.DE_PSEUDOBULK
HVG = scbench.HVG_NORMALIZATION
PCA = scbench.PCA_PREPROCESSING


def labels(code, spec):
    return [r.label for r in methods.classify(code, spec)]


def write(tmp_path, steps):
    """Write a chat-style transcript from (command, output) pairs."""
    messages = []
    for i, (command, output) in enumerate(steps):
        messages.append({"role": "assistant", "tool_calls": [{"id": f"c{i}", "function": {"arguments": json.dumps({"command": command})}}]})
        messages.append({"role": "tool", "tool_call_id": f"c{i}", "content": json.dumps({"returncode": 0, "output": output})})
    (tmp_path / "trajectory.json").write_text(json.dumps({"messages": messages}))
    return tmp_path


def test_design_argument_decides_paired_or_unpaired():
    paired = "dds = DeseqDataSet(counts=c, metadata=m, design='~ donor + condition')"
    unpaired = "dds = DeseqDataSet(counts=c, metadata=m,\n    design_factors='condition',\n    refit_cooks=True)"
    assert labels(paired, DE) == ["pseudobulk DESeq2, donor in design"]
    assert labels(unpaired, DE) == ["pseudobulk DESeq2, no donor term"]


def test_design_passed_as_a_variable_is_followed_one_level():
    code = "factors = ['donor', 'condition']\ndds = DeseqDataSet(counts=c, metadata=m, design_factors=factors)"
    assert labels(code, DE) == ["pseudobulk DESeq2, donor in design"]


def test_a_method_named_only_in_a_comment_is_ignored():
    code = "# could also try rank_genes_groups(method='wilcoxon')\ndds = DeseqDataSet(counts=c, metadata=m, design='~donor+condition')"
    assert labels(code, DE) == ["pseudobulk DESeq2, donor in design"]


def test_hvg_rules_read_flavour_and_input_state():
    assert labels("sc.pp.highly_variable_genes(a, n_top_genes=2000, flavor='seurat_v3')", HVG) == ["variance-stabilised HVG on counts (seurat_v3)"]
    assert labels("sc.pp.normalize_total(a)\nsc.pp.log1p(a)\nsc.pp.highly_variable_genes(a, n_top_genes=2000)", HVG) == ["log-normalise, then dispersion HVG"]
    assert labels("sc.pp.highly_variable_genes(a, n_top_genes=2000)", HVG) == ["dispersion HVG on raw counts"]
    assert labels("sc.pp.normalize_total(a)\nsc.pp.highly_variable_genes(a, flavor='seurat_v3')", HVG) == ["seurat_v3 given log-normalised data"]
    assert labels("for flavor in opts:\n    sc.pp.highly_variable_genes(a, flavor=flavor)", HVG) == []


def test_a_log_transform_alone_is_not_the_named_trap():
    """The notes name normalize_total plus log1p as the trap. A size-factor
    method followed by log1p is one they accept, so log1p alone is not it."""
    code = "sc.pp.log1p(a)\nsc.pp.highly_variable_genes(a, n_top_genes=2000)"
    assert labels(code, HVG) == ["log1p without size normalisation, then dispersion HVG"]
    assert methods.classify(code, HVG)[0].tier == "other"


def test_seurat_v3_reading_a_counts_layer_is_on_raw_counts():
    code = "sc.pp.normalize_total(a)\nsc.pp.log1p(a)\nsc.pp.highly_variable_genes(a, flavor='seurat_v3', layer='counts')"
    assert labels(code, HVG) == ["variance-stabilised HVG on counts (seurat_v3)"]
    assert HvgCall(("seurat",), normalized=True).search("highly_variable_genes(a)") is None


def test_linear_model_pseudobulk_needs_a_donor_term_to_be_intended():
    assert labels("fit <- glmQLFit(y, model.matrix(~ donor + condition))", DE) == ["pseudobulk edgeR or limma, donor in design"]
    assert labels("fit <- glmQLFit(y, model.matrix(~ condition))", DE) == ["pseudobulk edgeR or limma, no donor term"]


def test_combo_requires_exactly_one_pipeline():
    one = "sc.pp.regress_out(a, ['total_counts'])\nsc.pp.scale(a)\nsc.tl.pca(a)"
    assert labels(one, PCA) == ["depth regressed and genes scaled before PCA"]
    assert labels("sc.pp.scale(a)\nsc.tl.pca(a)", PCA) == ["genes scaled, depth not regressed"]
    assert labels("sc.tl.pca(a)", PCA) == ["PCA with neither step"]
    assert labels(one + "\nsc.tl.pca(b)", PCA) == []


def test_helpers_accept_any_searchable():
    assert CallArgument("f", "k", "x").search("f(k='x')") is not None
    assert CallArgument("f", "k", "x", want=False).search("f(k='y')") is not None
    assert Combo(("a", "b"), ("c",)).search("a b") is not None and Combo(("a",), ("c",)).search("a c") is None
    assert KeywordChoice("f", "k", ("x",), "x").search("f(1)") is not None


def test_value_is_traced_to_the_script_that_printed_it(tmp_path):
    run = write(tmp_path, [
        ("cat > de.py <<'EOF'\ndds = DeseqDataSet(counts=c, metadata=m, design='~condition')\nEOF", ""),
        ("python de.py", "Number of DEGs: 4242"),
        ("cat > de2.py <<'EOF'\ndds = DeseqDataSet(counts=c, metadata=m, design='~donor+condition')\nEOF", ""),
        ("python de2.py", "Number of DEGs: 3131"),
        ("cat eval_answer.json", '{"n_degs": 4242}'),
    ])
    a = methods.attribute("r", run, 4242, DE)
    assert a.label == "pseudobulk DESeq2, no donor term" and a.tier == "partial" and a.source == "printed_by_script"


def test_a_sweep_is_skipped_for_the_step_that_commits(tmp_path):
    sweep = "sc.pp.highly_variable_genes(a, flavor='seurat_v3')\nsc.pp.normalize_total(b)\nsc.pp.highly_variable_genes(b, flavor='seurat')"
    final = "sc.pp.highly_variable_genes(a, n_top_genes=2000, flavor='seurat_v3')\nprint(med)"
    run = write(tmp_path, [(sweep, "seurat_v3 205\nseurat 95"), (final, "205")])
    a = methods.attribute("r", run, 205, HVG)
    assert a.tier == "intended" and a.step_index == 1


def test_reviewed_label_overrides_and_is_marked(tmp_path):
    run = write(tmp_path, [("sc.tl.pca(a)", "0.5")])
    over = {"r": {"run_id": "r", "label": "genes scaled, depth not regressed", "note": "read in full"}}
    a = methods.attribute("r", run, 0.5, PCA, over)
    assert a.source == "reviewed" and a.tier == "trap"


def test_short_values_fall_back_instead_of_matching_noise(tmp_path):
    run = write(tmp_path, [("ls", "1 file"), ("sc.tl.rank_genes_groups(a, 'g', method='wilcoxon')", "done")])
    a = methods.attribute("r", run, 1, DE)
    assert a.source == "fallback" and a.label == "per-cell rank test"


def test_classify_any_sees_a_method_inside_a_sweep():
    sweep = "sc.pp.scale(a)\nsc.tl.pca(a)\nsc.pp.regress_out(b, ['total_counts'])\nsc.pp.scale(b)\nsc.tl.pca(b)"
    assert labels(sweep, PCA) == []
    assert "intended" in {r.tier for r in methods.classify_any(sweep, PCA)}
