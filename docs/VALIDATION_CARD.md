# The validation card

A proposal: every task in an agent benchmark ships with a validation card,
the way every assay ships with its Z-prime.

Before a plate assay is used to call a single hit it has to show that its
controls separate, that replicates agree, and that the hit threshold is not
sitting in the middle of the signal. A benchmark task is reviewed differently:
people check that the reference answer is right and the tolerance is
reasonable. The scBench contribution guide, for example, describes
ground-truth review, grader review and maintainer approval, and its task
notes reason carefully about which method gives which value. The card adds
the measurements that review cannot supply, because they only exist once
runs do.

## The six measurements

| # | Measurement | Assay analogue | Needs |
|---|---|---|---|
| 1 | **Verdict reproducibility**: share of published verdicts an independent grader reproduces | instrument qualification | answers, grader config |
| 2 | **Window geometry**: tolerance width as a share of the reference, per field, and whether a window is one-sided | assay window | grader config |
| 3 | **Dead readouts**: fields passed by at least 95% of runs, and how many verdicts each decided | a channel with little dynamic range | graded runs |
| 4 | **Edge sensitivity**: share of verdicts that flip at 0.8x or 1.25x tolerance, and any group of identical answers near an edge | hit threshold on the shoulder of a peak | graded runs |
| 5 | **Repeatability**: share of configurations whose repeats disagree, and share that submit the identical answer every time | replicate concordance | at least three repeats |
| 6 | **Method separation**: sensitivity and specificity of the pass window against intended and trap methods, the distance between their answers, and Z-prime between the intended method and each trap as a rough summary | positive and negative controls | controls, or traced runs |

Five of the six are computable from what a benchmark already produces. Method
separation needs something more: to know which method each answer came from.

A rate on a card carries an interval wherever the data can support one.
Repeats of one model are not independent, so the intervals resample whole
configurations, and with few configurations they are approximate. When every
configuration agrees there is nothing to resample, and the card gives an
exact one-sided bound counted in configurations. When fewer than three
configurations stand behind a number, it gives no interval.

## Flags

A card raises a flag when a measurement crosses a line. The lines are simple
on purpose. A flag prompts a look. It is not a verdict on the task, and a
task's notes may already explain it. Where they do, the card says so under
the flag.

| Flag | Raised when |
|---|---|
| `DEAD_READOUT` | a graded field is passed by at least 95% of runs |
| `EDGE_CLUSTER` | three or more identical answers sit within 20% inside or 25% outside an edge |
| `UNSTABLE_REPEATS` | at least 20% of configurations give different verdicts across repeats |
| `TRAP_PASSES` | any run that used a method the task notes name as incorrect passed |
| `THIN_CONTROL` | the intended control, or the control for any one trap method, rests on fewer than three configurations or a single provider |

## Controls: the one thing to add

Method separation needs a positive and a negative control. In this repository
they are recovered after the fact, by tracing each agent's answer to its
code. That works, it is slow, and it only covers the methods agents happened
to submit.

The direct route is to ship controls with the task:

- one **positive control** for each accepted method: a script that runs it
- one **negative control** for each method the task is built to reject

and to run them through the grader whenever the task changes. The scBench
task notes already contain most of this in prose: tables of which method
gives which answer, written by people who ran them. Making those tables
executable is a small step from where the authors already are.

A possible shape, as an extra block in the task file:

```json
"controls": [
  {"id": "reference", "role": "positive", "script": "controls/reference.py"},
  {"id": "accepted_variant", "role": "positive", "script": "controls/variant.py"},
  {"id": "named_trap", "role": "negative", "script": "controls/trap.py"}
]
```

With that block a continuous-integration job can assert, for every task, that
each positive control passes and each negative control fails. A named trap
that passes when run the way its control script runs it would be caught
before release. Whether a control script matches how agents run the same
method is a separate question, and the first point below is about it.

Two things the public runs suggest about controls:

1. **Run each control the way the prompt tells an agent to.** On the
   differential expression example, the value the notes record for one trap
   and the values agents obtained with the same method differ by more than
   half a tolerance width. The reason is not established here. A scripted
   control would settle it.
2. **Include the trap nobody expects to matter.** On the normalization
   example, one method the notes list as incorrect printed a value inside the
   window in the runs that tried it. No agent submitted it, so no graded run
   shows it. (This comes from reading intermediate steps of transcripts, not
   from the tool; see the findings.)

## What a benchmark needs to publish for cards to be computable by others

- the grader configuration for each task, or a way to grade without it
- the submitted answer for each run, not only the verdict
- at least three repeats per configuration
- transcripts, if method separation is to be checked independently

scBench publishes all four for its example tasks.

## Beyond single-cell

Nothing in the card is specific to transcriptomics. It applies to any task
with a structured answer and a deterministic grader: epigenomics, spatial,
variant calling, polygenic scores, molecular clocks, plate-based screening
analysis. For a laboratory automation benchmark the same measurements hold,
with the controls being scripted runs of the correct and incorrect procedure
on a reference plate.
