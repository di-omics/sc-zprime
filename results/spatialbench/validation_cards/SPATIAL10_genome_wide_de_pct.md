# Validation card: SPATIAL10_genome_wide_de_pct

- Benchmark: spatialbench
- Category: differential_expression
- Platform: atlasxomics
- Grader: numeric_tolerance, 1 field(s), all must pass
- Evidence: 48 graded runs from 16 configurations, 3 repeats each
- Pass rate: 0.0%
- Verdicts reproduced by the independent grader: 48 of 48

## Flags

A flag prompts a look. It is not a verdict on the task, and the task's own notes may already explain it. Where they do, that is said under the flag.

- none

## Readouts

Window widths are a percentage of the reference value, to the nearest percent.

| field | kind | window_lower_pct_of_reference | window_upper_pct_of_reference | lower_edge_at_zero | pass_rate | distinct_answers | largest_cluster_share | dead | failures_involving_field | failures_from_field_alone |
|---|---|---|---|---|---|---|---|---|---|---|
| pct_de | absolute | >200 | >200 | yes | 0 | 6 | 0.521 | no | 48 | 48 |

A window whose lower edge is at or below zero is a ceiling check: only the upper edge can be missed. The edge-sensitivity test below moves the upper edge and leaves the lower one where it is.

## Answer clusters

Three or more runs that submitted the identical value for a field with a tolerance window (answers are compared after rounding to six decimals; exact-match fields are not listed). Margin is in tolerance widths: 0 is the reference, 1 is the window edge.

| field | field_is_dead | runs | share_of_runs | configurations | providers | margin | field_passed | near_edge |
|---|---|---|---|---|---|---|---|---|
| pct_de | no | 25 | 0.521 | 11 | 4 | 11.58 | no | no |
| pct_de | no | 14 | 0.292 | 7 | 3 | 11.44 | no | no |
| pct_de | no | 4 | 0.083 | 2 | 2 | 11.58 | no | no |
| pct_de | no | 3 | 0.062 | 1 | 1 | 11.44 | no | no |

## Edge sensitivity

0 of 48 verdicts flip if every tolerance is made 20% tighter or 25% wider.

## Repeatability

16 configurations: 0 passed every repeat, 16 failed every repeat, 0 split. 10 submitted the identical answer on every repeat.

