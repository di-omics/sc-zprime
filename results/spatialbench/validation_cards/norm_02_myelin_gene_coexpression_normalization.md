# Validation card: norm_02_myelin_gene_coexpression_normalization

- Benchmark: spatialbench
- Category: normalization
- Platform: merfish
- Grader: numeric_tolerance, 1 field(s), all must pass
- Evidence: 48 graded runs from 16 configurations, 3 repeats each
- Pass rate: 16.7%
- Verdicts reproduced by the independent grader: 48 of 48

## Flags

A flag prompts a look. It is not a verdict on the task, and the task's own notes may already explain it. Where they do, that is said under the flag.

- UNSTABLE_REPEATS: 4 of 16 configurations gave different verdicts across repeats

## Readouts

Window widths are a percentage of the reference value, to the nearest percent.

| field | kind | window_lower_pct_of_reference | window_upper_pct_of_reference | lower_edge_at_zero | pass_rate | distinct_answers | largest_cluster_share | dead | failures_involving_field | failures_from_field_alone |
|---|---|---|---|---|---|---|---|---|---|---|
| spearman_mbp_plp1 | absolute | 19 | 19 | no | 0.167 | 8 | 0.646 | no | 40 | 40 |

## Answer clusters

Three or more runs that submitted the identical value for a field with a tolerance window (answers are compared after rounding to six decimals; exact-match fields are not listed). Margin is in tolerance widths: 0 is the reference, 1 is the window edge.

| field | field_is_dead | runs | share_of_runs | configurations | providers | margin | field_passed | near_edge |
|---|---|---|---|---|---|---|---|---|
| spearman_mbp_plp1 | no | 31 | 0.646 | 14 | 4 | -7.74 | no | no |
| spearman_mbp_plp1 | no | 5 | 0.104 | 3 | 2 | 0.3 | yes | no |
| spearman_mbp_plp1 | no | 4 | 0.083 | 2 | 1 | -7.74 | no | no |
| spearman_mbp_plp1 | no | 3 | 0.062 | 3 | 1 | -7.74 | no | no |

## Edge sensitivity

0 of 48 verdicts flip if every tolerance is made 20% tighter or 25% wider.

## Repeatability

16 configurations: 0 passed every repeat, 12 failed every repeat, 4 split. 8 submitted the identical answer on every repeat.

