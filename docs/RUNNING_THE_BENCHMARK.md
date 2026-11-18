# How much of this can be run, and how much re-implemented

Status of each layer, from the outside, as of November 2026.

| Layer | Status | Notes |
|---|---|---|
| Grading published answers | **done** | Independent grader reproduces 273 of 273 verdicts. Numeric tolerance only. |
| Statistics on published runs | **done** | Margins, tolerance sweep, clusters, repeatability, credit, with intervals. |
| Method tracing from transcripts | **done for 3 of 6 tasks** | Differential expression, normalization, PCA preprocessing. Labels confirmed by blind AI raters. |
| Leaderboard statistics | **done from the summary table** | Results are published overall, per category and per platform, not per task, so no paired comparison. |
| Other grader types | not started | Label-set Jaccard, marker-gene precision and recall, distribution comparison, multiple choice, rubric. |
| Re-deriving reference answers | **not attempted** | Needs the task data. See below. |
| Scripted controls | **not attempted** | The reference pipeline and each trap as code. Needs the task data. |
| Running agents | **not attempted** | See below. |

## What running the benchmark needs

The upstream harness (`latchbio/latch-eval-tools`) is publicly readable. Its
licence reserves all rights, so check the terms before using it. From reading
its code, a run needs three things:

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
