# Reviewed method labels

The method tracer in `sc_zprime/methods/` labels most runs automatically.
The files here hold the few runs that had to be read in full, one row each,
with the reason. A reviewed label overrides the automatic one and is marked `reviewed`
in the output tables.

Columns: `run_id` (task/provider/model/harness/replicate, as in the upstream
checkout), `label` (must match a rule label in the task's method spec), and
`note` (what in the public transcript settles it, by step index).

Step indices count shell commands from zero, in transcript order, as parsed
by `sc_zprime.trajectory.load_steps`.

Each of the scBench labels was later confirmed by independent blind raters (AI
models) who never saw it (see `validation/` at the repository root). The
SpatialBench labels have not been through that check yet.
