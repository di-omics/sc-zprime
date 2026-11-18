"""The repository must not contain benchmark answers. Skipped without a checkout.

Every reference value, tolerance and submitted answer with four or more
significant digits is looked for, as a standalone number, in every tracked
text file outside the generated result tables. The canary identifiers and the
task prompts are looked for everywhere.
"""

import json
import os
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
ROOT = Path(os.environ.get("SC_ZPRIME_UPSTREAM", REPO.parent / "upstream"))
SCBENCH = ROOT / "scbench"
pytestmark = pytest.mark.skipif(not (SCBENCH / "evals").exists(), reason="no upstream checkout")

TEXT = {".md", ".py", ".sh", ".toml", ".csv", ".json", ".svg", ".txt", ".cfg"}
SKIP_DIRS = {".git", ".venv", "__pycache__", ".pytest_cache", "build", "dist"}


def tracked_text(include_results: bool):
    for path in REPO.rglob("*"):
        if not path.is_file() or path.suffix not in TEXT:
            continue
        parts = set(path.relative_to(REPO).parts)
        if parts & SKIP_DIRS or any(p.endswith(".egg-info") for p in parts):
            continue
        if not include_results and "results" in parts:
            continue
        yield path


def significant(value) -> str | None:
    """Canonical text of a number, or None if it is too short or too round to identify anything."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    text = repr(float(value)).rstrip("0").rstrip(".") if float(value) != int(value) else str(int(value))
    digits = re.sub(r"[^0-9]", "", text).lstrip("0")
    if len(digits.rstrip("0")) <= 1:
        # Round numbers such as 1000 or 0.05 identify nothing and appear everywhere.
        return None
    return text if len(digits) >= 4 else None


def numbers_in(obj):
    if isinstance(obj, dict):
        for v in obj.values():
            yield from numbers_in(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from numbers_in(v)
    else:
        yield obj


def forbidden_numbers() -> set[str]:
    out = set()
    for spec_path in (SCBENCH / "evals").glob("*/*.json"):
        spec = json.loads(spec_path.read_text())
        out.update(filter(None, (significant(v) for v in numbers_in(spec.get("grader", {})))))
    for answer_path in (SCBENCH / "trajectories").glob("*/*/*/*/*/eval_answer.json"):
        out.update(filter(None, (significant(v) for v in numbers_in(json.loads(answer_path.read_text())))))
    return out


def test_no_benchmark_number_outside_the_result_tables():
    forbidden = forbidden_numbers()
    assert len(forbidden) > 50
    token = re.compile(r"(?<![\w.])-?\d+(?:\.\d+)?(?![\w]|\.\d)")
    leaks = []
    for path in tracked_text(include_results=False):
        found = {t.lstrip("-") for t in token.findall(path.read_text(errors="ignore"))}
        hits = sorted(found & forbidden)
        if hits:
            leaks.append((str(path.relative_to(REPO)), hits))
    assert not leaks, leaks


def test_no_canary_or_prompt_text_anywhere():
    needles = []
    for spec_path in (SCBENCH / "evals").glob("*/*.json"):
        spec = json.loads(spec_path.read_text())
        guid = re.search(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", spec.get("canary", ""))
        if guid:
            needles.append(guid.group(0))
        sentences = [s.strip() for s in re.split(r"(?<=[.?!])\s+", spec.get("task", "")) if len(s.strip()) > 60]
        needles.extend(sentences[:6])
    assert needles
    for path in tracked_text(include_results=True):
        text = path.read_text(errors="ignore")
        for needle in needles:
            assert needle not in text, (str(path.relative_to(REPO)), needle[:50])
