"""Method specs for the batch-correction tasks in the public SpatialBench sample.

Three of the sixteen example tasks test one decision: does the agent correct
for the sample a barcode came from before it clusters? Each asks for a
clustering of a multi-sample dataset and a number that says how far the
clusters follow sample identity. None of the three prompts tells the agent to
integrate. The ovary task's notes say the agent must infer that it is needed;
the two donor tasks' notes say only that the test is whether it is applied.

The tiers follow the design notes published with each task file; `basis`
records where. A rule reads the code of one step, with comments removed.
"""

from __future__ import annotations

from . import Combo, MethodSpec, Rule

_CLUSTER = (r"leiden\s*\(|louvain\s*\(|KMeans\s*\(|kmeans\s*\(|AgglomerativeClustering\s*\("
            r"|PLM\s*\(|best_partition\s*\(|community_(?:leiden|multilevel)\s*\(")
_HARMONY = r"harmony_integrate\s*\(|run_harmony\s*\(|RunHarmony\s*\(|harmonize\s*\("
_BBKNN = r"bbknn\s*\("
_SCANORAMA = r"scanorama_integrate\s*\(|scanorama\.\w+\s*\("
_COMBAT = r"combat\s*\("
_MODEL = r"scvi\.|mnn_correct\s*\(|fastMNN\s*\("
_REGRESS = r"regress_out\s*\("
# batch_key given to variable-gene selection, with any value but None. One
# level of nested brackets is allowed inside the call.
_BATCH_HVG = r"highly_variable_genes\s*\((?:[^()]|\([^()]*\))*?batch_key\s*=\s*(?!None)"

_INTEGRATION = (_HARMONY, _BBKNN, _SCANORAMA, _COMBAT, _MODEL)

NOT_CHECKED = ("An AI model then read the runs that ran a correction, the runs that passed and the runs the rules "
               "could not label, and a second AI model searched every transcript of these tasks for a correction "
               "method and read a sample of the rest. No blind re-rating and no person has checked the labels.")


def _rules(regress_tier: str) -> list[Rule]:
    def tool(label: str, pattern: str) -> Rule:
        others = tuple(p for p in _INTEGRATION if p != pattern)
        return Rule(label, Combo((_CLUSTER, pattern), others, once=_CLUSTER), "intended")

    return [
        tool("Harmony before clustering", _HARMONY),
        tool("BBKNN before clustering", _BBKNN),
        tool("Scanorama before clustering", _SCANORAMA),
        tool("ComBat before clustering", _COMBAT),
        tool("scVI or MNN before clustering", _MODEL),
        Rule("regress_out, no integration method", Combo((_CLUSTER, _REGRESS), _INTEGRATION), regress_tier),
        Rule("sample-aware gene selection only", Combo((_CLUSTER, _BATCH_HVG), _INTEGRATION + (_REGRESS,)), "other"),
        Rule("no sample handling", Combo((_CLUSTER,), _INTEGRATION + (_REGRESS, _BATCH_HVG)), "trap"),
    ]


_DESCRIBE_DRG = {
    "intended": "applies a batch-correction method on the donor key before clustering. The notes derive their "
                "reference with Harmony and list values for it alone; other correction tools are counted here "
                "because the notes say the test is whether correction is applied",
    "trap": "clusters with no correction for donor (the notes' first named trap)",
    "other": "something the notes do not give a value for: variable genes chosen within each donor with no "
             "correction of the embedding, or a covariate regressed out with no integration method. The notes "
             "name regressing fragment count instead of sample as a trap; no public run did either",
}

NORM01 = MethodSpec(
    task="NORM01_batch_correction",
    field="mean_max_sample_fraction",
    rules=_rules("other"),
    describe=_DESCRIBE_DRG,
    basis="task notes, sections 1, 3, 4 and 6",
    checked=NOT_CHECKED,
)

DR01 = MethodSpec(
    task="DR01_batch_confounded_clustering",
    field="n_dominated_clusters",
    rules=_rules("other"),
    describe=_DESCRIBE_DRG,
    basis="task notes, sections 1, 3, 4 and 6. The traced field is a small whole number, which cannot be "
          "found reliably in printed output, so every label on this task comes from the last classifiable "
          "step or from reading",
    checked=NOT_CHECKED,
)

CURIO = MethodSpec(
    task="curio_ovary_batch_driven_clustering",
    field="max_single_timepoint_fraction",
    rules=_rules("trap"),
    describe={
        "intended": "applies a batch-correction method on the timepoint key before clustering (the notes name "
                    "Harmony, BBKNN and Scanorama, and say other correction methods land in the same range)",
        "trap": "clusters with no correction for timepoint, or regresses a covariate out and stops there (the "
                "notes' first two named traps)",
        "other": "variable genes chosen within each timepoint with no correction of the embedding (not "
                 "mentioned in the notes; this analysis' label)",
    },
    basis="task notes, sections 2, 3, 4 and 6",
    checked=NOT_CHECKED,
)

SPECS = [NORM01, DR01, CURIO]

# What the task notes already say about a flag a validation card raises.
# Paraphrase only: no value from the notes is stated.
_DIAGNOSTIC = ("the notes call the variable-gene count diagnostic and give it a window wide enough that it is "
               "not meant to decide a verdict.")
_NO_CONTROL = ("the notes predict that a naive agent will cluster without integrating and land above the window. "
               "They list passing values for a corrected pipeline from the authors' own analysis. No published "
               "agent run submitted a corrected answer to set beside them.")

NOTES_CONTEXT: dict[str, dict[str, str]] = {
    "NORM01_batch_correction": {"DEAD_READOUT": _DIAGNOSTIC, "NO_POSITIVE_CONTROL_IN_RUNS": _NO_CONTROL},
    "DR01_batch_confounded_clustering": {"DEAD_READOUT": _DIAGNOSTIC, "NO_POSITIVE_CONTROL_IN_RUNS": _NO_CONTROL},
    "curio_ovary_batch_driven_clustering": {
        "NO_POSITIVE_CONTROL_IN_RUNS": _NO_CONTROL,
        "TRAP_PASSES": "the notes expect an uncorrected clustering to land well above the window. The run that "
                       "passes clustered every bead with no on-tissue filter, which the notes list as a separate "
                       "trap, and its submitted maximum comes from a cluster of fewer than 20 beads (read from the "
                       "transcript by AI models; not produced by the tool).",
    },
}
