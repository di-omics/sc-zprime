# Validation card: bd_rhapsody_tnbc_panel_aware_qc

- Benchmark: scbench
- Category: qc
- Platform: bd_rhapsody
- Grader: numeric_tolerance, 3 field(s), all must pass
- Evidence: 48 graded runs from 16 configurations, 3 repeats each
- Pass rate: 75.0%
- Verdicts reproduced by the independent grader: 48 of 48

## Flags

A flag prompts a look. It is not a verdict on the task, and the task's own notes may already explain it. Where they do, that is said under the flag.

- EDGE_CLUSTER: 2 cluster(s) of identical answers, 17 runs in all, sit within 20% inside or 25% outside a window edge
- UNSTABLE_REPEATS: 5 of 16 configurations gave different verdicts across repeats

## Readouts

Window widths are a percentage of the reference value, to the nearest percent.

| field | kind | window_lower_pct_of_reference | window_upper_pct_of_reference | lower_edge_at_zero | pass_rate | distinct_answers | largest_cluster_share | dead | failures_involving_field | failures_from_field_alone |
|---|---|---|---|---|---|---|---|---|---|---|
| median_genes_per_pbmc | absolute | withheld | withheld | no | 0.792 | 9 | 0.333 | no | 10 | 3 |
| n_monocytes_pbmc | absolute | 39 | 39 | no | 0.938 | 41 | 0.062 | no | 3 | 0 |
| n_pbmcs_retained | absolute | 6 | 6 | no | 0.833 | 29 | 0.146 | no | 8 | 2 |

A width is withheld for a whole-number field with a small tolerance, where it would give the reference away (docs/DATA_POLICY.md).

## Answer clusters

Three or more runs that submitted the identical value for a field with a tolerance window (answers are compared after rounding to six decimals; exact-match fields are not listed). Margin is in tolerance widths: 0 is the reference, 1 is the window edge.

| field | field_is_dead | runs | share_of_runs | configurations | providers | margin | field_passed | near_edge |
|---|---|---|---|---|---|---|---|---|
| median_genes_per_pbmc | no | 16 | 0.333 | 10 | 4 | inside | yes | no |
| median_genes_per_pbmc | no | 13 | 0.271 | 9 | 4 | inside, near the upper edge | yes | yes |
| median_genes_per_pbmc | no | 7 | 0.146 | 5 | 3 | inside | yes | no |
| median_genes_per_pbmc | no | 4 | 0.083 | 4 | 3 | above, near the edge | no | yes |
| n_monocytes_pbmc | no | 3 | 0.062 | 2 | 2 | -0.33 | yes | no |
| n_pbmcs_retained | no | 7 | 0.146 | 6 | 3 | 0.06 | yes | no |
| n_pbmcs_retained | no | 6 | 0.125 | 3 | 3 | 0.25 | yes | no |
| n_pbmcs_retained | no | 3 | 0.062 | 2 | 2 | 0.01 | yes | no |
| n_pbmcs_retained | no | 3 | 0.062 | 3 | 3 | 0.09 | yes | no |

For a whole-number field with a tolerance under 10 the margin is given as a zone, not a number: its margins would fall on a grid that shows the tolerance (docs/DATA_POLICY.md). Near an edge means within 20% inside it or 25% outside it.

## Edge sensitivity

17 of 48 verdicts flip if every tolerance is made 20% tighter or 25% wider.

## Repeatability

16 configurations: 9 passed every repeat, 2 failed every repeat, 5 split. 0 submitted the identical answer on every repeat.

