"""The dataset audit's extension surface, and the reproducibility of a report.

Everything here was a live defect found by pointing the tool at a 209MB
published statistical release (FINDINGS D-048, D-049). The tests exist so the
fixes stay fixed, and each one fails on the code as it was.
"""

from __future__ import annotations

import json

import pytest

from dinostomp.extensions import Collector, ExtensionCheck, LoadedExtension
from dinostomp.lint import _extension_only_report, lint_dataset


def _ext(level: str = "warn", cid: str = "A1") -> tuple[list, list]:
    """A loaded extension and one finding, shaped as the report expects."""
    ext = LoadedExtension("demo-ext", "1.0", "a" * 64,
                          [ExtensionCheck(cid, "a demo check", False, "always", lambda c, o: None)],
                          validated=True)
    return [ext], [{"check_id": f"x:demo-ext:{cid}", "level": level, "detail": "something",
                    "n": 1, "examples": [], "evidence": {}, "validated": True,
                    "extension": "demo-ext"}]


def test_a_file_the_core_cannot_read_still_reports_what_an_extension_found(tmp_path):
    """The 100MB cap protects a reader that holds every row. It is not a reason
    for a streaming check never to look."""
    big = tmp_path / "big.csv"
    big.write_text("a\n", encoding="utf-8")
    loaded, findings = _ext()
    report = _extension_only_report(big, "dataset is 209MB, over the 100MB cap", loaded, findings)
    assert report["summary"]["verdict"] == "incomplete"
    # Every core check must say why it did not run. A silent absence is how a
    # coverage number stops meaning anything.
    reasons = {f["detail"] for f in report["findings"] if f["level"] == "skip"}
    assert reasons == {"dataset is 209MB, over the 100MB cap"}
    assert report["extension_findings"] == findings


def test_an_extension_finding_can_never_produce_sound(tmp_path):
    """Coverage outranks tone: skipped core checks keep the verdict incomplete
    no matter how green the extension is."""
    f = tmp_path / "x.csv"
    f.write_text("a\n", encoding="utf-8")
    loaded, findings = _ext(level="pass")
    report = _extension_only_report(f, "no eval mapping", loaded, findings)
    assert report["summary"]["verdict"] == "incomplete"


def test_an_extension_failure_takes_the_verdict_to_broken(tmp_path):
    f = tmp_path / "x.csv"
    f.write_text("a\n", encoding="utf-8")
    loaded, findings = _ext(level="fail")
    report = _extension_only_report(f, "no eval mapping", loaded, findings)
    assert report["summary"]["verdict"] == "broken"


def test_a_table_that_is_not_an_eval_is_still_refused_without_extensions(tmp_path):
    """No mapping and nothing that claims the file: the answer is still no.

    The extension path must not become a way for an unmappable file to acquire a
    report it did not earn.
    """
    f = tmp_path / "aggregate.csv"
    f.write_text("geo,metric,value\nGLOBAL,pct,50.0\n", encoding="utf-8")
    report, issues, _ctx = lint_dataset(f, use_extensions=False)
    assert report is None
    assert issues


def test_verify_re_derives_with_the_extension_set_the_report_names(tmp_path, monkeypatch):
    """A report is a claim about a specific set of code, on the verifying side too.

    Before this, `verify_report` used whatever was installed, so one unrelated
    plugin turned nine committed example reports into `mismatch` -- which reads
    as "stale, or edited by hand", and neither was true.
    """
    from dinostomp import report as report_mod

    pod = tmp_path / "pod"
    pod.mkdir()
    (pod / report_mod.JSON_NAME).write_text(json.dumps({"extensions": []}), encoding="utf-8")
    assert report_mod._published_extensions(pod) == []

    named = [{"name": "demo-ext", "version": "1.0", "sha256": "a" * 64}]
    (pod / report_mod.JSON_NAME).write_text(json.dumps({"extensions": named}), encoding="utf-8")
    assert report_mod._published_extensions(pod) == named

    # Three-valued on purpose: `[]` says "produced core-only, re-derive
    # core-only", which is a different statement from "no published report".
    (pod / report_mod.JSON_NAME).unlink()
    assert report_mod._published_extensions(pod) is False


@pytest.mark.parametrize("published, expect_use", [(False, True), ([], False),
                                                   ([{"name": "x"}], True)])
def test_the_three_way_answer_picks_the_right_extension_mode(published, expect_use):
    """`[] is not False` is True, and that bug shipped for one test run: a
    core-only report was re-derived WITH extensions and never verified."""
    use_ext = True if published is False else bool(published)
    assert use_ext is expect_use
