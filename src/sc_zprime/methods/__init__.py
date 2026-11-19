"""Trace a submitted number back to the analysis method that produced it.

A numeric grader sees only the final number. This module asks the question
the grader cannot: which method made that number, and is it one the task
authors would accept?

The attribution is rule based and reproducible:

1. Read the transcript as (command, output) steps.
2. Walk the steps whose output shows the submitted value, earliest first,
   skipping steps that only echo the answer file.
3. Classify the code behind each with the task's rules, ignoring comments,
   and stop at the first step that matches exactly one method. If a step
   only runs a script, its code is the nearest earlier step that matches a
   rule. A step that sweeps several methods at once is skipped in favour of
   the later step where the agent commits to one.

If no step prints the value, the last classifiable step is used and the row
is flagged `fallback`. If the code matches more than one method, the row is
flagged `ambiguous`. A reviewed label from `annotations/<task>.csv` takes
precedence when present. Every label keeps its evidence so a reader can check
it against the public transcript.

A task spec is domain knowledge written down. Adding one for a new task is
how an expert teaches the audit what "the right method" means there.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from pathlib import Path

from .. import trajectory


TIERS = ("intended", "partial", "trap", "other")


@dataclass(frozen=True)
class Rule:
    """One recognisable method.

    `pattern` is anything with a `.search(text)` method: a compiled regex or a
    `CallArgument` matcher. `tier` says how the task authors treat the method:
    intended (the design the task is testing for), partial (right family,
    missing a required element), trap (the shortcut the task is built to
    reject), or other.
    """

    label: str
    pattern: object
    tier: str


def _balanced(text: str, start: int, limit: int = 4000) -> str:
    """Return the argument text of the call whose "(" is at `start`."""
    depth, i, end = 0, start, min(len(text), start + limit)
    while i < end:
        ch = text[i]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return text[start + 1:i]
        i += 1
    return text[start + 1:end]


@dataclass(frozen=True)
class CallArgument:
    """Match a function call by the content of one keyword argument.

    Finds each call matching `call`, takes the value of the keyword matching
    `keyword`, follows one level of variable assignment if the value is a bare
    name, and tests it against `value`. With `want=False` the call matches
    when the argument is present but its value does not match.
    """

    call: str
    keyword: str
    value: str
    want: bool = True

    def search(self, text: str):
        for hit in re.finditer(self.call + r"\s*\(", text):
            args = _balanced(text, hit.end() - 1)
            kw = re.search(r"(?:^|[,(\s])(?:" + self.keyword + r")\s*=\s*([^\n]*)", args)
            if not kw:
                continue
            val = kw.group(1)
            name = re.match(r"\s*([A-Za-z_][A-Za-z_0-9]*)\s*[,)]?\s*$", val)
            if name:
                assigned = re.findall(r"(?m)^\s*" + re.escape(name.group(1)) + r"\s*=\s*([^\n]*)", text)
                if assigned:
                    val = assigned[-1]
            if bool(re.search(self.value, val)) == self.want:
                return hit
        return None


@dataclass(frozen=True)
class Combo:
    """Match when every `require` pattern is present and no `forbid` one is.

    With `once`, the step must contain exactly one occurrence of that pattern,
    so a script that runs several alternative pipelines is not classified.
    """

    require: tuple
    forbid: tuple = ()
    once: str | None = None

    def search(self, text: str):
        if self.once is not None and len(re.findall(self.once, text)) != 1:
            # Several pipelines in one script is a sweep, not a commitment.
            return None
        if any(re.search(p, text) for p in self.forbid):
            return None
        hit = None
        for p in self.require:
            hit = re.search(p, text)
            if hit is None:
                return None
        return hit


@dataclass(frozen=True)
class KeywordChoice:
    """Match a call by the value of a string keyword, with a default.

    `choices` are the accepted values. If the keyword is absent the call is
    treated as using `default`. `before` optionally requires (True) or forbids
    (False) a pattern earlier in the same script, which is how "was the input
    already log-normalised" is told apart.
    """

    call: str
    keyword: str
    choices: tuple
    default: str
    before: str | None = None
    before_present: bool = True

    def search(self, text: str):
        for hit in re.finditer(self.call + r"\s*\(", text):
            args = _balanced(text, hit.end() - 1)
            present = re.search(r"(?:^|[,(\s])" + self.keyword + r"\s*=", args)
            kw = re.search(self.keyword + r"\s*=\s*[\"']+([A-Za-z_0-9]+)[\"']", args)
            if present and not kw:
                # Passed as a variable (a sweep over options): not decidable here.
                continue
            value = kw.group(1) if kw else self.default
            if value not in self.choices:
                continue
            if self.before is not None:
                seen = re.search(self.before, text[:hit.start()]) is not None
                if seen != self.before_present:
                    continue
            return hit
        return None


@dataclass
class MethodSpec:
    """Domain knowledge for one task: which field to trace and how to
    recognise each method in a transcript."""

    task: str
    field: str
    rules: list[Rule]
    describe: dict[str, str] = field(default_factory=dict)
    basis: str = ""
    # How the labels this spec produces were checked, as one sentence for the
    # validation card. Say who or what did the checking.
    checked: str = ""


@dataclass
class Attribution:
    run_id: str
    label: str
    tier: str
    source: str
    evidence: str
    step_index: int | None


_COMMENT = re.compile(r"(?m)(?<![\"'&\\$])#.*$")
_RUNNER = re.compile(r"^\s*(?:cd\s+\S+\s*(?:&&|;)\s*)?(?:python3?|Rscript|bash|sh|uv|time|nohup|tail|head|sleep|ls)\b")
_ANSWER_FILE = re.compile(r"eval_answer|analysis_output|EVAL_ANSWER")


def strip_comments(command: str) -> str:
    """Drop `# ...` comments so a method named in a comment is not counted."""
    return _COMMENT.sub("", command)


def classify(command: str, spec: MethodSpec) -> list[Rule]:
    code = strip_comments(command)
    return [rule for rule in spec.rules if rule.pattern.search(code)]


def classify_any(command: str, spec: MethodSpec) -> list[Rule]:
    """Like `classify`, but a rule that insists on a single pipeline per step
    (`once`) is also tried without that restriction. Used only to ask whether
    a method's code appears in a step at all."""
    code = strip_comments(command)
    hits = []
    for rule in spec.rules:
        pattern = rule.pattern
        if isinstance(pattern, Combo) and pattern.once is not None:
            pattern = Combo(pattern.require, pattern.forbid, None)
        if pattern.search(code):
            hits.append(rule)
    return hits


def is_runner(command: str) -> bool:
    """True for a step that only launches or inspects a script written earlier."""
    return len(command) < 400 and bool(_RUNNER.search(command)) and "<<" not in command


def load_overrides(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    with open(path, newline="", encoding="utf-8") as handle:
        return {row["run_id"]: row for row in csv.DictReader(handle)}


def _resolve(steps: list, index: int, spec: MethodSpec):
    """Classify the code behind the step at `index`.

    Agents usually write a script in one step and run it in the next, so the
    step that prints a number is often just `python script.py`. Only for such
    runner steps, walk back to the nearest earlier step that matches a rule.
    A step with its own code that matches no rule is left unclassified.
    Returns (step, rules) or (None, []).
    """
    hits = classify(steps[index].command, spec)
    if hits:
        return steps[index], hits
    if not is_runner(steps[index].command):
        return None, []
    for i in range(index - 1, -1, -1):
        hits = classify(steps[i].command, spec)
        if hits:
            return steps[i], hits
    return None, []


def attribute(run_id: str, run_dir: str | Path, value, spec: MethodSpec, overrides: dict[str, dict] | None = None) -> Attribution:
    """Label the method that produced `value` in one run."""
    steps = trajectory.load_steps(Path(run_dir) / "trajectory.json")
    label, tier, source, evidence, where = "unresolved", "other", "none", "no step matched any rule", None
    ambiguous = None

    # A one or two character number appears in too much unrelated output to
    # be traced by its printed value.
    traceable = value is not None and len(str(value).rstrip("0").rstrip(".")) >= 3
    if traceable:
        pattern = trajectory.number_pattern(value)
        for step in steps:
            if not pattern.search(step.output):
                continue
            if _ANSWER_FILE.search(step.command) and not classify(step.command, spec):
                # Echoing the answer file says what was submitted, not how
                # it was computed.
                continue
            code_step, hits = _resolve(steps, step.index, spec)
            if code_step is None:
                continue
            if len({rule.label for rule in hits}) == 1:
                label, tier = hits[0].label, hits[0].tier
                source = "printed" if code_step.index == step.index else "printed_by_script"
                evidence = f"value printed at step {step.index}, code at step {code_step.index}"
                where = code_step.index
                break
            if ambiguous is None:
                ambiguous = (code_step, hits)

    if source == "none":
        if ambiguous is not None:
            code_step, hits = ambiguous
            label, tier, source, where = "ambiguous", "other", "ambiguous", code_step.index
            evidence = f"step {code_step.index} matches: " + "; ".join(sorted({rule.label for rule in hits}))
        else:
            for step in reversed(steps):
                hits = classify(step.command, spec)
                if len({rule.label for rule in hits}) == 1:
                    label, tier, source, where = hits[0].label, hits[0].tier, "fallback", step.index
                    evidence = f"submitted value not matched to an analysis step; last classifiable step is {step.index}"
                    break

    override = (overrides or {}).get(run_id)
    by_label = {rule.label: rule for rule in spec.rules}
    if override and override.get("label") in by_label:
        rule = by_label[override["label"]]
        evidence = f"reviewed: {override.get('note', '').strip()} (auto: {label})"
        label, tier, source = rule.label, rule.tier, "reviewed"
    return Attribution(run_id, label, tier, source, evidence, where)


def registry() -> dict[str, MethodSpec]:
    from . import scbench, spatialbench

    return {spec.task: spec for spec in scbench.SPECS + spatialbench.SPECS}


def notes_context(task: str) -> dict[str, str]:
    """What the task's own notes say about each flag a card may raise."""
    from . import scbench, spatialbench

    return {**scbench.NOTES_CONTEXT, **spatialbench.NOTES_CONTEXT}.get(task, {})
