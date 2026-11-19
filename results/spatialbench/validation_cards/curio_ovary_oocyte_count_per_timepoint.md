# Validation card: curio_ovary_oocyte_count_per_timepoint

- Benchmark: spatialbench
- Category: cell_typing
- Platform: curio
- Grader: numeric_tolerance, 9 field(s), all must pass
- Evidence: 48 graded runs from 16 configurations, 3 repeats each
- Pass rate: 12.5%
- Verdicts reproduced by the independent grader: 48 of 48

## Flags

A flag prompts a look. It is not a verdict on the task, and the task's own notes may already explain it. Where they do, that is said under the flag.

- EDGE_CLUSTER: 3 cluster(s) of identical answers, 12 runs in all, sit within 20% inside or 25% outside a window edge
- UNSTABLE_REPEATS: 5 of 16 configurations gave different verdicts across repeats

## Readouts

Window widths are a percentage of the reference value, to the nearest percent.

| field | kind | window_lower_pct_of_reference | window_upper_pct_of_reference | lower_edge_at_zero | pass_rate | distinct_answers | largest_cluster_share | dead | failures_involving_field | failures_from_field_alone |
|---|---|---|---|---|---|---|---|---|---|---|
| trend_answer | exact | 0 | 0 | no | 0.854 | 3 | 0.854 | no | 7 | 0 |
| 0hr_oocyte_count | absolute | 73 | 73 | no | 0.396 | 43 | 0.083 | no | 29 | 0 |
| 1hr_oocyte_count | absolute | 70 | 70 | no | 0.771 | 45 | 0.083 | no | 11 | 0 |
| 4hr_oocyte_count | absolute | 78 | 78 | no | 0.812 | 43 | 0.104 | no | 9 | 0 |
| 6hr_oocyte_count | absolute | 68 | 68 | no | 0.417 | 45 | 0.083 | no | 28 | 0 |
| 8hr_oocyte_count | absolute | 75 | 75 | no | 0.583 | 43 | 0.083 | no | 20 | 0 |
| 11hr_oocyte_count | absolute | 71 | 71 | no | 0.562 | 44 | 0.083 | no | 21 | 0 |
| 12hr_oocyte_count | absolute | withheld | withheld | no | 0.708 | 38 | 0.104 | no | 14 | 3 |
| immature_oocyte_count | absolute | 41 | 41 | no | 0.188 | 44 | 0.083 | no | 39 | 2 |

A width is withheld for a whole-number field with a small tolerance, where it would give the reference away (docs/DATA_POLICY.md).

## Answer clusters

Three or more runs that submitted the identical value for a field with a tolerance window (answers are compared after rounding to six decimals; exact-match fields are not listed). Margin is in tolerance widths: 0 is the reference, 1 is the window edge.

| field | field_is_dead | runs | share_of_runs | configurations | providers | margin | field_passed | near_edge |
|---|---|---|---|---|---|---|---|---|
| 0hr_oocyte_count | no | 4 | 0.083 | 3 | 3 | 0.95 | yes | yes |
| 11hr_oocyte_count | no | 4 | 0.083 | 3 | 3 | 0.52 | yes | no |
| 12hr_oocyte_count | no | 5 | 0.104 | 4 | 3 | -1.33 | no | no |
| 12hr_oocyte_count | no | 4 | 0.083 | 3 | 3 | -1.11 | no | yes |
| 1hr_oocyte_count | no | 4 | 0.083 | 3 | 3 | 0.1 | yes | no |
| 4hr_oocyte_count | no | 5 | 0.104 | 4 | 3 | 0.34 | yes | no |
| 6hr_oocyte_count | no | 4 | 0.083 | 3 | 3 | 1.63 | no | no |
| 8hr_oocyte_count | no | 4 | 0.083 | 3 | 3 | 1.15 | no | yes |
| immature_oocyte_count | no | 4 | 0.083 | 3 | 3 | 3.01 | no | no |

## Edge sensitivity

8 of 48 verdicts flip if every tolerance is made 20% tighter or 25% wider.

## Repeatability

16 configurations: 0 passed every repeat, 11 failed every repeat, 5 split. 0 submitted the identical answer on every repeat.

