# Validation card: curio_ovary_cumulus_gc_count_immature

- Benchmark: spatialbench
- Category: cell_typing
- Platform: curio
- Grader: numeric_tolerance, 2 field(s), all must pass
- Evidence: 48 graded runs from 16 configurations, 3 repeats each
- Pass rate: 6.2%
- Verdicts reproduced by the independent grader: 48 of 48

## Flags

A flag prompts a look. It is not a verdict on the task, and the task's own notes may already explain it. Where they do, that is said under the flag.

- DEAD_READOUT: 1 of 2 graded fields are passed by at least 95% of runs; between them they decided 0 verdict(s) on their own

## Readouts

Window widths are a percentage of the reference value, to the nearest percent.

| field | kind | window_lower_pct_of_reference | window_upper_pct_of_reference | lower_edge_at_zero | pass_rate | distinct_answers | largest_cluster_share | dead | failures_involving_field | failures_from_field_alone |
|---|---|---|---|---|---|---|---|---|---|---|
| cumulus_count | absolute | >200 | >200 | yes | 0.062 | 47 | 0.042 | no | 45 | 44 |
| distinction_answer | exact | 0 | 0 | no | 0.979 | 2 | 0.979 | yes | 1 | 0 |

A window whose lower edge is at or below zero is a ceiling check: only the upper edge can be missed. The edge-sensitivity test below moves the upper edge and leaves the lower one where it is.

## Answer clusters

Three or more runs that submitted the identical value for a field with a tolerance window (answers are compared after rounding to six decimals; exact-match fields are not listed). Margin is in tolerance widths: 0 is the reference, 1 is the window edge.

_none_

## Edge sensitivity

0 of 48 verdicts flip if every tolerance is made 20% tighter or 25% wider.

## Repeatability

16 configurations: 0 passed every repeat, 14 failed every repeat, 2 split. 0 submitted the identical answer on every repeat.

