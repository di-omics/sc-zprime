# Validation card: T04a_endothelin_niche_sources

- Benchmark: scbench
- Category: cell_typing
- Platform: illumina-snrna
- Grader: numeric_tolerance, 2 field(s), all must pass
- Evidence: 33 graded runs from 11 configurations, 3 repeats each
- Pass rate: 54.5%
- Verdicts reproduced by the independent grader: 33 of 33

## Flags

A flag prompts a look. It is not a verdict on the task, and the task's own notes may already explain it. Where they do, that is said under the flag.

- DEAD_READOUT: 1 of 2 graded fields are passed by at least 95% of runs; between them they decided 1 verdict(s) on their own
- UNSTABLE_REPEATS: 5 of 11 configurations gave different verdicts across repeats

## Readouts

Window widths are a percentage of the reference value, to the nearest percent.

| field | kind | window_lower_pct_of_reference | window_upper_pct_of_reference | lower_edge_at_zero | pass_rate | distinct_answers | largest_cluster_share | dead | failures_involving_field | failures_from_field_alone |
|---|---|---|---|---|---|---|---|---|---|---|
| interpretation | exact | 0 | 0 | no | 0.576 | 4 | 0.576 | no | 14 | 14 |
| mural_nuclei | absolute | withheld | withheld | yes | 0.97 | 2 | 0.97 | yes | 1 | 1 |

A width is withheld for a whole-number field with a small tolerance, where it would give the reference away (docs/DATA_POLICY.md).

A window whose lower edge is at or below zero is a ceiling check: only the upper edge can be missed. The edge-sensitivity test below moves the upper edge and leaves the lower one where it is.

## Answer clusters

Three or more runs that submitted the identical value for a field with a tolerance window (answers are compared after rounding to six decimals; exact-match fields are not listed). Margin is in tolerance widths: 0 is the reference, 1 is the window edge.

| field | field_is_dead | runs | share_of_runs | configurations | providers | margin | field_passed | near_edge |
|---|---|---|---|---|---|---|---|---|
| mural_nuclei | yes | 32 | 0.97 | 11 | 3 | inside | yes | no |

For a whole-number field with a tolerance under 10 the margin is given as a zone, not a number: its margins would fall on a grid that shows the tolerance (docs/DATA_POLICY.md). Near an edge means within 20% inside it or 25% outside it.

## Edge sensitivity

0 of 33 verdicts flip if every tolerance is made 20% tighter or 25% wider.

## Repeatability

11 configurations: 3 passed every repeat, 3 failed every repeat, 5 split. 6 submitted the identical answer on every repeat.

