"""The engine's own hash: what a reader checks to know which bytes judged them."""

import re
from pathlib import Path

from dinostomp.fingerprint import engine_files, engine_fingerprint, short

REPO = Path(__file__).resolve().parents[1]
README = (REPO / "README.md").read_text(encoding="utf-8")


def test_fingerprint_is_stable_across_calls():
    assert engine_fingerprint() == engine_fingerprint()
    assert re.fullmatch(r"[0-9a-f]{64}", engine_fingerprint())


def test_fingerprint_covers_code_and_schemas_only():
    names = {p.name for p in engine_files()}
    assert "lint.py" in names and "runner.py" in names
    assert "eval.schema.json" in names
    assert not any(n.endswith(".md") for n in names), (
        "the README publishes this value; hashing it would make the number "
        "impossible to state correctly")


def test_moving_a_file_moves_the_fingerprint(tmp_path):
    (tmp_path / "a.py").write_text("x = 1\n", encoding="utf-8")
    before = engine_fingerprint(tmp_path)
    (tmp_path / "a.py").rename(tmp_path / "b.py")
    assert engine_fingerprint(tmp_path) != before, "path is part of the digest, not just bytes"


def test_line_endings_do_not_change_the_fingerprint(tmp_path):
    # A checkout that converted CRLF is the same engine and must not read as a
    # different one; otherwise the published hash is unusable on Windows.
    (tmp_path / "a.py").write_bytes(b"x = 1\ny = 2\n")
    unix = engine_fingerprint(tmp_path)
    (tmp_path / "a.py").write_bytes(b"x = 1\r\ny = 2\r\n")
    assert engine_fingerprint(tmp_path) == unix


def test_editing_a_shipped_file_moves_the_fingerprint(tmp_path):
    (tmp_path / "a.py").write_text("x = 1\n", encoding="utf-8")
    before = engine_fingerprint(tmp_path)
    (tmp_path / "a.py").write_text("x = 2\n", encoding="utf-8")
    assert engine_fingerprint(tmp_path) != before


def test_readme_publishes_the_current_fingerprint():
    """An audit tool that publishes a stale hash is worse than one that
    publishes none: a reader would confirm authenticity against a lie."""
    current = short()
    assert f"`{current}`" in README, (
        f"README pins a stale engine fingerprint; the current one is {current}. "
        "Run `dinostomp fingerprint` and update the line under the version."
    )


def test_r19_warns_when_runs_came_from_a_different_engine(tmp_path):
    """tool_sha256 was recorded in every manifest and read by nothing.

    That made the engine the one input inside the drift boundary that could
    change without anyone being told, which matters because a scorer fix
    between the run and the audit changes what the recorded verdicts mean.
    """
    import json

    from dinostomp.lint import lint_eval
    from dinostomp.runner import OK, run_spec
    from tests.test_lint import arith_items, finding, write_eval

    pod = write_eval(tmp_path, arith_items())
    assert run_spec(pod).exit_code == OK
    assert finding(lint_eval(pod)[0], "R19")["level"] == "pass", "fresh runs are current"

    mf = next((tmp_path / "data" / "runs").glob("*_manifest.json"))
    m = json.loads(mf.read_text(encoding="utf-8"))
    m["tool_sha256"] = "0" * 64
    m["tool_version"] = "0.1.0"
    mf.write_text(json.dumps(m), encoding="utf-8")

    r19 = finding(lint_eval(pod)[0], "R19")
    assert r19["level"] == "warn"
    assert "0000000000000000" in " ".join(r19["examples"])
    assert r19["level"] != "fail", "upgrading the tool must not brick every pod"


def test_r19_is_not_applicable_when_no_manifest_stamps_an_engine(tmp_path):
    import json

    from dinostomp.lint import lint_eval
    from dinostomp.runner import OK, run_spec
    from tests.test_lint import arith_items, finding, write_eval

    pod = write_eval(tmp_path, arith_items())
    assert run_spec(pod).exit_code == OK
    mf = next((tmp_path / "data" / "runs").glob("*_manifest.json"))
    m = json.loads(mf.read_text(encoding="utf-8"))
    m.pop("tool_sha256")
    mf.write_text(json.dumps(m), encoding="utf-8")
    assert finding(lint_eval(pod)[0], "R19")["level"] == "n/a"
