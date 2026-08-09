"""The field this tool can never fill, and the guard that keeps it that way.

Fifty-four checks sounds comprehensive. The ways an eval can be invalid are
unbounded: task selection, ecological validity, distribution mismatch, benchmark
saturation, contamination nobody can observe, strategic behaviour, whether the
construct is the one anyone cares about. A reader seeing "54 of 54 ran" will
reason "so there probably is not much wrong", and that inference is the most
dangerous thing this tool could cause.

A caveat in a paragraph gets skimmed. A field in the artifact that permanently
reads NOT ESTABLISHED does not. These tests are what keep it permanent.
"""

import ast
import json
from pathlib import Path

from dinostomp.cli import main
from dinostomp.lint import CONSTRUCT_VALIDITY, lint_dataset, lint_eval
from dinostomp.runner import OK, run_spec
from tests.test_lint import FLEET, arith_items, write_eval

REPO = Path(__file__).resolve().parents[1]
NEVER = "NOT ESTABLISHED BY DINOSTOMP"


def test_a_perfect_report_still_says_construct_validity_is_not_established(tmp_path):
    """The strongest possible verdict must carry the strongest possible caveat.

    A green run is exactly when someone stops reading, which is exactly when
    this has to be on screen.
    """
    pod = write_eval(tmp_path, arith_items(), models=FLEET)
    assert run_spec(pod).exit_code == OK
    report, _ = lint_eval(pod)
    assert report["summary"]["verdict"] == "sound"
    assert report["construct_validity"]["measures_the_intended_construct"] == NEVER


def test_a_dataset_audit_carries_it_too(tmp_path):
    rows = [{"question": f"q{i}", "answer": f"a{i}"} for i in range(20)]
    p = tmp_path / "d.jsonl"
    p.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    report, _, _ = lint_dataset(p)
    assert report["construct_validity"]["measures_the_intended_construct"] == NEVER


def test_nothing_in_the_source_can_set_it_to_anything_else():
    """The architectural half.

    A constant that some code path could overwrite is a caveat, not a boundary.
    This walks the AST of every shipped module and asserts that
    `measures_the_intended_construct` is only ever assigned the refusal.
    """
    offenders = []
    for path in sorted((REPO / "src" / "dinostomp").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            # dict literals: {"measures_the_intended_construct": ...}
            if isinstance(node, ast.Dict):
                for k, v in zip(node.keys, node.values):
                    if isinstance(k, ast.Constant) and k.value == "measures_the_intended_construct":
                        if not (isinstance(v, ast.Constant) and v.value == NEVER):
                            offenders.append(f"{path.name}:{node.lineno} assigns a non-constant")
            # subscript writes: report[...]["measures_the_intended_construct"] = ...
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if (isinstance(target, ast.Subscript)
                            and isinstance(target.slice, ast.Constant)
                            and target.slice.value == "measures_the_intended_construct"):
                        offenders.append(f"{path.name}:{node.lineno} writes the field")
    assert not offenders, (
        "construct validity became fillable: " + "; ".join(offenders))


def test_the_cli_prints_it_on_every_verdict(tmp_path, capsys):
    pod = write_eval(tmp_path, arith_items(), models=FLEET)
    main(["run", str(pod)])
    capsys.readouterr()
    main(["stomp", str(pod)])
    out = capsys.readouterr().out
    assert NEVER in out
    assert "Mechanical integrity is not construct validity" in out


def test_the_word_sound_never_stands_alone_in_output(tmp_path, capsys):
    """"SOUND 54/54" gets screenshotted and read as a grade.

    Interface semantics beat documentation, so the qualifier rides on the
    verdict rather than sitting in a paragraph below it.
    """
    pod = write_eval(tmp_path, arith_items(), models=FLEET)
    main(["run", str(pod)])
    capsys.readouterr()
    main(["stomp", str(pod)])
    lines = [l for l in capsys.readouterr().out.splitlines() if "SOUND" in l]
    assert lines, "the sound path did not run"
    for line in lines:
        assert "MECHANICALLY SOUND" in line, f"a bare SOUND escaped: {line!r}"


def test_the_badge_says_integrity_not_sound(tmp_path):
    """The badge travels furthest from its own documentation."""
    import re

    from dinostomp.report import render_badge

    pod = write_eval(tmp_path, arith_items(), models=FLEET)
    run_spec(pod)
    report, _ = lint_eval(pod)
    label = re.search(r">([a-z]+) \d+/\d+<", render_badge(report)).group(1)
    assert label == "integrity", f"the badge says {label!r}, which a reader will hear as a grade"


def test_the_explanation_names_what_would_establish_it():
    """Refusing to answer is only honest if it says who could."""
    why = CONSTRUCT_VALIDITY["what_would"]
    assert "argued, not computed" in why
    assert "external criterion" in why
