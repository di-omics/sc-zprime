# sc-zprime, explained

A plain-language guide. No statistics or machine-learning background needed.
If you only read one section, read "The idea in one paragraph".

## The idea in one paragraph

AI agents are now being tested on real biological data analysis. A benchmark
hands the agent a dataset and a question, the agent writes and runs code, and
a program checks whether its final number falls inside an accepted window.
The share of tasks passed becomes a leaderboard score. sc-zprime does not ask
how good the agents are. It asks a question that comes first: **is the test
itself any good?** It checks each task the way a laboratory checks an assay
before trusting it, and it reports the result as a short validation card.

## Why a benchmark is an assay

In a screening lab, an assay turns a sample into a readout: a plate goes in, a
number comes out, and a threshold turns the number into "hit" or "not a hit".

An agent benchmark has the same shape:

| Screening lab | Agent benchmark |
|---|---|
| sample | the AI model |
| assay | one benchmark task |
| readout | the number the agent submits |
| hit threshold | the pass window around the reference answer |
| replicate wells | repeat runs of the same model |
| positive control | a run that used the method the task wants |
| negative control | a run that used the shortcut the task is meant to catch |

Nobody in a screening lab trusts a hit until the assay has been validated
with controls. Benchmark tasks are reviewed too, and careful authors go
further: the scBench task notes record what each accepted method and each
shortcut gives on the data. What is not yet routine is to measure, from real
runs, whether a task's pass window separates the methods agents actually use.
sc-zprime adds that measurement.

## What Z-prime is

Z-prime is the standard number for assay quality in high-throughput screening
(Zhang, Chung and Oldenburg, 1999). It compares the gap between the positive
and negative controls with how much each control scatters:

    Z' = 1 - 3 * (spread of positives + spread of negatives)
                 -------------------------------------------
                  distance between positives and negatives

- Close to 1: the controls are far apart and tight. The assay can tell them
  apart with room to spare.
- 0.5 or above: an excellent assay, by the usual convention.
- Between 0 and 0.5: marginal.
- Below 0: the scatter bands of the two controls, three standard deviations
  each, overlap. Whatever the assay reports, it cannot be relied on to
  separate the thing it was built to separate.

### A worked example with invented numbers

Suppose a task asks "how many genes change?", the reference answer is 100 and
answers from 70 to 130 pass.

Four runs use the method the task wants and submit 110, 112, 108 and 110.
Four runs take a shortcut.

**Case A.** The shortcut runs submit 40, 45, 42 and 43. They are far from
the correct runs and tightly grouped. Z-prime is 0.83. The task works: the
shortcut always fails and the right method always passes.

**Case B.** The shortcut runs submit 80, 125, 95 and 130. Now they are
scattered all around the correct runs, and all four of them land inside the
pass window. Z-prime is about -30. The task cannot tell the shortcut from
the right method, and all four shortcut runs get full marks.

**A caution.** Z-prime was built for readouts that scatter smoothly around
two averages, with one threshold between them. Benchmark answers often behave
differently: every run that follows the same recipe submits exactly the same
number, and a pass window has two edges. So Z-prime is a rough summary here.
It can be negative when no shortcut answer actually lies among the correct
ones, and it can be a perfect 1 when the two groups sit close together but
neither has any spread. sc-zprime reports it next to plain counts (how many
shortcut runs passed) and distances, and those carry the conclusions.

In Case B nothing is wrong with the grading program. It does exactly what it
was told. The weakness is in the choice of readout: a single count that
different methods can reach by different routes.

## The five checks

Each check is a question an assay developer would ask, translated.

### 1. Can someone else reproduce the verdict?

*Lab version: does a second instrument give the same reading?*

sc-zprime contains its own grader, written separately from the benchmark's.
It regrades every published answer and counts how often the two agree. If
they did not agree, nothing else would be worth measuring.

### 2. Do the controls separate?

*Lab version: positive and negative controls, and Z-prime.*

This is the central check and the one that takes knowledge of the biology.
The grading program only sees the final number. sc-zprime opens the transcript of each
run, finds the code that produced that number, and labels the method: the
one the task intends, a shortcut the task authors name as incorrect, or
something they do not mention.

Two things are then reported, and they are different questions:

- **Does the task's pass window do its job?** Sensitivity is the share of
  intended-method runs that pass. Specificity is the share of shortcut runs
  that fail. A task can have perfect sensitivity and poor specificity.
- **How far apart are the answers?** Z-prime, computed between the intended
  method and each named shortcut separately, summarises the distance between
  the two sets of answers relative to their scatter. It is a rough guide for
  the reasons given above, so it is read together with the distances
  themselves.

### 3. Does the pass window sit on a cliff?

*Lab version: is the hit threshold on the shoulder of a peak?*

Agents that run the same recipe get exactly the same number, so answers come
in tight groups. If a group sits right at the edge of the pass window, a tiny
change to the window flips all of those verdicts at once. sc-zprime regrades
everything with the window made slightly narrower and slightly wider and
counts the verdicts that change.

### 4. Do repeats agree?

*Lab version: replicate concordance.*

Each model is run on each task several times. If the same model passes on one
run and fails on the next, that task is partly measuring luck. sc-zprime
counts how often the repeats disagree.

### 5. Are there dead readouts?

*Lab version: a channel with no dynamic range.*

Some tasks grade several numbers. If every run gets one of them right, that
number cannot change who passes. It is harmless under all-or-nothing grading
and inflates scores under partial credit.

## How the method is traced

The hard part is check 2, because it requires knowing what each agent did.

1. The transcript of a run is read as an ordered list of steps: each command
   the agent ran and what it printed.
2. The tool looks for the step whose output shows the number the agent later
   submitted.
3. It reads the code behind that step. Agents usually write a script in one
   step and run it in the next, so the tool follows that link.
4. It matches the code against a short specification written for the task,
   which takes knowledge of the biology: which function calls mean
   "pseudobulk with a donor term", which mean "a test on individual cells",
   and so on.

Most runs are labelled automatically. A handful are ambiguous, for example
when an agent tries four methods in one script, and those are read and
recorded with the reason. Every label is published with the step it came
from, so anyone can check it against the public transcript. The labels were
also checked by independent blind raters, who agreed with all of them. The
raters were AI models; a person has not yet checked a sample.

## What you get

For each task, a **validation card**: one page with the measurements above,
with an interval wherever the data can support one, and a list of
plain-language flags such as "a shortcut
method passes" or "answers cluster at the edge of the window". A flag prompts
a look. It is not a verdict. For the whole benchmark, a set of tables and
three figures.

The proposal behind the project is that every benchmark task should ship with
a card like this, and with scripted positive and negative controls, the same
way every assay ships with its Z-prime. See
[VALIDATION_CARD.md](VALIDATION_CARD.md).

## What it does not do

- It does not rank models.
- It does not say a benchmark is bad. A task can have a weak readout and
  still be a good idea, and several weaknesses it finds are ones the task
  authors already wrote down themselves.
- It does not rerun any analysis. It works from what the benchmark authors
  published: answers, grades and transcripts.
- It cannot see the tasks a benchmark keeps private.

## Why single cell first, and what comes next

The first target is a single-cell RNA-seq benchmark because its authors
published everything needed: graded runs, transcripts and their own design
notes. The idea is not specific to single cell. It applies wherever an
analysis ends in a number that a program accepts or rejects.

Planned next, none of it started:

- **Whole-genome analysis.** Variant calling has reference truth sets, which
  are natural positive controls, and well-known failure modes that make
  natural negative controls.
- **Polygenic risk scores.** A score can pass a numeric check while being
  computed on the wrong ancestry reference or the wrong genome build. Those
  are the shortcuts a validation card should catch.
- **Epigenetic and proteomic clocks.** A clock's readout is a predicted age.
  Controls would be samples of known age, and the traps would be skipped
  normalisation or the wrong tissue model.

## Glossary

| Term | Meaning |
|---|---|
| Agent | An AI model that writes and runs code on its own to finish a task. |
| Harness | The program that runs the agent and records what it did. |
| Task | One question on one dataset, with a reference answer and a pass window. |
| Reference | The answer the task authors computed. |
| Tolerance | How far from the reference an answer may be and still pass. |
| Margin | Distance from the reference measured in tolerances. 0 is the reference, 1 is the edge of the window. |
| Transcript | The full record of one run: every command and its output. |
| Configuration | One model paired with one harness. |
| Repeat | One of several runs of the same configuration on the same task. |
| Intended method | The analysis the task is designed to reward. |
| Trap | A shortcut the task is designed to catch. |
| Z-prime | Separation between positive and negative controls relative to their scatter, from 1 (far apart and tight) to below 0 (their scatter bands overlap). |
| Validation card | The one-page report sc-zprime writes for each task. |
