"""Method specs for the public scBench example tasks.

Each spec states which methods the task authors intend, which they treat as
the trap, and how to recognise each in a transcript. The tiers follow the
design notes published with each task file; `basis` records where.
"""

from __future__ import annotations

import re

from dataclasses import dataclass

from . import CallArgument, Combo, MethodSpec, Rule, _balanced

CHECKED = "All were confirmed by blind AI raters (see validation/)."

_DESEQ = r"(?:DeseqDataSet|DESeqDataSetFromMatrix)"
_DESIGN = r"design(?:_factors)?"
_LINEAR = r"glmQLFit|glmFit|exactTest|voom\s*\(|lmFit"

DE_PSEUDOBULK = MethodSpec(
    task="DE01_pseudobulk_de",
    field="n_degs",
    rules=[
        Rule("pseudobulk DESeq2, donor in design", CallArgument(_DESEQ, _DESIGN, r"donor"), "intended"),
        Rule("pseudobulk DESeq2, no donor term", CallArgument(_DESEQ, _DESIGN, r"donor", want=False), "partial"),
        Rule("pseudobulk edgeR or limma, donor in design", Combo((_LINEAR, r"donor")), "intended"),
        Rule("pseudobulk edgeR or limma, no donor term", Combo((_LINEAR,), (r"donor",)), "partial"),
        Rule("pseudobulk paired t-test, hand-rolled", re.compile(r"ttest_rel|ttest_1samp|stats\.t\.sf"), "other"),
        Rule("per-cell rank test", re.compile(r"method\s*=\s*[\"']wilcoxon|mannwhitneyu|ranksums"), "trap"),
        Rule("per-cell t-test", re.compile(r"method\s*=\s*[\"']t-?test|ttest_ind"), "trap"),
    ],
    describe={
        "intended": "sums counts per donor and condition, then fits a count model with donor as a covariate (the notes' correct approach)",
        "partial": "sums counts per donor and condition, but leaves donor out of the model (not mentioned in the notes; this analysis' label)",
        "trap": "tests individual cells as if they were independent replicates (the notes' primary trap is per-cell testing with scanpy's default tools; they give a value for the t-test and for the rank test, and reject any per-cell method)",
        "other": "donor-aware pseudobulk with a hand-written test instead of a count model (not mentioned in the notes)",
    },
    basis="task notes, sections 1 to 4, for the intended and trap tiers; the partial and other tiers are this analysis' labels for methods the notes do not mention",
    checked=CHECKED,
)


@dataclass(frozen=True)
class HvgCall:
    """Match a variable-gene selection call by flavour and by what was done to
    the matrix earlier in the same script.

    `normalized` and `logged` each require (True), forbid (False) or ignore
    (None) an earlier normalize_total or log1p call. A `layer=` argument is
    read as pointing at raw counts, which is how it is used with seurat_v3.
    """

    flavors: tuple
    normalized: bool | None = None
    logged: bool | None = None

    def search(self, text: str):
        for hit in re.finditer(r"highly_variable_genes\s*\(", text):
            args = _balanced(text, hit.end() - 1)
            present = re.search(r"(?:^|[,(\s])flavor\s*=", args)
            literal = re.search(r"flavor\s*=\s*[\"']+([A-Za-z_0-9]+)[\"']", args)
            if present and not literal:
                continue
            if (literal.group(1) if literal else "seurat") not in self.flavors:
                continue
            before = text[:hit.start()]
            on_layer = re.search(r"layer\s*=", args) is not None
            was_normalized = not on_layer and re.search(r"normalize_total\s*\(", before) is not None
            was_logged = not on_layer and re.search(r"log1p\s*\(", before) is not None
            if self.normalized is not None and was_normalized != self.normalized:
                continue
            if self.logged is not None and was_logged != self.logged:
                continue
            return hit
        return None


_V3 = ("seurat_v3", "seurat_v3_paper")
_DISP = ("seurat", "cell_ranger")

HVG_NORMALIZATION = MethodSpec(
    task="NRM01_sparse_normalization",
    field="median_hvg_prevalence",
    rules=[
        Rule("Pearson residual HVG", re.compile(r"pearson_residuals"), "intended"),
        Rule("variance-stabilised HVG on counts (seurat_v3)", HvgCall(_V3, normalized=False, logged=False), "intended"),
        Rule("seurat_v3 given log-normalised data", HvgCall(_V3, normalized=True), "other"),
        Rule("seurat_v3 given logged, unnormalised data", HvgCall(_V3, normalized=False, logged=True), "other"),
        Rule("log-normalise, then dispersion HVG", HvgCall(_DISP, normalized=True), "trap"),
        Rule("log1p without size normalisation, then dispersion HVG", HvgCall(_DISP, normalized=False, logged=True), "other"),
        Rule("dispersion HVG on raw counts", HvgCall(_DISP, normalized=False, logged=False), "trap"),
    ],
    describe={
        "intended": "selects variable genes with a method the notes accept as depth-aware: Pearson residuals (their reference) or seurat_v3 on raw counts",
        "trap": "an approach the notes name as incorrect: normalize_total and log1p followed by dispersion-based selection, or dispersion-based selection fed raw counts",
        "other": "a variant the notes do not list by name, such as seurat_v3 applied to already normalised data (their last item rejects any pipeline built on normalize_total, which plausibly covers it; kept apart here as the cautious choice)",
    },
    basis="task notes, sections 4 to 6, for the intended and trap tiers; the notes also accept scran and SCTransform, for which there is no rule here because no run used them",
    checked=CHECKED,
)

_REGRESS = r"regress_out\s*\("
_SCALE = r"(?:sc\.pp\.|pp\.)scale\s*\(|StandardScaler"
_PCA = r"(?:sc\.tl\.|sc\.pp\.|tl\.)pca\s*\(|PCA\s*\(|TruncatedSVD"

PCA_PREPROCESSING = MethodSpec(
    task="dr_05_pca_preprocessing_sentinels",
    field="max_top5_depth_corr",
    rules=[
        Rule("depth regressed and genes scaled before PCA", Combo((_PCA, _REGRESS, _SCALE), once=_PCA), "intended"),
        Rule("genes scaled, depth not regressed", Combo((_PCA, _SCALE), (_REGRESS,), once=_PCA), "trap"),
        Rule("depth regressed, genes not scaled", Combo((_PCA, _REGRESS), (_SCALE,), once=_PCA), "trap"),
        Rule("PCA with neither step", Combo((_PCA,), (_REGRESS, _SCALE), once=_PCA), "trap"),
    ],
    describe={
        "intended": "removes sequencing-depth variance and standardises each gene before PCA (the notes require both decisions)",
        "trap": "skips depth regression, gene scaling, or both (the notes' three named traps; skipping regression is their primary one)",
    },
    basis="task notes, sections 2 to 4. The notes also accept SCTransform and scVI with a depth covariate as depth handling; the rules here recognise only an explicit regress_out call, which is all that the public runs used",
    checked=CHECKED,
)

SPECS = [DE_PSEUDOBULK, HVG_NORMALIZATION, PCA_PREPROCESSING]

# Canonical family names used by the blind re-rating in validation/. Several
# rule labels can map to one family.
FAMILY = {
    "pseudobulk DESeq2, donor in design": "pseudobulk_count_model_with_donor",
    "pseudobulk edgeR or limma, donor in design": "pseudobulk_count_model_with_donor",
    "pseudobulk edgeR or limma, no donor term": "pseudobulk_count_model_no_donor",
    "pseudobulk DESeq2, no donor term": "pseudobulk_count_model_no_donor",
    "pseudobulk paired t-test, hand-rolled": "pseudobulk_handrolled_test",
    "per-cell rank test": "per_cell_rank_test",
    "per-cell t-test": "per_cell_t_test",
    "Pearson residual HVG": "pearson_residuals_hvg",
    "variance-stabilised HVG on counts (seurat_v3)": "seurat_v3_on_raw_counts",
    "seurat_v3 given log-normalised data": "seurat_v3_on_lognormalized",
    "seurat_v3 given logged, unnormalised data": "seurat_v3_on_lognormalized",
    "log1p without size normalisation, then dispersion HVG": "lognormalize_then_dispersion_hvg",
    "log-normalise, then dispersion HVG": "lognormalize_then_dispersion_hvg",
    "dispersion HVG on raw counts": "dispersion_hvg_on_raw_counts",
    "depth regressed and genes scaled before PCA": "regress_depth_and_scale",
    "genes scaled, depth not regressed": "scale_only",
    "depth regressed, genes not scaled": "regress_only",
    "PCA with neither step": "neither",
}


# What the task notes already say about a flag a validation card raises.
# Paraphrase only: no value from the notes is stated. A card prints the entry
# under its flag, so a reader does not take a documented design choice for a
# discovery.
NOTES_CONTEXT = {
    "DE01_pseudobulk_de": {
        "TRAP_PASSES": "the notes expect this method to fail below the window, and the value they record for it does. "
                       "The runs that pass obtained higher values with the same method. Why is not established here.",
    },
    "NRM01_sparse_normalization": {
        "DEAD_READOUT": "the notes describe these two fields as scaffolding, there to make the agent inspect the data "
                        "before it chooses a method. They are not meant to discriminate.",
        "EDGE_CLUSTER": "the notes place this recipe at this distance from the lower edge on purpose, and state under "
                        "limitations that the task cannot tell an agent that reasons about depth from one that uses a "
                        "good default.",
    },
}
