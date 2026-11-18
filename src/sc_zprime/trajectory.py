"""Read agent transcripts as an ordered list of (command, output) steps.

Four transcript shapes are handled, covering the harnesses in the public
single-cell runs:

1. mini-swe-agent, chat-completions style: assistant messages carry
   `tool_calls`, and `tool` messages carry the output.
2. mini-swe-agent, responses style: a response object carries `output` items
   of type `function_call`, and later `function_call_output` items carry the
   output, matched by `call_id`.
3. Claude Code stream: assistant events carry `tool_use` blocks, user events
   carry `tool_result` blocks, matched by id.
4. Codex stream: `item.completed` events of type `command_execution` carry the
   command and its aggregated output together.

Transcripts are parsed as JSON and never executed.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class Step:
    index: int
    command: str
    output: str = ""


def _text(content: Any) -> str:
    """Flatten a tool-output payload to text."""
    if content is None:
        return ""
    if isinstance(content, str):
        stripped = content.strip()
        if stripped.startswith("{") and '"output"' in stripped:
            try:
                doc = json.loads(stripped)
            except ValueError:
                return content
            if isinstance(doc, dict):
                parts = [doc.get(k) for k in ("output", "output_head", "output_tail")]
                return "\n".join(str(p) for p in parts if p)
        return content
    if isinstance(content, list):
        return "\n".join(_text(c.get("text") if isinstance(c, dict) else c) for c in content)
    if isinstance(content, dict):
        return _text(content.get("text") or content.get("output") or content.get("content"))
    return str(content)


def _command(arguments: Any) -> str:
    if isinstance(arguments, dict):
        return str(arguments.get("command", json.dumps(arguments)))
    if isinstance(arguments, str):
        try:
            doc = json.loads(arguments)
        except ValueError:
            return arguments
        if isinstance(doc, dict):
            return str(doc.get("command", arguments))
        return arguments
    return str(arguments)


_SHELL_WRAP_SINGLE = re.compile(r"^\s*(?:/bin/|/usr/bin/)?(?:ba|z)?sh\s+-l?c\s+'(.*)'\s*$", re.S)
_SHELL_WRAP_DOUBLE = re.compile(r'^\s*(?:/bin/|/usr/bin/)?(?:ba|z)?sh\s+-l?c\s+"(.*)"\s*$', re.S)


def unwrap_shell(command: str) -> str:
    """Undo `bash -lc '...'` or `bash -lc "..."` wrapping and its escapes.

    Without this, a Python string inside the wrapped script can read as
    `'"'"'seurat'"'"'` and keyword matching fails.
    """
    hit = _SHELL_WRAP_SINGLE.match(command)
    if hit:
        return hit.group(1).replace("'\"'\"'", "'").replace("'\\''", "'")
    hit = _SHELL_WRAP_DOUBLE.match(command)
    if hit:
        return hit.group(1).replace('\\"', '"').replace("\\$", "$").replace("\\`", "`")
    return command


def steps_from_document(doc: Any) -> list[Step]:
    steps: list[Step] = []
    by_id: dict[str, Step] = {}

    def add(command: str, call_id: str | None = None, output: str = "") -> None:
        step = Step(len(steps), command, output)
        steps.append(step)
        if call_id:
            by_id[call_id] = step

    def attach(call_id: str | None, output: Any) -> None:
        if call_id and call_id in by_id:
            by_id[call_id].output += _text(output)

    if isinstance(doc, dict) and isinstance(doc.get("messages"), list):
        for message in doc["messages"]:
            if not isinstance(message, dict):
                continue
            for call in message.get("tool_calls") or []:
                fn = call.get("function") or {}
                add(_command(fn.get("arguments")), call.get("id"))
            if message.get("role") == "tool":
                attach(message.get("tool_call_id"), message.get("content"))
            if isinstance(message.get("output"), list):
                for item in message["output"]:
                    if isinstance(item, dict) and item.get("type") == "function_call":
                        add(_command(item.get("arguments")), item.get("call_id"))
            if message.get("type") == "function_call_output":
                attach(message.get("call_id"), message.get("output"))
        return steps

    if isinstance(doc, list):
        for event in doc:
            if not isinstance(event, dict):
                continue
            kind = event.get("type")
            message = event.get("message") if isinstance(event.get("message"), dict) else {}
            content = message.get("content") if isinstance(message.get("content"), list) else []
            if kind == "assistant":
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        add(_command(block.get("input")), block.get("id"))
            elif kind == "user":
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_result":
                        attach(block.get("tool_use_id"), block.get("content"))
            elif kind == "item.completed":
                item = event.get("item") or {}
                if item.get("type") == "command_execution":
                    add(unwrap_shell(str(item.get("command", ""))), None, _text(item.get("aggregated_output")))
    return steps


def load_steps(path: str | Path) -> list[Step]:
    path = Path(path)
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as handle:
        try:
            doc = json.load(handle)
        except ValueError:
            return []
    return steps_from_document(doc)


def number_pattern(value: float | int) -> re.Pattern:
    """Regex that finds a submitted number as a standalone token in output.

    Integers also match with thousands separators (1,234). Decimals also match
    when the printed value carries more digits than the submitted one, since
    agents usually round before submitting.
    """
    if float(value).is_integer():
        digits = str(int(round(float(value))))
        sign = "-" if digits.startswith("-") else ""
        digits = digits.lstrip("-")
        head = len(digits) % 3 or 3
        groups = [digits[:head]] + [digits[i:i + 3] for i in range(head, len(digits), 3)]
        body = ",?".join(re.escape(g) for g in groups)
        return re.compile(rf"(?<![\d.,]){sign}{body}(?:\.0+)?(?![\d]|[.,]\d)")
    text = repr(float(value))
    return re.compile(rf"(?<![\d.,]){re.escape(text)}\d*(?![\d])")


def first_step_printing(steps: list[Step], value: float | int, command_filter: re.Pattern | None = None) -> Step | None:
    """Earliest step whose output shows the submitted value.

    With `command_filter`, only steps whose command matches are considered.
    This is how a submitted number is traced back to the code that made it.
    """
    pattern = number_pattern(value)
    for step in steps:
        if command_filter is not None and not command_filter.search(step.command):
            continue
        if pattern.search(step.output):
            return step
    return None
