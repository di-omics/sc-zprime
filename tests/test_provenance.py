import subprocess

from sc_zprime import provenance


def test_fingerprint_changes_when_an_input_changes(tmp_path):
    (tmp_path / "evals" / "c").mkdir(parents=True)
    task = tmp_path / "evals" / "c" / "t.json"
    task.write_text("{}")
    first = provenance.input_fingerprint(tmp_path)
    assert first["files"] == 1 and first == provenance.input_fingerprint(tmp_path)
    task.write_text('{"x": 1}')
    assert provenance.input_fingerprint(tmp_path)["sha256"] != first["sha256"]


def test_commit_is_only_reported_for_the_top_of_a_repository(tmp_path):
    def git(*args):
        subprocess.run(["git", "-C", str(tmp_path), *args], check=True, capture_output=True)

    git("init", "-q")
    git("-c", "user.name=t", "-c", "user.email=t@example.com", "commit", "-q", "--allow-empty", "-m", "x")
    inner = tmp_path / "copied_tree"
    inner.mkdir()
    assert provenance.git_head(tmp_path)
    assert provenance.git_head(inner) is None
