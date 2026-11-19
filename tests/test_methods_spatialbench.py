"""Rules for the SpatialBench batch-correction tasks, on small code snippets."""

import json

from sc_zprime import methods
from sc_zprime.methods import spatialbench

NORM, CURIO = spatialbench.NORM01, spatialbench.CURIO

PLAIN = "sc.pp.pca(a)\nsc.pp.neighbors(a)\nsc.tl.leiden(a)\n"


def labels(code, spec=NORM):
    return [r.label for r in methods.classify(code, spec)]


def tiers(code, spec=NORM):
    return [r.tier for r in methods.classify(code, spec)]


def test_clustering_with_nothing_done_about_the_sample_is_the_named_trap():
    assert labels(PLAIN) == ["no sample handling"] and tiers(PLAIN) == ["trap"]


def test_each_integration_tool_is_recognised_and_counts_as_intended():
    for call, label in [("sc.external.pp.harmony_integrate(a, key='sample')", "Harmony before clustering"),
                        ("sc.external.pp.bbknn(a, batch_key='sample')", "BBKNN before clustering"),
                        ("sc.external.pp.scanorama_integrate(a, key='sample')", "Scanorama before clustering"),
                        ("sc.pp.combat(a, key='sample')", "ComBat before clustering")]:
        code = f"sc.pp.pca(a)\n{call}\nsc.tl.leiden(a)\n"
        assert labels(code) == [label] and tiers(code) == ["intended"], call


def test_an_integration_tool_named_only_in_a_comment_or_an_install_is_not_a_correction():
    assert labels("# harmony_integrate(a) would be the fix\n" + PLAIN) == ["no sample handling"]
    assert labels("pip install harmonypy") == []


def test_variable_genes_chosen_per_sample_is_not_a_correction_and_not_the_trap():
    code = "sc.pp.highly_variable_genes(a, n_top_genes=min(2000, n), batch_key='sample')\n" + PLAIN
    assert labels(code) == ["sample-aware gene selection only"] and tiers(code) == ["other"]
    assert labels("sc.pp.highly_variable_genes(a, batch_key=None)\n" + PLAIN) == ["no sample handling"]


def test_regress_out_alone_is_a_named_trap_on_the_ovary_task_only():
    code = "sc.pp.regress_out(a, ['total_counts'])\n" + PLAIN
    assert labels(code) == ["regress_out, no integration method"]
    assert tiers(code, NORM) == ["other"] and tiers(code, CURIO) == ["trap"]


def test_a_script_that_clusters_twice_is_not_credited_with_the_correction():
    """Corrected and uncorrected arms in one step: the step does not say which one was submitted."""
    sweep = PLAIN + "sc.external.pp.harmony_integrate(a, key='sample')\nsc.tl.leiden(a, key_added='h')\n"
    assert labels(sweep) == []
    assert "Harmony before clustering" in [r.label for r in methods.classify_any(sweep, NORM)]


def test_a_graph_clustering_outside_scanpy_still_counts_as_clustering():
    assert labels("plm = nk.community.PLM(g, refine=True)\nplm.run()\n") == ["no sample handling"]


def test_a_corrected_number_that_was_printed_but_not_submitted_is_reported(tmp_path):
    """The label follows the submitted value; the corrected attempt is kept as a separate fact."""
    steps = [("sc.pp.pca(a)\nsc.external.pp.bbknn(a, batch_key='sample')\nsc.tl.leiden(a)\nprint(m)", "0.7271"),
             (PLAIN + "print(m)", "0.8852")]
    messages = []
    for i, (command, output) in enumerate(steps):
        messages.append({"role": "assistant", "tool_calls": [{"id": f"c{i}", "function": {"arguments": json.dumps({"command": command})}}]})
        messages.append({"role": "tool", "tool_call_id": f"c{i}", "content": json.dumps({"returncode": 0, "output": output})})
    (tmp_path / "trajectory.json").write_text(json.dumps({"messages": messages}))
    a = methods.attribute("run", tmp_path, 0.8852, NORM)
    assert (a.label, a.tier, a.source) == ("no sample handling", "trap", "printed")
    assert methods.attribute("run", tmp_path, 0.7271, NORM).label == "BBKNN before clustering"


def test_every_spec_is_registered_and_says_how_its_labels_were_checked():
    registry = methods.registry()
    for spec in spatialbench.SPECS:
        assert registry[spec.task] is spec
        assert "No blind re-rating and no person" in spec.checked
