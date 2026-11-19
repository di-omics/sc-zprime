# Validation card: SPATIAL07_sex_housekeeping_de

- Benchmark: spatialbench
- Category: spatial_analysis
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
| n_significant | absolute | withheld | withheld | yes | 0 | 2 | 0.5 | no | 48 | 48 |

A width is withheld for a whole-number field with a small tolerance, where it would give the reference away (docs/DATA_POLICY.md).

A window whose lower edge is at or below zero is a ceiling check: only the upper edge can be missed. The edge-sensitivity test below moves the upper edge and leaves the lower one where it is.

## Answer clusters

Three or more runs that submitted the identical value for a field with a tolerance window (answers are compared after rounding to six decimals; exact-match fields are not listed). Margin is in tolerance widths: 0 is the reference, 1 is the window edge.

| field | field_is_dead | runs | share_of_runs | configurations | providers | margin | field_passed | near_edge |
|---|---|---|---|---|---|---|---|---|
| n_significant | no | 24 | 0.5 | 11 | 4 | above, clear of the edge | no | no |
| n_significant | no | 24 | 0.5 | 12 | 4 | above, clear of the edge | no | no |

For a whole-number field with a tolerance under 10 the margin is given as a zone, not a number: its margins would fall on a grid that shows the tolerance (docs/DATA_POLICY.md). Near an edge means within 20% inside it or 25% outside it.

## Edge sensitivity

0 of 48 verdicts flip if every tolerance is made 20% tighter or 25% wider.

## Repeatability

16 configurations: 0 passed every repeat, 16 failed every repeat, 0 split. 9 submitted the identical answer on every repeat.

