# Validation card: curio_ovary_follicle_count_immature

- Benchmark: spatialbench
- Category: cell_typing
- Platform: curio
- Grader: numeric_tolerance, 1 field(s), all must pass
- Evidence: 48 graded runs from 16 configurations, 3 repeats each
- Pass rate: 25.0%
- Verdicts reproduced by the independent grader: 48 of 48

## Flags

A flag prompts a look. It is not a verdict on the task, and the task's own notes may already explain it. Where they do, that is said under the flag.

- UNSTABLE_REPEATS: 7 of 16 configurations gave different verdicts across repeats

## Readouts

Window widths are a percentage of the reference value, to the nearest percent.

| field | kind | window_lower_pct_of_reference | window_upper_pct_of_reference | lower_edge_at_zero | pass_rate | distinct_answers | largest_cluster_share | dead | failures_involving_field | failures_from_field_alone |
|---|---|---|---|---|---|---|---|---|---|---|
| follicle_count | absolute | withheld | withheld | no | 0.25 | 42 | 0.083 | no | 36 | 36 |

A width is withheld for a whole-number field with a small tolerance, where it would give the reference away (docs/DATA_POLICY.md).

## Answer clusters

Three or more runs that submitted the identical value for a field with a tolerance window (answers are compared after rounding to six decimals; exact-match fields are not listed). Margin is in tolerance widths: 0 is the reference, 1 is the window edge.

| field | field_is_dead | runs | share_of_runs | configurations | providers | margin | field_passed | near_edge |
|---|---|---|---|---|---|---|---|---|
| follicle_count | no | 4 | 0.085 | 3 | 2 | -1.45 | no | no |

## Edge sensitivity

6 of 48 verdicts flip if every tolerance is made 20% tighter or 25% wider.

## Repeatability

16 configurations: 1 passed every repeat, 8 failed every repeat, 7 split. 0 submitted the identical answer on every repeat.

