# Validation card: norm_01_opc_olig_maturation_foldchange

- Benchmark: spatialbench
- Category: normalization
- Platform: merfish
- Grader: numeric_tolerance, 1 field(s), all must pass
- Evidence: 48 graded runs from 16 configurations, 3 repeats each
- Pass rate: 2.1%
- Verdicts reproduced by the independent grader: 48 of 48

## Flags

A flag prompts a look. It is not a verdict on the task, and the task's own notes may already explain it. Where they do, that is said under the flag.

- none

## Readouts

Window widths are a percentage of the reference value, to the nearest percent.

| field | kind | window_lower_pct_of_reference | window_upper_pct_of_reference | lower_edge_at_zero | pass_rate | distinct_answers | largest_cluster_share | dead | failures_involving_field | failures_from_field_alone |
|---|---|---|---|---|---|---|---|---|---|---|
| log2fc_mbp_olig_vs_opc | absolute | 8 | 8 | no | 0.021 | 11 | 0.333 | no | 47 | 47 |

## Answer clusters

Three or more runs that submitted the identical value for a field with a tolerance window (answers are compared after rounding to six decimals; exact-match fields are not listed). Margin is in tolerance widths: 0 is the reference, 1 is the window edge.

| field | field_is_dead | runs | share_of_runs | configurations | providers | margin | field_passed | near_edge |
|---|---|---|---|---|---|---|---|---|
| log2fc_mbp_olig_vs_opc | no | 16 | 0.333 | 7 | 3 | -1.73 | no | no |
| log2fc_mbp_olig_vs_opc | no | 9 | 0.188 | 5 | 4 | -1.73 | no | no |
| log2fc_mbp_olig_vs_opc | no | 9 | 0.188 | 5 | 3 | 6.75 | no | no |
| log2fc_mbp_olig_vs_opc | no | 5 | 0.104 | 3 | 2 | 5.67 | no | no |
| log2fc_mbp_olig_vs_opc | no | 3 | 0.062 | 1 | 1 | -1.74 | no | no |

## Edge sensitivity

0 of 48 verdicts flip if every tolerance is made 20% tighter or 25% wider.

## Repeatability

16 configurations: 0 passed every repeat, 15 failed every repeat, 1 split. 8 submitted the identical answer on every repeat.

