# Validation card: xenium_kidney_spatial_fibro_inflammatory_niche_emergence_2

- Benchmark: spatialbench
- Category: spatial_analysis
- Platform: xenium
- Grader: numeric_tolerance, 4 field(s), all must pass
- Evidence: 48 graded runs from 16 configurations, 3 repeats each
- Pass rate: 0.0%
- Verdicts reproduced by the independent grader: 48 of 48

## Flags

A flag prompts a look. It is not a verdict on the task, and the task's own notes may already explain it. Where they do, that is said under the flag.

- DEAD_READOUT: 1 of 4 graded fields are passed by at least 95% of runs; between them they decided 0 verdict(s) on their own

## Readouts

Window widths are a percentage of the reference value, to the nearest percent.

| field | kind | window_lower_pct_of_reference | window_upper_pct_of_reference | lower_edge_at_zero | pass_rate | distinct_answers | largest_cluster_share | dead | failures_involving_field | failures_from_field_alone |
|---|---|---|---|---|---|---|---|---|---|---|
| fold_increase | absolute | 22 | 22 | no | 0.021 | 48 | 0.021 | no | 47 | 0 |
| mean_coloc_sham | absolute | 30 | 30 | no | 0.021 | 48 | 0.021 | no | 47 | 0 |
| peak_time_index | exact | 0 | 0 | no | 0.958 | 2 | 0.958 | yes | 2 | 0 |
| mean_coloc_day14 | absolute | 24 | 24 | no | 0.125 | 48 | 0.021 | no | 42 | 0 |

## Answer clusters

Three or more runs that submitted the identical value for a field with a tolerance window (answers are compared after rounding to six decimals; exact-match fields are not listed). Margin is in tolerance widths: 0 is the reference, 1 is the window edge.

_none_

## Edge sensitivity

0 of 48 verdicts flip if every tolerance is made 20% tighter or 25% wider.

## Repeatability

16 configurations: 0 passed every repeat, 16 failed every repeat, 0 split. 0 submitted the identical answer on every repeat.

