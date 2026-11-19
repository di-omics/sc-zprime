# Data policy

The upstream task files carry a canary string asking that benchmark data
never appear in training corpora. The authors withhold most of their tasks
for the same reason. This repository is built to respect that.

## What is not in this repository

- no task prompt
- no reference answer, reference label, tolerance, or answer submitted by any model
- no agent transcript or excerpt from one
- no copy of any upstream file, and no upstream code

`tests/test_data_policy.py` checks part of this. It fails if a reference
value, tolerance or submitted answer with 4 or more significant digits
appears in a tracked file outside the generated result tables, or if a canary
identifier, an opening sentence of a task prompt, or a reference label of 6
or more characters appears anywhere. It reads the task files of the 4
benchmarks analysed here. Values with fewer than 4 significant digits, which
includes most tolerances, cannot be checked this way: they would match
ordinary numbers. The result tables are kept clean by construction, since
the report writer drops the value columns before it writes. One more test
repeats, on the committed tables, the grid and zero-reference routes
described below, and fails if one of them succeeds. It reads the tables
only. The cluster table in `docs/FINDINGS.md` is rebuilt from them by
another test. Both cover the ways that have been found, not ways nobody has
thought of.

## What is

- code that reads an upstream checkout you fetch yourself
- result tables holding normalised quantities:
  - **margin**: (submitted value minus reference) divided by the tolerance
    width, rounded to 2 decimals. For a whole-number field with a tolerance
    under 10 the margin is replaced by the zone it falls in: inside, inside
    near the lower or upper edge, or above or below the window, near its
    edge or clear of it
  - window width as a percentage of the reference, rounded to a whole percent,
    written as ">200" beyond that, and withheld for a whole-number field
    with a tolerance under 100
  - a flag for a window whose floor is at or below zero around a reference
    of zero or more
  - Z-prime for the traced field of a task: to 2 decimals, or to 1 decimal
    where the reference and tolerance are whole numbers
  - for a set grader, 1 of 3 bands that say how the similarity score compares
    with its pass threshold: at or above, under 0.25 below, 0.25 or more
    below
  - rates and counts
  - method labels and the transcript step index that supports each one
- task identifiers, field names, grader types, failure-mode labels, model
  names and harness names, taken from the public upstream task files, README
  and results tables
- published leaderboard accuracies and intervals, which are results, not
  task content

## What the normalisation does and does not protect

A margin does not state the reference or the answer. It is not a guarantee
that they cannot be worked out. Reviews by AI models have found 5 ways so
far. No person has checked for others. Each is described here with what was
changed, and then what is still exposed.

**1. Margins at high precision.** Submitted answers are often whole numbers,
and with enough margins for one field, at high enough precision, the
tolerance and then the reference can be solved for. An audit of the first
version of this repository did exactly that from margins published to 4
decimals. Margins are now rounded to 2 decimals and per-run margins outside
the traced tasks are no longer published. The tables for benchmarks graded
from transcripts carry no margins at all.

**2. A blank cell.** A window around a reference of zero has no width as a
percentage, and the table left that cell blank, which said the reference was
zero. This one was in a published table. Widths beyond 200% of the
reference, including that case, are now written as ">200".

**3. Margins on a grid.** For a field whose reference and tolerance are whole
numbers, the answers are whole numbers too, so the margins fall on a grid
whose spacing is 1 divided by the tolerance. With a small tolerance the grid
shows at 2 decimals. Taking the smallest whole tolerance that fits the
published margins gave the true tolerance of 5 fields. 1 of the 5 was in the
scBench tables published with version 0.2.0: its tolerance could be worked
out there, and its reference could not. For 3 of the others the window
percentage then gave the reference. When the percentage was withheld, the
flag for a floor at zero still gave 1 of the 3, because it bounds the
reference by the tolerance.

2 things changed. The window percentage is withheld for every field whose
reference and tolerance are whole numbers and whose tolerance is under 100.
And where the tolerance is under 10, so that a handful of margins shows the
grid, no margin is published as a number anywhere in this repository: the
tables, the cards, the figures and the documents give only the zone a margin
falls in.

**4. A flag that singled out zero.** The flag for a floor at or below zero
was defined for positive references only. A window wider than 200% with the
flag off could then only be a window around zero: the blank cell again, for
1 more field. The flag now covers a reference of zero.

**5. A statistic computed from the answers.** Z-prime does not depend on the
tolerance, but it was computed from the raw answers and written to 3
decimals. For 1 scBench field with a whole-number tolerance, the margins,
the cluster sizes and that value together left only 3 whole tolerances that
could have produced it. Z-prime, spans and gaps of such a field are now
computed from the published 2-decimal margins, and its Z-prime is written
to 1 decimal. That leaves as many candidates as the margins do alone.

The references found by ways 3 and 4 were in SpatialBench tables that had
not been published. The tolerances of ways 3 and 5 could be worked out, or
narrowed, from the scBench tables of version 0.2.0. This version replaces
those tables.

**What the tables still say.** Stated here so that nobody has to work it
out:

- A withheld width says the reference and the tolerance are whole numbers
  and the tolerance is under 100. A margin given as a zone says the
  tolerance is under 10.
- The floor flag, when on, says the reference is zero or positive and no
  larger than the tolerance. Next to a zone, that leaves the whole numbers
  from 0 to 9. This is so for 4 fields, 1 in the scBench tables and 3 in the
  SpatialBench tables. When off, the flag says the reference is larger than
  the tolerance, or negative.
- By the grid method alone, no tolerance can now be worked out from the
  committed tables. A field with a tolerance from 10 to 99 keeps its margins
  as numbers. Today 3 such fields have margins published as numbers, with at
  most 5 distinct values on any one field, and at least 18 whole tolerances
  under 100 fit each of them. With more distinct answers a grid could show.
  The test checks that the smallest fit is wrong and that more than 3
  candidates remain.
- Zone counts and the pass rates along the tolerance sweep come from the same
  margins at coarse resolution. They say how many answers sit near an edge,
  not where the reference is.

**Scores over short lists.** A set grader's similarity score over a short
list is a fraction with a small denominator, which says something about the
length of the reference list. The tables therefore give that score only as
a band. And for a field with 2 possible labels, a pass column together with
a description of the task's logic can give the reference label away. The
pages avoid describing such logic.

All of these values are public in the upstream repository, which is where
anyone wanting them would look. The aim here is narrower: this repository
should not be a second place where benchmark answers can be read off.

## Where the line is

The method specs under `src/sc_zprime/methods/` say which function calls
identify each analysis method for the traced tasks (3 of scBench, 3 of
SpatialBench), and `docs/FINDINGS.md` and `docs/SPATIALBENCH.md` say which
methods pass. Someone could use that to choose a
passing method for those public tasks. Their answers and design notes
are already public upstream, so this adds little, but it is more than
"method families" and is stated here plainly.

The findings paraphrase the authors' design notes where that is needed to say
what a task intends. They do not quote them.

The upstream harness and grader library (`latchbio/latch-eval-tools`) is
publicly readable but its licence reserves all rights. Its source was read to
understand the grader's behaviour, and the grader here mirrors that
behaviour, including which configurations are rejected. None of the upstream
code is copied or redistributed. scBench, SpatialBench and VariantBench are
Apache-2.0. TxBench-PP publishes no licence file, so only task identifiers,
field names, metadata labels (category, platform, horizon, grader type,
failure-mode labels) and normalised quantities from it are used.

## If you hold a private benchmark

`sc-zprime run` works on a checkout in the same layout whose tasks use the
numeric tolerance grader. Tasks with other grader types are skipped and listed
in the summary. `sc-zprime regrade` also grades label-set, marker-list,
multiple-choice and all_of graders, which have not been checked against
published verdicts. Be aware that a validation card names the traced field
and the method labels, so cards for private tasks reveal something about
them, and that margins for a whole-number field show its tolerance (see
above). Share the aggregate tables and keep the cards, the per-field tables
and the method specs private.
