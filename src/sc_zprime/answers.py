"""Recover the answer a run submitted when only its transcript is published.

scBench and SpatialBench publish each run's answer file next to its
transcript. Other benchmarks in the family publish the transcript alone. The
harness grades whatever the agent left in its answer file, so the question
here is what that file held at the end of the run.

The recovery is rule based:

1. Collect every JSON object the transcript shows that carries at least one
   of the fields the task grades: objects written to the answer file by a
   command, objects printed by any step, and objects inside answer tags in
   the agent's own messages. A template whose values are type names or
   placeholders is not an answer. Objects that carry every graded field are
   preferred over objects that carry only some.
2. The last such object shown by a step is taken, since the file holds what
   was written last. If no step shows one, the last tagged object in the
   agent's messages is taken.
3. If a later step writes the answer file again without showing what it
   wrote, the recovered object may be stale. That is flagged, not hidden.

A run whose script computes the answer and writes it without ever showing it
as an object cannot be recovered, and is reported as such rather than guessed.

Known ways this goes wrong, all seen in the measured test set: a literal in a
script that is written to the answer file only on a branch that did not run,
and a file overwritten by a step that shows nothing. `validation/` holds the
measurement against every run whose answer file is published. Transcripts are
parsed as text and JSON and never executed.
"""

from __future__ import annotations

import ast
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import trajectory

ANSWER_FILE = re.compile(r"(?:eval_answer|analysis_output)\.json")
TAG = re.compile(r"<EVAL_ANSWER>(.*?)</EVAL_ANSWER>", re.S)
_PLACEHOLDER = re.compile(
    r"^\s*<?\s*(?:float|int|integer|number|str|string|bool|boolean|list|array)\s*>?\s*$|^\s*(?:\.\.\.|TBD|<[^<>]*>)\s*$", re.I)
_NUMPY_SCALAR = re.compile(r"\bnp\.(?:float|int|uint|bool_?|str_)\d*\(([^()]*)\)")
_SCRIPT = re.compile(r"\.(?:py|sh|R|r)$")
_WRITES_ANSWER = re.compile(
    r">\s*[^\s|;&]*(?:eval_answer|analysis_output)\.json"
    r"|open\([^)]*(?:eval_answer|analysis_output)\.json[^)]*,\s*[\"']w"
    r"|json\.dump\s*\(")


@dataclass
class Recovered:
    answer: dict | None
    source: str          # "written", "printed", "tagged" or "none"
    step: int | None
    # Every distinct answer object the steps showed, in order of first
    # appearance. More than one means the choice of the last one matters.
    shown: tuple = ()
    # True when a later step writes the answer file again without showing
    # what it wrote, so the recovered object may not be the final one.
    written_again_unseen: bool = False


def objects_in(text: str) -> list[dict]:
    """Every outermost {...} span in `text` that parses as a non-empty object.

    JSON is tried first, then a Python literal, since agents often print a
    dict rather than dump it. numpy scalars printed as np.float64(1.5) are
    read as the number inside. Nothing is evaluated: `ast.literal_eval`
    accepts literals only.
    """
    out, i, n = [], 0, len(text)
    while i < n:
        if text[i] != "{":
            i += 1
            continue
        depth, j, quote, escaped = 0, i, "", False
        while j < n:
            ch = text[j]
            if quote:
                if escaped:
                    escaped = False
                elif ch == "\\":
                    escaped = True
                elif ch == quote:
                    quote = ""
            elif ch in "\"'":
                quote = ch
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        obj = None
        if j < n and depth == 0:
            span = text[i:j + 1]
            try:
                obj = json.loads(span)
            except ValueError:
                try:
                    obj = ast.literal_eval(_NUMPY_SCALAR.sub(r"\1", span))
                except (ValueError, SyntaxError, MemoryError, RecursionError):
                    obj = None
        if isinstance(obj, dict) and obj:
            out.append(obj)
            i = j + 1
        else:
            i += 1
    return out


def graded_fields(grader: Any) -> set[str]:
    """Top-level answer keys that a grader reads, children included."""
    keys: set[str] = set()

    def walk(node: Any) -> None:
        if not isinstance(node, dict):
            return
        config = node.get("config") if isinstance(node.get("config"), dict) else {}
        kind = node.get("type")
        if kind == "numeric_tolerance":
            keys.update(str(k) for k in (config.get("ground_truth") or {}))
        elif kind == "multiple_choice":
            keys.add("answer")
        elif isinstance(config.get("answer_field"), str):
            keys.add(config["answer_field"])
        for child in config.get("children") if isinstance(config.get("children"), list) else []:
            walk(child)

    walk(grader)
    return {key.split(".")[0] for key in keys}


def _is_answer(obj: Any, fields: set[str]) -> bool:
    if not isinstance(obj, dict):
        return False
    shared = fields & set(obj)
    if not shared:
        return False
    return not any(isinstance(obj[k], str) and _PLACEHOLDER.match(obj[k]) for k in shared)


def _written_objects(command: str, fields: set[str]) -> list[dict]:
    """Answer objects that a command writes as literals to the answer file."""
    out = []
    for obj in objects_in(command):
        if isinstance(obj.get("content"), str) and ({"file_path", "path"} & set(obj)):
            # A file-write tool call is itself an object holding the text it
            # wrote. It counts if the file is the answer file, or a script
            # that names the answer file, as a shell command holding the same
            # script would. A draft in a notes file does not count.
            target = str(obj.get("file_path") or obj.get("path") or "")
            if ANSWER_FILE.search(target) or (_SCRIPT.search(target) and ANSWER_FILE.search(obj["content"])):
                out += [inner for inner in objects_in(obj["content"]) if _is_answer(inner, fields)]
        elif _is_answer(obj, fields):
            out.append(obj)
    return out


def recover(path: str | Path, grader: Any, fields: set[str] | None = None) -> Recovered:
    """The answer a run left behind, read from its transcript.

    The fields to look for come from the grader config. `fields` overrides
    that, for a benchmark whose grader is withheld but whose answer keys are
    known.
    """
    doc = trajectory.load_document(Path(path))
    fields = set(fields) if fields else graded_fields(grader)
    if doc is None or not fields:
        return Recovered(None, "none", None)
    steps = trajectory.steps_from_document(doc)
    shown: list[tuple[int, str, dict]] = []
    for step in steps:
        if ANSWER_FILE.search(step.command):
            shown += [(step.index, "written", obj) for obj in _written_objects(step.command, fields)]
        shown += [(step.index, "printed", obj) for obj in objects_in(step.output) if _is_answer(obj, fields)]
    complete = [item for item in shown if fields <= set(item[2])]
    pool = complete or shown
    if pool:
        index, source, answer = pool[-1]
        distinct: dict[str, dict] = {}
        for _, _, obj in pool:
            distinct.setdefault(json.dumps(obj, sort_keys=True, default=str), obj)
        again = any(ANSWER_FILE.search(step.command) and _WRITES_ANSWER.search(step.command)
                    for step in steps if step.index > index)
        return Recovered(answer, source, index, tuple(distinct.values()), again)
    tagged = [obj for text in trajectory.assistant_texts(doc) for hit in TAG.finditer(text)
              for obj in objects_in(hit.group(1)) if _is_answer(obj, fields)]
    complete = [obj for obj in tagged if fields <= set(obj)]
    if complete or tagged:
        return Recovered((complete or tagged)[-1], "tagged", None)
    return Recovered(None, "none", None)
