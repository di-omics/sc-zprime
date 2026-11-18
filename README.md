# sc-zprime

**Z-prime for single-cell agent evals.** Assay validation for the benchmarks
that grade AI agents on biology.

In assay development nobody trusts a readout until its controls have been
shown to separate. Z-prime is the standard number for that (Zhang, Chung and
Oldenburg, 1999): it compares the distance between the positive and negative
controls with how much each one scatters. At 0.5 or above an assay is
conventionally good enough to call hits. Below zero the scatter bands of the
two controls overlap and the readout cannot be trusted, however carefully the
plate was run.

Agent benchmarks are assays. The model is the sample, the task is the assay,
and pass or fail is the readout. This repository validates them that way. It
takes the graded runs a benchmark publishes and asks what an assay developer
would ask before believing a result:

- Can an independent implementation reproduce the published verdicts?
- Do the controls separate? Does a run that used the intended analysis pass,
  and does a run that took a named shortcut fail?
- Does the pass window sit on a cliff? How many verdicts flip if a tolerance
  moves a little?
- Do repeats agree? Same model, same task, three runs: same verdict?
- Are there dead readouts, graded fields that nearly every run passes?

New here? Start with the plain-language guide: [docs/EXPLAINER.md](docs/EXPLAINER.md).

The first target is [scBench](https://github.com/latchbio/scbench), LatchBio's
benchmark for single-cell RNA-seq analysis. Its authors published graded runs,
full transcripts and their own design notes for a sample of tasks, which is
what makes validation from the outside possible. Everything here is computed
from that public material. No model was run and no dataset was downloaded.

## What the public scBench sample shows

Six example tasks, 16 model and harness configurations, 91 task and
configuration pairs with three repeats each: 273 graded runs. Upstream commit
`106726f`, November 2026.

| Question | Result |
|---|---|
| Are the published verdicts reproducible? | Yes. An independent grader agrees on 273 of 273 runs. |
| Does the intended method pass? | Yes, on all three tasks traced: 51 of 51 runs. On one of the three that is 5 runs from a single model. |
| Does a method the task notes call incorrect fail? | On two tasks, always (60 of 60 runs). On differential expression, only 7 of 20 runs (35%, interval 19% to 53%). |
| Do verdicts sit near an edge? | 68 of 273 verdicts (25%) flip if tolerances are 20% tighter or 25% wider. 29 of them are one recipe that the task notes place there on purpose. |
| Do verdicts repeat? | In 33 of 91 pairs (36%) the three repeats did not agree. |
| Are there dead readouts? | 4 of 13 graded fields are passed by at least 95% of runs. |
| How well does the leaderboard resolve? | On the published 195-task table, 10 of the 17 other configurations cannot be told apart from the leader by an unpaired test of the difference. |

Intervals are 95% cluster-bootstrap intervals that resample whole
configurations, because three repeats of one model are not three independent
observations. With 16 configurations they are approximate and probably too
narrow.

![Where each method's answers land](results/scbench/figures/fig1_method_separation.png)

Each spike is a group of runs whose answers agree to within 0.01 tolerance
widths. The x axis is distance from the reference answer in tolerance widths,
so the shaded band is the pass window for every task. Colour and marker shape
say which method produced the answer, traced from the code in each run's
transcript and confirmed by blind AI raters.

- **Normalization** and **PCA preprocessing** separate cleanly among the
  answers that were submitted: every intended-method run passes and every
  run that used a method the task notes call incorrect fails.
- **Differential expression** does not. The notes' primary trap is per-cell
  testing with scanpy's default tools, and they expect both of its forms to
  fail: the t-test above the window and the rank test below it. The one
  t-test run fails as expected. The rank test, which is the per-cell method
  agents actually reached for, lands inside the pass window in 13 of 19 runs,
  from seven configurations across all four providers. Six of those thirteen
  sit inside the range the notes accept for correct methods, so no choice of
  window edges that admits the accepted variants can reject them.

Each of these has caveats that matter, and several were anticipated by the
task authors in their own notes. The full account, with every number, its
interval and its limits, is in [docs/FINDINGS.md](docs/FINDINGS.md).

![Verdict stability](results/scbench/figures/fig2_verdict_stability.png)

Per-task reports: [results/scbench/validation_cards](results/scbench/validation_cards).

## How it was checked

Every check was carried out by AI models, in sessions separate from the one
that wrote the code. No person has yet checked a sample of the labels or the
numbers.

- **Method labels.** Blind AI raters re-labelled all 144 traced runs from the
  raw transcripts: 192 ratings, every one in agreement with the tool. See
  [validation/](validation).
- **Numbers.** Separate passes recomputed about 1,100 statements in the first
  draft of these documents from the raw data and reported 58 problems. Two
  later reviews, one of the statistics and one from the benchmark authors'
  side, found more. This version incorporates the corrections.
- **Documents against data.** A test rebuilds each headline sentence from the
  result tables and fails if a number has drifted.
- **Reproducibility.** Pinned dependencies, a fingerprint of the input files
  in every summary, byte-identical tables across runs, and a CI job that
  regenerates everything and compares.
- **Not yet done.** A check of a sample by a person, and code review of the
  transcript parser and the method tracer. See section 8 of the findings.

## What this is not

- Not a leaderboard and not a claim about any model.
- Not a statement about the full benchmark. The six public tasks are examples
  the authors chose. The other 189 are withheld to prevent contamination, and
  nothing here estimates how they behave. The one exception is the leaderboard
  analysis, which uses the published summary table and says so.
- Not a re-derivation of any reference answer. Reference values are taken as
  given.
- Not a judgement that a task is wrong. A flag on a validation card prompts a
  look. The task authors document their own reasoning carefully, including
  limitations, and the findings credit that wherever it applies.
- Not a claim that Z-prime carries over unchanged. It was built for smooth
  scatter and a one-sided threshold. Benchmark answers come in clusters of
  identical values and pass windows have two edges, so Z-prime is reported
  for each trap as a rough summary, next to plain pass counts and margins.
  What carries over is the habit: show that the controls separate before
  trusting the readout.

## The validation card

The proposal in this repository is small: every benchmark task could ship with
a validation card, the way every assay ships with its Z-prime, and with
scripted positive and negative controls so the card can be computed before any
model is run. Spec: [docs/VALIDATION_CARD.md](docs/VALIDATION_CARD.md).

## Run it

Needs Python 3.10 or newer.

```bash
git clone https://github.com/di-omics/sc-zprime
cd sc-zprime
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.lock && pip install -e . --no-deps

scripts/fetch_upstream.sh ../upstream     # shallow clone of scBench at the pinned commit
pytest -rs                                # any test that skips says why
sc-zprime run --upstream ../upstream/scbench --out out/scbench --name scbench --figures
scripts/compare_results.py results/scbench out/scbench   # regenerated tables against the committed ones
```

The tests that use the benchmark data look for it in `../upstream`, or
wherever `SC_ZPRIME_UPSTREAM` points (the directory that contains `scbench`).
Without it they are skipped, and `pytest -rs` lists them.

## How it works

| Module | Job |
|---|---|
| `graders.py` | Independent re-implementation of the numeric tolerance grader, written after reading the upstream one, in separate code. |
| `load.py` | Reads a benchmark checkout into tidy tables. Tasks with other grader types are skipped and listed. |
| `trajectory.py` | Reads agent transcripts from three harnesses, in four transcript shapes, as ordered (command, output) steps. |
| `methods/` | Traces a submitted number back to the code that produced it and labels the method. Three of the six tasks have a method spec so far. |
| `metrics.py` | The validation measurements. |
| `uncertainty.py` | Cluster-bootstrap intervals, leave-one-provider-out ranges, and sensitivity to every threshold. |
| `provenance.py` | Fingerprints the input files and records software versions. |
| `report.py` | Runs everything and writes tables, validation cards and `summary.json`. |
| `figures.py` | Draws the figures from the exported tables only. |

Method tracing is the part that takes domain knowledge. A numeric grader sees
one number. The tracer finds the step in the transcript that printed that
number, reads the code behind it, and labels it against a short spec written
for the task: which calls mean pseudobulk with a donor term, which mean a
per-cell test, which mean a log transform was applied before variable-gene
selection. Of 144 traced runs, 133 are labelled from the printed value, 7 from
the last classifiable step and 4 by reading. Every label and its evidence is
in `results/scbench/method_trace.csv`.

## Data policy

scBench task files carry a canary string asking that benchmark data stay out
of training corpora. This repository states no task prompt, no reference
answer, no submitted answer and no tolerance in its own units. Exported
quantities are normalised and rounded: distances are in tolerance widths and
window widths are a percentage of the reference. A test fails if a benchmark
value with four or more significant digits appears in a tracked file outside
the result tables. Those values are public upstream, and the policy says
exactly what the normalisation does and does not protect:
[docs/DATA_POLICY.md](docs/DATA_POLICY.md).

## Roadmap

- Scripted controls: the reference pipeline and each named trap as code, so
  Z-prime can be computed before any model is run. This needs the task data.
- More graders: label-set Jaccard, marker-gene precision and recall,
  distribution comparison, multiple choice.
- More tasks traced: the QC, clustering and cell typing examples.
- A second benchmark. SpatialBench publishes graded runs in a similar tree
  with its task files laid out differently, so it needs its own loader.
- Other data types: whole-genome analysis, polygenic risk scores, epigenetic
  and proteomic clocks.

## Corrections

If something here misreads a task or its notes, please open an issue. That
goes especially for the scBench authors, who know these tasks far better than
an outside reading can. It will be fixed and the fix noted.

## Licence

MIT, see [LICENSE](LICENSE). This repository contains no benchmark data.
scBench itself is Apache-2.0. Its harness, latch-eval-tools, reserves all
rights; it was read to understand the grader and is not copied here.

## Acknowledgement

This work exists because the scBench authors published their runs,
transcripts and design notes, including the limitations they saw themselves.
Most benchmarks publish a number.
