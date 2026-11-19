"""Record exactly what a result was computed from.

A result is only reproducible if the inputs can be shown to be the same. This
module fingerprints the inputs the analysis reads (task grader configs,
submitted answers, published grades, transcripts) and records the software
versions used.
"""

from __future__ import annotations

import hashlib
import platform
import subprocess
from importlib import metadata
from pathlib import Path

READ_BY_ANALYSIS = ("eval_answer.json", "result.json", "trajectory.json")


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def input_fingerprint(root: str | Path) -> dict:
    """SHA-256 over every file the analysis reads, in sorted path order."""
    from .load import task_dir

    root = Path(root)
    where = task_dir(root)
    files = sorted(where.glob("*/*.json")) if where else []
    for name in READ_BY_ANALYSIS:
        files += sorted((root / "trajectories").glob(f"*/*/*/*/*/{name}"))
    board = root / "results" / "model_results.csv"
    if board.exists():
        files.append(board)
    overall = hashlib.sha256()
    for path in sorted(files):
        overall.update(str(path.relative_to(root)).encode())
        overall.update(b"\0")
        overall.update(_sha(path).encode())
        overall.update(b"\n")
    return {"files": len(files), "sha256": overall.hexdigest()}


def git_head(root: str | Path) -> str | None:
    """Commit of the checkout at `root`, or None unless `root` is itself the
    top of a git repository. A copied tree inside some other repository must
    not be stamped with that repository's commit."""
    root = Path(root).resolve()
    try:
        top = subprocess.run(["git", "-C", str(root), "rev-parse", "--show-toplevel"], capture_output=True, text=True, timeout=10)
        if top.returncode != 0 or Path(top.stdout.strip()).resolve() != root:
            return None
        out = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip() or None


def environment() -> dict:
    versions = {}
    for name in ("pandas", "numpy", "scipy", "matplotlib"):
        try:
            versions[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            versions[name] = None
    return {"python": platform.python_version(), **versions}
