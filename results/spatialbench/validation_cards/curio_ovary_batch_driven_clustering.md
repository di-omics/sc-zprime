# Validation card: curio_ovary_batch_driven_clustering

- Benchmark: spatialbench
- Category: clustering
- Platform: curio
- Grader: numeric_tolerance, 1 field(s), all must pass
- Evidence: 48 graded runs from 16 configurations, 3 repeats each
- Pass rate: 4.2%
- Verdicts reproduced by the independent grader: 48 of 48

## Flags

A flag prompts a look. It is not a verdict on the task, and the task's own notes may already explain it. Where they do, that is said under the flag.

- NO_POSITIVE_CONTROL_IN_RUNS: no run of the 48 traced is labelled as submitting an answer from an intended method, so these runs cannot show whether the intended method passes (sensitivity is not measured)
  - What the task notes say: the notes predict that a naive agent will cluster without integrating and land above the window. They list passing values for a corrected pipeline from the authors' own analysis. No published agent run submitted a corrected answer to set beside them.
- TRAP_PASSES: 1 of 47 runs that used a method the task notes name as incorrect passed
  - What the task notes say: the notes expect an uncorrected clustering to land well above the window. The run that passes clustered every bead with no on-tissue filter, which the notes list as a separate trap, and its submitted maximum comes from a cluster of fewer than 20 beads (read from the transcript by AI models; not produced by the tool).

## Readouts

Window widths are a percentage of the reference value, to the nearest percent.

| field | kind | window_lower_pct_of_reference | window_upper_pct_of_reference | lower_edge_at_zero | pass_rate | distinct_answers | largest_cluster_share | dead | failures_involving_field | failures_from_field_alone |
|---|---|---|---|---|---|---|---|---|---|---|
| max_single_timepoint_fraction | absolute | 60 | 60 | no | 0.042 | 41 | 0.125 | no | 46 | 46 |

## Answer clusters

Three or more runs that submitted the identical value for a field with a tolerance window (answers are compared after rounding to six decimals; exact-match fields are not listed). Margin is in tolerance widths: 0 is the reference, 1 is the window edge.

| field | field_is_dead | runs | share_of_runs | configurations | providers | margin | field_passed | near_edge |
|---|---|---|---|---|---|---|---|---|
| max_single_timepoint_fraction | no | 6 | 0.125 | 5 | 2 | 2.78 | no | no |
| max_single_timepoint_fraction | no | 3 | 0.062 | 3 | 2 | 1.89 | no | no |

## Edge sensitivity

2 of 48 verdicts flip if every tolerance is made 20% tighter or 25% wider.

## Repeatability

16 configurations: 0 passed every repeat, 14 failed every repeat, 2 split. 0 submitted the identical answer on every repeat.

## Method separation

Traced field: `max_single_timepoint_fraction`. Basis for the tiers: task notes, sections 2, 3, 4 and 6.

- intended: applies a batch-correction method on the timepoint key before clustering (the notes name Harmony, BBKNN and Scanorama, and say other correction methods land in the same range)
- trap: clusters with no correction for timepoint, or regresses a covariate out and stops there (the notes' first two named traps)
- other: variable genes chosen within each timepoint with no correction of the embedding (not mentioned in the notes; this analysis' label)

By method:

| tier | method | runs | passes | configurations | median_margin | pass_rate |
|---|---|---|---|---|---|---|
| trap | no sample handling | 47 | 1 | 16 | 2.54 | 0.021 |
| other | sample-aware gene selection only | 1 | 1 | 1 | 0.93 | 1 |

By configuration (one model in one harness; its three repeats are not independent):

| tier | runs | runs_passed | configurations | configurations_with_a_pass | configurations_passing_every_time | providers |
|---|---|---|---|---|---|---|
| trap | 47 | 1 | 16 | 1 | 0 | 4 |
| other | 1 | 1 | 1 | 1 | 1 | 1 |

The pass window as a test of method (whole-run verdicts):

- Specificity, trap-method runs that fail: 46 of 47 (98%; 95% interval 94% to 100%)
- Passing runs that used a trap method: 1 of 2; no interval, because fewer than 3 configurations stand behind it

Each named trap method as its own negative control. Z-prime is the classic mean and SD form, computed on the traced field against the intended-method answers. It is a rough summary here: answers come in clusters of identical values and the pass window has two edges, so a negative value can occur with no answer of one method lying among the answers of the other, and two controls with no spread score exactly 1 however close they are. Read it with the margins above.

| trap_method | runs | configurations | providers | runs_passed | configurations_with_a_pass | lowest_margin | median_margin | highest_margin | distinct_answers | zprime_against_intended | zprime_note | zprime_95pct_interval | resamples_where_zprime_is_defined |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| no sample handling | 47 | 16 | 4 | 1 | 1 | 0.28 | 2.54 | 2.78 | 40 | n/a | needs at least 3 runs in each control |  |  |

- Runs that ran an intended method at some step but submitted a different method's number: 0
- Labels: 28 traced from the printed value, 18 from the last classifiable step, 2 set by reading the transcript in full. An AI model then read the runs that ran a correction, the runs that passed and the runs the rules could not label, and a second AI model searched every transcript of these tasks for a correction method and read a sample of the rest. No blind re-rating and no person has checked the labels.
- Intervals are 95% cluster-bootstrap percentile intervals that resample whole configurations. With this few configurations they are approximate and probably too narrow.

