# How much of this can be run, and how much re-implemented

Status of each layer, from the outside, as of November 2026.

| Layer | Status | Notes |
|---|---|---|
| Grading published answers | **done** | Independent grader reproduces 273 of 273 scBench verdicts and 768 of 768 SpatialBench verdicts. Numeric tolerance only. |
| Statistics on published runs | **done** | Margins, tolerance sweep, clusters, repeatability, credit, with intervals. |
| Method tracing from transcripts | **done for 3 of 6 scBench and 3 of 16 SpatialBench tasks** | scBench: differential expression, normalization, PCA preprocessing, labels confirmed by blind AI raters. SpatialBench: the 3 batch-correction tasks, labels reviewed by AI models and not blind re-rated. |
| Leaderboard statistics | **done from the summary table** | In the repositories, leaderboard results for the full benchmark are published overall, per category and per platform, not per task, so no paired comparison. On benchmarks.bio, the scBench and SpatialBench boards also list example tasks, each with a pass rate. This tool does not read the site. |
| Other grader types | **re-implemented, not checked** | Label-set Jaccard, marker list precision and recall, multiple choice and all_of are re-implemented and used for a first grading of VariantBench and TxBench-PP. No benchmark that uses them publishes per-run verdicts, so they are pinned by unit tests only. Distribution comparison and rubric: not started. |
| Re-deriving reference answers | **not attempted** | Needs the task data. See below. |
| Scripted controls | **done for 1 task, elsewhere** | The reference pipeline and each named shortcut as code, for one scBench task, in [sc-controls](https://github.com/di-omics/sc-controls). It needs the task data and states the task's numbers, so it is kept out of this repository. |
| Running agents | **tried once, elsewhere** | 3 repeats of one scBench task outside the official container, in sc-controls, with the caveats stated there. Not attempted here. See below. |

## What running the benchmark needs

The upstream harness (`latchbio/latch-eval-tools`) is publicly readable. Its
licence reserves all rights, so check the terms before using it. GitHub
showed the repository as archived on 19 November 2026. The commit read here
(`0d79831`, version 0.4.54, 30 September 2026) is the head of its default
branch. From reading its code, a run needs three things:

1. **The task data.** Each task names its dataset as a `latch://` node. The
   harness fetches it through the Latch SDK, which requires a Latch account
   and login. Whether the example datasets are readable by any account has
   not been tested here: no access attempt was made.
2. **A container runtime.** Agents run inside a published Docker image with
   the analysis stack preinstalled and a memory limit. The mini-swe-agent
   harness also applies a per-command timeout.
3. **A model API key** for whichever provider is being evaluated.

Cost, from the per-task figures in the upstream README: between about $0.03
and $2.50 per task per run depending on the model. Three repeats of the six
example tasks with one frontier model is on the order of tens of dollars.

## What re-running would add

- **More repeats.** Three repeats give four possible outcomes per cell. Ten
  would give a usable estimate of each task's pass probability.
- **Scripted controls.** With the data, the reference pipeline and each named
  trap can be run directly, which turns method separation from an observation
  about what agents submitted into a property of the task.
- **A defensible-analyst range.** For a task where two competent analysts
  would choose differently, running both choices shows whether the window
  admits both.

None of this is needed to reproduce the results in this repository.
