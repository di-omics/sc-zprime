# Tests

`pytest -rs` runs everything and says why any test skips. Tests that need the
benchmark data look for it in `../upstream`, or wherever `SC_ZPRIME_UPSTREAM`
points, and skip without it.

| Test file | Covers | Needs the benchmark data |
|---|---|---|
| `test_graders.py` | `graders.py`, the numeric tolerance grader | no |
| `test_graders_sets.py` | `graders.py`, the set, choice and composite graders | no |
| `test_load.py` | `load.py`, and `report.py` run end to end on small synthetic checkouts | no |
| `test_trajectory.py` | `trajectory.py` | no |
| `test_answers.py` | `answers.py` | no |
| `test_methods.py` | `methods/` and the scBench method specs | no |
| `test_methods_spatialbench.py` | `methods/` and the SpatialBench method specs | no |
| `test_metrics.py` | `metrics.py` | no |
| `test_uncertainty.py` | `uncertainty.py` and `scripts/interval_coverage.py` | no |
| `test_provenance.py` | `provenance.py` | no |
| `test_regrade.py` | `regrade.py`, `inventory.py` and the inventory figure in `figures.py` | no |
| `test_docs_numbers.py` | the scBench numbers in `README.md` and `docs/FINDINGS.md`, rebuilt from `results/scbench` | no |
| `test_docs_numbers_spatialbench.py` | the SpatialBench numbers in `README.md` and `docs/SPATIALBENCH.md` | one test does |
| `test_docs_numbers_family.py` | the numbers in `README.md` and `docs/FAMILY.md` | no |
| `test_docs_numbers_suite.py` | the numbers in `README.md` and `docs/SUITE.md`, rebuilt from `results/suite` and `results/family`, and the figure of the boards in `figures.py` | no |
| `test_data_policy.py` | that no benchmark value is in a tracked file, and that the tables do not give a reference away | yes |
| `test_upstream.py` | the published verdicts reproduced, `tracing.py`, the measured answer recovery, the pinned commits | yes |

Not every module has a test file of its own:

- `report.py` is exercised through `test_load.py`.
- `inventory.py` is exercised through `test_regrade.py` and `test_data_policy.py`.
- `tracing.py` is checked against real runs only by `test_upstream.py`, which needs the benchmark data.
  `test_load.py` also runs it, through `report.run` on a synthetic checkout, where the trace is empty.
- `figures.py`: one test draws the inventory figure and one the figure of the boards. No test draws the other figures.
- `scripts/site_boards.py` reads the live site and has no test. Its committed output is what `test_docs_numbers_suite.py` checks `docs/SUITE.md` against.
- `cli.py` has no test. The reproduce job in `.github/workflows/ci.yml` runs its 3 commands and compares their output with the committed tables.
