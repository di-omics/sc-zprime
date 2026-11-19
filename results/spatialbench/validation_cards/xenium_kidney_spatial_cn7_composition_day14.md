# Validation card: xenium_kidney_spatial_cn7_composition_day14

- Benchmark: spatialbench
- Category: spatial_analysis
- Platform: xenium
- Grader: numeric_tolerance, 4 field(s), all must pass
- Evidence: 48 graded runs from 16 configurations, 3 repeats each
- Pass rate: 91.7%
- Verdicts reproduced by the independent grader: 48 of 48

## Flags

A flag prompts a look. It is not a verdict on the task, and the task's own notes may already explain it. Where they do, that is said under the flag.

- DEAD_READOUT: 3 of 4 graded fields are passed by at least 95% of runs; between them they decided 1 verdict(s) on their own

## Readouts

Window widths are a percentage of the reference value, to the nearest percent.

| field | kind | window_lower_pct_of_reference | window_upper_pct_of_reference | lower_edge_at_zero | pass_rate | distinct_answers | largest_cluster_share | dead | failures_involving_field | failures_from_field_alone |
|---|---|---|---|---|---|---|---|---|---|---|
| assessment | exact | 0 | 0 | no | 1 | 1 | 1 | yes | 0 | 0 |
| fib_enrichment | absolute | 36 | 36 | no | 1 | 4 | 0.625 | yes | 0 | 0 |
| fr_pt_enrichment | absolute | 30 | 30 | no | 0.979 | 5 | 0.604 | yes | 1 | 1 |
| pct_top1_celltype | absolute | 11 | 11 | no | 0.938 | 4 | 0.562 | no | 3 | 3 |

## Answer clusters

Three or more runs that submitted the identical value for a field with a tolerance window (answers are compared after rounding to six decimals; exact-match fields are not listed). Margin is in tolerance widths: 0 is the reference, 1 is the window edge.

| field | field_is_dead | runs | share_of_runs | configurations | providers | margin | field_passed | near_edge |
|---|---|---|---|---|---|---|---|---|
| fib_enrichment | yes | 30 | 0.625 | 11 | 4 | 0.01 | yes | no |
| fib_enrichment | yes | 13 | 0.271 | 6 | 2 | 0 | yes | no |
| fib_enrichment | yes | 4 | 0.083 | 3 | 1 | 0.01 | yes | no |
| fr_pt_enrichment | yes | 29 | 0.604 | 11 | 4 | 0 | yes | no |
| fr_pt_enrichment | yes | 13 | 0.271 | 6 | 2 | 0 | yes | no |
| fr_pt_enrichment | yes | 4 | 0.083 | 3 | 1 | 0 | yes | no |
| pct_top1_celltype | no | 27 | 0.562 | 11 | 4 | -0 | yes | no |
| pct_top1_celltype | no | 15 | 0.312 | 6 | 2 | 0 | yes | no |
| pct_top1_celltype | no | 3 | 0.062 | 2 | 2 | -8.81 | no | no |
| pct_top1_celltype | no | 3 | 0.062 | 2 | 1 | -0 | yes | no |

## Edge sensitivity

0 of 48 verdicts flip if every tolerance is made 20% tighter or 25% wider.

## Repeatability

16 configurations: 13 passed every repeat, 0 failed every repeat, 3 split. 9 submitted the identical answer on every repeat.

