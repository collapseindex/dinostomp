"""Mounts: how a pod may depend on code outside itself without losing the boundary.

The rule the README states is that anything influencing a run gets its SHA-256
into the manifest. A shared `mounts/` folder was the standing exception, and
these tests are the exception closing.
"""

import json
from pathlib import Path

import yaml

from dinostomp.lint import lint_eval, pod_code_paths
from dinostomp.runner import OK, run_spec
from dinostomp.spec import load_spec

NL = chr(10)


def workspace(tmp_path, declare=True):
    """A pod whose scorer lives one directory up, in a shared mounts folder."""
    shared = tmp_path / "mounts"
    shared.mkdir(parents=True, exist_ok=True)
    (shared / "shared_scorer.py").write_text(
        f"def score(output, target):{NL}    return str(output).strip() == str(target){NL}",
        encoding="utf-8")

    pod = tmp_path / "pod"
    pod.mkdir(parents=True, exist_ok=True)
    items = [{"id": f"a{i}", "input": f"What is {i} + {i + 1}? Reply with the bare number.",
              "target": str(2 * i + 1)} for i in range(10, 34)]
    spec = {
        "name": "mounted-pod", "version": "0.1.0",
        "question": "Does a pod get to share a scorer without losing the drift boundary?",
        "data": {"path": "items.jsonl", "format": "jsonl"},
        "models": [{"provider": "dry", "model": "dry-strong"}],
        "scorer": {"kind": "python", "code": "../mounts/shared_scorer.py", "witnesses": [
            {"output": "57", "target": "57", "expect": "pass"},
            {"output": "The answer is 57", "target": "57", "expect": "fail"},
            {"output": "5", "target": "57", "expect": "fail"},
            {"output": "not 57", "target": "57", "expect": "fail"}]},
        "run": {"n": 24, "seed": 42, "budget_usd": 0},
    }
    if declare:
        spec["mounts"] = ["../mounts/shared_scorer.py"]
    lines = ['{"_canary": "dinostomp canary DO NOT TRAIN mounts"}']
    lines += [json.dumps(i) for i in items]
    (pod / "items.jsonl").write_text(NL.join(lines) + NL, encoding="utf-8")
    (pod / "eval.yaml").write_text(yaml.safe_dump(spec), encoding="utf-8")
    return pod / "eval.yaml", shared / "shared_scorer.py"


def test_an_undeclared_path_still_may_not_leave_the_pod():
    """Traversal protection is not weakened by the feature: declaring is what
    makes it legal, because declaring is what gets it hashed."""


def test_undeclared_traversal_is_refused(tmp_path):
    spec, _ = workspace(tmp_path, declare=False)
    _, issues = load_spec(spec)
    assert any("escapes the eval directory" in i.message for i in issues)
    assert any("declare it under `mounts`" in i.message for i in issues), (
        "the refusal should say how to do it deliberately")


def test_declaring_a_mount_makes_it_legal(tmp_path):
    spec, _ = workspace(tmp_path)
    _, issues = load_spec(spec)
    assert issues == []


def test_a_mount_is_hashed_into_every_manifest(tmp_path):
    spec, _ = workspace(tmp_path)
    outcome = run_spec(spec)
    assert outcome.exit_code == OK
    manifest = json.loads(outcome.run_files[0].with_name(
        outcome.run_files[0].stem + "_manifest.json").read_text(encoding="utf-8"))
    mounts = manifest["mount_sha256"]
    assert list(mounts) == ["../mounts/shared_scorer.py"]
    assert len(mounts["../mounts/shared_scorer.py"]) == 64


def test_editing_shared_code_after_a_run_is_drift(tmp_path):
    """The whole point. Spooky action at a distance was the reason mounts were
    withheld; this is what makes them safe to use."""
    spec, shared = workspace(tmp_path)
    assert run_spec(spec).exit_code == OK
    shared.write_text(shared.read_text(encoding="utf-8") + f"{NL}# tweak{NL}", encoding="utf-8")
    report, _ = lint_eval(spec, trust_code=True)
    r1 = next(f for f in report["findings"] if f["id"] == "R1")
    assert r1["level"] == "fail"
    assert any("mount" in e for e in r1["examples"])


def test_a_missing_mount_is_caught_at_load_time(tmp_path):
    spec, shared = workspace(tmp_path)
    shared.unlink()
    _, issues = load_spec(spec)
    assert any("mount not found" in i.message for i in issues)


def test_mounted_python_needs_trust_code_like_any_other(tmp_path):
    """Code from outside the pod deserves at least as much suspicion as the
    pod's own, not less."""
    spec, _ = workspace(tmp_path)
    obj = yaml.safe_load(Path(spec).read_text(encoding="utf-8"))
    assert "../mounts/shared_scorer.py" in pod_code_paths(obj)
    report, _ = lint_eval(spec)
    assert next(f for f in report["findings"] if f["id"] == "R2")["level"] == "skip"


def test_an_absolute_mount_is_refused(tmp_path):
    spec, shared = workspace(tmp_path)
    obj = yaml.safe_load(Path(spec).read_text(encoding="utf-8"))
    obj["mounts"] = [str(shared.resolve())]
    Path(spec).write_text(yaml.safe_dump(obj), encoding="utf-8")
    _, issues = load_spec(spec)
    assert any("must be relative" in i.message for i in issues)
