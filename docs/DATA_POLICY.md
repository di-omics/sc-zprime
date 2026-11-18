# Data policy

The upstream task files carry a canary string asking that benchmark data
never appear in training corpora. The authors withhold most of their tasks
for the same reason. This repository is built to respect that.

## What is not in this repository

- no task prompt
- no reference answer, tolerance, or answer submitted by any model
- no agent transcript or excerpt from one
- no copy of any upstream file, and no upstream code

`tests/test_data_policy.py` checks part of this. It fails if a reference
value, tolerance or submitted answer with four or more significant digits
appears in a tracked file outside the generated result tables, or if a canary
identifier or an opening sentence of a task prompt appears anywhere. Values
with fewer than four significant digits, which includes most tolerances,
cannot be checked this way: they would match ordinary numbers. The result
tables are kept clean by construction, since the report writer drops the
value columns before it writes.

## What is

- code that reads an upstream checkout you fetch yourself
- result tables holding normalised quantities:
  - **margin**: (submitted value minus reference) divided by the tolerance
    width, rounded to two decimals
  - window width as a percentage of the reference, rounded to a whole percent
  - rates and counts
  - method labels and the transcript step index that supports each one
- task identifiers, field names, model names and harness names, taken from
  the public upstream task files, README and results tables
- published leaderboard accuracies and intervals, which are results, not
  task content

## What the normalisation does and does not protect

A margin does not state the reference or the answer. It is not a guarantee
that they cannot be worked out. Submitted answers are often whole numbers, and
with enough margins for one field, at high enough precision, the tolerance and
then the reference can be solved for. An audit of the first version of this
repository did exactly that from margins published to four decimals.

Margins are now rounded to two decimals and per-run margins outside the traced
tasks are no longer published. That makes reconstruction impractical for most
fields. For a field with a small whole-number tolerance, the tolerance itself
can still be inferred. All of these values are public in the upstream
repository, which is where anyone wanting them would look. The aim here is
narrower: this repository should not be a second place where benchmark
answers can be read off.

## Where the line is

The method specs under `src/sc_zprime/methods/` say which function calls
identify each analysis method for the three traced tasks, and
`docs/FINDINGS.md` says which methods pass. Someone could use that to choose a
passing method for those three public tasks. Their answers and design notes
are already public upstream, so this adds little, but it is more than
"method families" and is stated here plainly.

The findings paraphrase the authors' design notes where that is needed to say
what a task intends. They do not quote them.

The upstream harness and grader library (`latchbio/latch-eval-tools`) is
publicly readable but its licence reserves all rights. Its source was read to
understand the grader's behaviour, and the grader here mirrors that
behaviour, including which configurations are rejected. None of the upstream
code is copied or redistributed. scBench itself is Apache-2.0.

## If you hold a private benchmark

The tool runs on a checkout in the same layout whose tasks use the numeric
tolerance grader. Tasks with other grader types are skipped and listed in the
summary. Be aware that a validation card names the traced field and the method
labels, so cards for private tasks reveal something about them. Share the
aggregate tables and keep the cards and method specs private.
