# Independent validation of the method labels

The method tracer in `src/sc_zprime/methods/` decides which analysis method
produced each submitted answer. Every result about method separation rests on
those labels, so they were checked by a blind re-rating.

## Protocol

- **Raters.** Independent AI raters, each a fresh session with no access to
  the tracer, its rules, its output, the labels set by reading, the task authors'
  design notes, or any pass or fail verdict. Each read the raw transcript and
  the submitted answer for four runs and labelled the method from the code
  that was run and the output it printed.
- **Taxonomy.** Each task had a fixed list of method labels with written
  definitions, plus "other" and "cannot determine". The list was written for
  this analysis, so the raters were blind to the tool's answers but shared
  its vocabulary.
- **Coverage.** All 144 traced runs. The 48 differential expression runs,
  which carry the main finding, were each labelled by two independent raters.
  That is 192 independent ratings.
- **Second question.** Each rater also recorded whether the run executed an
  intended-family method at some other step than the one behind the
  submitted answer.
- **Adjudication.** Any run where a rater disagreed with the tool on either
  question, or was not confident, went to two further independent
  adjudicators who were shown the candidate labels without their source.

## Result

| | |
|---|---|
| Method labels where every rater agreed with the tool | 144 of 144 |
| Differential expression runs where both raters agreed with each other | 48 of 48 |
| Runs sent to adjudication over the method label | 0 |
| Runs sent to adjudication over the second question | 2 |

On the second question the tool had missed two runs in which the intended
method was executed inside a script that swept several pipelines at once. Both
adjudicators confirmed the raters. The detector was loosened to count such
scripts and now matches the adjudicated answer on all 144 runs. The published
count rose from 13 to 15.

Four labels had been set by reading the transcript in full, not by rule, in
the first version, three of them moving a run from one tier to another. The raters never saw those labels and reached
the same ones.

## What this does and does not show

It shows that an independent reading of the transcripts reaches the same
method label as the rules, for every traced run. It does not show that the
tiers assigned to those methods (intended, partial, trap) are right. Tiers
follow the task authors' design notes and are a separate question.

The raters were AI models. A check by a human analyst on a sample of runs is
still worth doing and has not been done.

## Files

`blind_rerating.csv` holds one row per run: each rater's label, the
adjudicated label, and the adjudicated answer to the second question. It
contains no benchmark answer. `tests/test_upstream.py` asserts that the
tracer agrees with it.

## SpatialBench

The method labels for the 3 SpatialBench batch-correction tasks have not
been through this protocol. They were set by rule, read in part by one AI
model, and then reviewed by a second AI model that searched every transcript
of those tasks for a correction method (see `docs/SPATIALBENCH.md`, section
5). That is a review, not a blind re-rating, and no person has checked the
labels.

`spatialbench_closing_messages.csv` is not a rating. It is the output of
`scripts/closing_messages.py`: for each of those 3 tasks, how many runs
store a last message that names a batch effect, and from which providers. It
is a keyword match. Some transcripts store no assistant text, and in some
the last stored text is an opening plan. How many store any differs by
provider, so the table also gives, for each provider, its runs, its runs
with any assistant text and the median length of the last stored text.

## Answer recovery

`answer_recovery.csv` is the output of `scripts/answer_recovery_check.py`.
For the 3 benchmarks that publish each run's answer next to its transcript,
it counts, by harness, how often `sc_zprime.answers` recovers the answer from
the transcript alone and how often the recovered answer equals the published
one. `tests/test_upstream.py` regenerates it.
