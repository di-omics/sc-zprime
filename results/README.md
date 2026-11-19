# What each result table holds

One folder per benchmark. Every file here is written by the tool and
regenerates from the pinned upstream checkouts (see the README, "Run it").
The tables hold normalised quantities only: see
[docs/DATA_POLICY.md](../docs/DATA_POLICY.md).

## scbench and spatialbench

Written by `sc-zprime run`. Both folders have the same files.

| File | One row is | Written by |
|---|---|---|
| `tasks.csv` | a task: category, platform, grader type, number of graded fields | `load.py` |
| `readouts.csv` | a graded field: its window, pass rate, distinct answers, whether it is dead, the failures it caused | `metrics.readouts` |
| `margin_zones.csv` | a graded field: how many answers fall in each zone around the window edge | `metrics.margin_bins` |
| `tolerance_sweep.csv` | a task at one tolerance scale: pass rate and verdicts that flip | `metrics.tolerance_sweep`, `metrics.sweep_summary` |
| `edge_decided.csv` | a task: runs whose verdict flips when tolerances move a little | `metrics.edge_decided` |
| `answer_clusters.csv` | a group of runs that submitted the identical value for a field | `metrics.clusters` |
| `repeat_cells.csv` | a task and configuration: passes among its repeats, and whether they split | `metrics.repeatability` |
| `repeatability.csv` | a task, plus one row for all tasks: cells that always pass, always fail or split | `metrics.repeatability_summary` |
| `credit.csv` | a task: strict pass rate next to partial credit per field | `metrics.credit` |
| `method_trace.csv` | a run of a traced task: its method label, tier, evidence and verdict | `tracing.trace` |
| `method_by_tier.csv` | a method on a traced task: runs and passes | `tracing.by_method` |
| `method_by_trap.csv` | a named trap method: where its answers land, and Z-prime against the intended method | `metrics.separation_by_trap` |
| `method_separation.csv` | a traced task: intended and trap runs, and how the window sorts them | `metrics.method_separation` |
| `method_by_configuration.csv` | a tier on a traced task, counted in configurations | `uncertainty.configuration_level` |
| `uncertainty.csv` | a headline statistic: estimate, bootstrap interval, leave-one-provider-out range | `uncertainty.uncertainty` |
| `sensitivity.csv` | a headline statistic recomputed under another analysis choice | `uncertainty.sensitivity` |
| `leaderboard_implied.csv` | a configuration of the published summary table: accuracy, interval, told apart from the leader or not | `metrics.leaderboard` |
| `summary.json` | the headline numbers, the fingerprint of the inputs and the software versions | `report.run` |

`validation_cards/` holds one Markdown card per task (`report.validation_card`).
`figures/` holds the figures, drawn from these tables only (`figures.py`).

## variantbench and txbench-pp

Written by `sc-zprime regrade`, for benchmarks that publish transcripts and
grader configs but no verdicts.

| File | One row is | Written by |
|---|---|---|
| `tasks.csv` | a task: its grader, runs, answers recovered, passes | `regrade.run` |
| `regrade_runs.csv` | a transcript: where its answer was recovered from, and its verdict | `regrade.run` |
| `regrade_fields.csv` | a graded field of a recovered answer: pass or fail, score band, reason | `regrade.run` |
| `summary.json` | the counts for the benchmark: answers recovered, passes, failures by reason | `regrade.run` |

## family

Written by `sc-zprime inventory`.

| File | One row is | Written by |
|---|---|---|
| `inventory.csv` | a benchmark repository: what it publishes | `inventory.run` |
| `failure_modes.csv` | a failure-mode label in a repository: tasks that carry it | `inventory.run` |
| `summary.json` | the totals across repositories | `inventory.run` |

`figures/` holds the inventory figure (`figures.py`).
