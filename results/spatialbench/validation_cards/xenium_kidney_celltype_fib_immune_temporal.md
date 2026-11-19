# Validation card: xenium_kidney_celltype_fib_immune_temporal

- Benchmark: spatialbench
- Category: cell_typing
- Platform: xenium
- Grader: numeric_tolerance, 4 field(s), all must pass
- Evidence: 48 graded runs from 16 configurations, 3 repeats each
- Pass rate: 35.4%
- Verdicts reproduced by the independent grader: 48 of 48

## Flags

A flag prompts a look. It is not a verdict on the task, and the task's own notes may already explain it. Where they do, that is said under the flag.

- DEAD_READOUT: 1 of 4 graded fields are passed by at least 95% of runs; between them they decided 0 verdict(s) on their own
- UNSTABLE_REPEATS: 6 of 16 configurations gave different verdicts across repeats

## Readouts

Window widths are a percentage of the reference value, to the nearest percent.

| field | kind | window_lower_pct_of_reference | window_upper_pct_of_reference | lower_edge_at_zero | pass_rate | distinct_answers | largest_cluster_share | dead | failures_involving_field | failures_from_field_alone |
|---|---|---|---|---|---|---|---|---|---|---|
| fib_peak_pct | absolute | withheld | withheld | no | 0.646 | 41 | 0.125 | no | 17 | 3 |
| immune_peak_pct | absolute | 28 | 28 | no | 0.562 | 41 | 0.125 | no | 21 | 1 |
| fib_peak_time_index | exact | 0 | 0 | no | 0.479 | 4 | 0.479 | no | 25 | 6 |
| immune_peak_time_index | exact | 0 | 0 | no | 0.958 | 3 | 0.958 | yes | 2 | 0 |

A width is withheld for a whole-number field with a small tolerance, where it would give the reference away (docs/DATA_POLICY.md).

## Answer clusters

Three or more runs that submitted the identical value for a field with a tolerance window (answers are compared after rounding to six decimals; exact-match fields are not listed). Margin is in tolerance widths: 0 is the reference, 1 is the window edge.

| field | field_is_dead | runs | share_of_runs | configurations | providers | margin | field_passed | near_edge |
|---|---|---|---|---|---|---|---|---|
| fib_peak_pct | no | 6 | 0.125 | 5 | 2 | inside | yes | no |
| immune_peak_pct | no | 6 | 0.125 | 5 | 2 | -0.52 | yes | no |

For a whole-number field with a tolerance under 10 the margin is given as a zone, not a number: its margins would fall on a grid that shows the tolerance (docs/DATA_POLICY.md). Near an edge means within 20% inside it or 25% outside it.

## Edge sensitivity

0 of 48 verdicts flip if every tolerance is made 20% tighter or 25% wider.

## Repeatability

16 configurations: 2 passed every repeat, 8 failed every repeat, 6 split. 0 submitted the identical answer on every repeat.

