"""Report renderer tests: content contract, diff-cleanliness, and the
teeth (a broken pod's report must refuse to publish claims)."""

import json
from pathlib import Path

from dinostomp.cli import main
from dinostomp.lint import CHECKS
from dinostomp.report import BADGE_NAME, JSON_NAME, MD_NAME, write_report


def make_pod(tmp_path):
    pod = tmp_path / "p"
    main(["new", str(pod)])
    main(["run", str(pod / "eval.yaml")])
    return pod


def test_report_writes_all_three_artifacts(tmp_path):
    pod = make_pod(tmp_path)
    report, issues, written = write_report(pod / "eval.yaml")
    assert issues == []
    assert {p.name for p in written} == {MD_NAME, JSON_NAME, BADGE_NAME}
    assert all(p.exists() for p in written)


def test_markdown_content_contract(tmp_path):
    pod = make_pod(tmp_path)
    write_report(pod / "eval.yaml")
    md = (pod / MD_NAME).read_text(encoding="utf-8")
    assert "INCOMPLETE" in md, "single-model pod reports incomplete"
    assert f"n/a of {len(CHECKS)} declared" in md, "full battery size always visible"
    assert "resolves gaps down to" in md, "the MDE line keeps point estimates honest"
    assert "offline dry provider" in md, "dry-ness disclosed"
    assert "not currently entitled to publish claims" in md, "no claims without a green verdict"
    assert "<details>" in md, "receipts are collapsible"
    assert "spec_sha256" in md, "provenance hashes present"


def test_json_next_to_markdown_and_consistent(tmp_path):
    pod = make_pod(tmp_path)
    write_report(pod / "eval.yaml")
    report = json.loads((pod / JSON_NAME).read_text(encoding="utf-8"))
    md = (pod / MD_NAME).read_text(encoding="utf-8")
    assert report["summary"]["verdict"] == "incomplete"
    assert "generated_at" not in report, "published raw report is byte-stable; timestamps live in manifests"
    assert "generated_at" not in md, "markdown omits volatile fields by design"
    for f in report["findings"]:
        assert f["check"] in md, f"finding {f['id']} missing from markdown"


def test_rereport_is_byte_identical_when_nothing_changed(tmp_path):
    pod = make_pod(tmp_path)
    write_report(pod / "eval.yaml")
    names = (MD_NAME, JSON_NAME, BADGE_NAME)
    first = tuple((pod / n).read_bytes() for n in names)
    write_report(pod / "eval.yaml")
    second = tuple((pod / n).read_bytes() for n in names)
    assert first == second, "ALL published report artifacts live in git; an unchanged pod must not diff"


def test_broken_pod_report_and_exit_code(tmp_path):
    pod = make_pod(tmp_path)
    spec_path = pod / "eval.yaml"
    spec_path.write_text(spec_path.read_text(encoding="utf-8") + "\n# post-run tweak\n", encoding="utf-8")
    assert main(["report", str(spec_path)]) == 1
    md = (pod / MD_NAME).read_text(encoding="utf-8")
    badge = (pod / BADGE_NAME).read_text(encoding="utf-8")
    assert "BROKEN" in md
    assert "None." in md, "a broken report explicitly refuses claims"
    assert "broken" in badge


def test_incomplete_report_is_nonzero_by_default(tmp_path):
    pod = make_pod(tmp_path)
    assert main(["report", str(pod / "eval.yaml")]) == 4
    assert main(["report", str(pod / "eval.yaml"), "--allow-incomplete"]) == 0
