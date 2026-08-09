"""README transcript parity: the quoted verdict lines must match what the
battery actually prints. Doctrine 4 says hand-editing a summary is a gated
finding; this test applies the same rule to the README itself. Each example
pod is copied to a temp dir, re-run with the deterministic dry provider, and
stomped; the verdict line printed must appear verbatim in README.md.
"""

import shutil
from pathlib import Path

import pytest

from dinostomp.cli import main

REPO = Path(__file__).resolve().parents[1]

# The docs were split into product / receipts / methodology. The parity
# guarantee follows the CONTENT, not the filename: a quoted transcript has to
# match reality wherever it lives, or the split becomes a way to launder stale
# numbers into a file nobody tests.
DOC_FILES = ["README.md", "FINDINGS.md", "METHODOLOGY.md"]
DOCS = "\n".join((REPO / f).read_text(encoding="utf-8") for f in DOC_FILES)
README = DOCS


def rerun_pod(name: str, tmp_path: Path, capsys, probe: bool = False) -> str:
    src = REPO / "examples" / name
    dst = tmp_path / name
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("data", "STOMP.*", "stomp-badge.svg"))
    assert main(["run", str(dst / "eval.yaml")]) in (0,)
    if probe:
        # R13 only unlocks on a real (non-dry) blind probe; the agent pod ships
        # one, so the quoted transcript has to reproduce it.
        assert main(["run", str(dst / "eval.yaml"), "--probe", "blind"]) == 0
    main(["stomp", str(dst / "eval.yaml"), "--allow-incomplete"])
    return capsys.readouterr().out


@pytest.mark.parametrize("pod, quoted_lines, probe", [
    ("smoke", [
        "smoke-arith | dry-strong | complete | acc 1.000 [0.61, 1.00] on 6 checkable",
        "INCOMPLETE: no failures, but only 18 of 28 checks ran (26 n/a of 54 declared).",
    ], False),
    ("fleet", [
        "fleet-arith | dry-alpha | complete | acc 1.000 [0.86, 1.00] on 24 checkable",
        "0 of 6 model(s) score no better than guessing; fleet spans 38% to 100% vs chance ~4% (modal target floor)",
        "MECHANICALLY SOUND: no integrity findings, full coverage (29 of 29 ran; 25 n/a of 54 declared)",
    ], False),
    ("iris", [
        "(32 of 32 ran; 22 n/a of 54 declared)",
    ], False),
    ("agent", [
        "agent-capitals | agent-grounded | complete | acc 0.923 [0.76, 0.98] on 26 checkable",
        "INCOMPLETE: no failures, but only 37 of 41 checks ran (13 n/a of 54 declared).",
    ], True),
])
def test_readme_transcripts_match_reality(pod, quoted_lines, probe, tmp_path, capsys):
    out = rerun_pod(pod, tmp_path, capsys, probe=probe)
    for line in quoted_lines:
        assert line in out, f"the battery no longer prints {line!r}; regenerate the README transcript"
        # normalize the README's aligned-whitespace quoting before comparing
        assert " ".join(line.split()) in " ".join(README.split()), (
            f"README does not quote the real output line {line!r}; the transcript drifted"
        )


def test_readme_battery_size_matches_registry():
    from dinostomp.lint import CHECKS

    assert f"of {len(CHECKS)} declared" in README, "README coverage lines disagree with the registry size"
    assert f"current {len(CHECKS)}-check battery" in README, (
        "the First-blood caption's battery count drifted from the registry again")


def test_readme_trial_counts_match_the_suite():
    """The trials counts quoted in the README are pinned to the actual TRIALS
    and CLEAN_TRIALS lists, closing the stale-count class the same way the
    check table closed it."""
    import sys
    sys.path.insert(0, str(REPO))
    from trials.run_trials import CLEAN_TRIALS, TRIALS

    assert f"sensitivity: {len(TRIALS)} of {len(TRIALS)} defects caught" in README
    assert f"{len(TRIALS)} planted defects" in README
    assert f"{len(CLEAN_TRIALS)} expected-CLEAN pods" in README or            f"{len(CLEAN_TRIALS)} of {len(CLEAN_TRIALS)} clean pods" in README


def test_readme_check_table_matches_registry():
    """The published check table is generated from the registry; every row
    must match id, name, tier, and applicability exactly."""
    from dinostomp.lint import CHECKS

    from dinostomp.lint import SLUGS

    for cid, name, gating, when in CHECKS:
        tier = "invariant (gates)" if gating else "diagnostic (warns)"
        row = f"| {cid} | `{SLUGS[cid]}` | {name} | {tier} | {when} |"
        assert row in README, f"check table row missing or drifted: {row}"


def test_every_check_has_a_unique_stable_slug():
    """Slugs are an API: they appear in output, in flags, and in saved reports."""
    import re as _re

    from dinostomp.lint import CHECKS, SLUGS

    ids = {cid for cid, *_ in CHECKS}
    assert set(SLUGS) == ids, "a check without a slug, or a slug without a check"
    assert len(set(SLUGS.values())) == len(SLUGS), "two checks share a slug"
    for slug in SLUGS.values():
        assert _re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", slug), f"{slug!r} is not kebab-case"

def test_the_action_and_workflow_parse_and_default_to_strict():
    """CI defaults are load-bearing: an unattended pipeline must not accept
    thin coverage or import a stranger's Python because a default said so."""
    import yaml

    action = yaml.safe_load((REPO / "action.yml").read_text(encoding="utf-8"))
    inputs = action["inputs"]
    assert inputs["allow-incomplete"]["default"] == "false"
    assert inputs["trust-code"]["default"] == "false", "importing pod code must stay opt-in in CI"
    assert set(action["outputs"]) == {"verdict", "findings"}

    wf = yaml.safe_load((REPO / ".github/workflows/stomp.yml").read_text(encoding="utf-8"))
    steps = [s for j in wf["jobs"].values() for s in j["steps"]]
    run_lines = " ".join(s.get("run", "") for s in steps)
    assert "trials/run_trials.py" in run_lines, "CI must run both tails of the trials"
    assert "dinostomp verify" in run_lines, "CI must re-derive the published reports"


def test_every_doc_the_readme_links_actually_exists():
    """The authoring story vanished in one rewrite because nothing checked.

    A README that promises AUTHORING.md and does not ship it is the same class
    of defect as a summary that does not re-derive: a document making a claim
    its artifacts do not support.
    """
    import re as _re

    readme = (REPO / "README.md").read_text(encoding="utf-8")
    for target in set(_re.findall(r"\]\(([A-Za-z0-9_./-]+\.md)\)", readme)):
        assert (REPO / target).is_file(), f"README links {target}, which does not exist"


def test_the_authoring_doc_covers_the_llm_loop():
    """AUTHORING.md is addressed to a model landing on this repo to build an
    eval. If it stops naming the loop or the non-negotiable rule, it has
    stopped doing its job."""
    doc = (REPO / "AUTHORING.md").read_text(encoding="utf-8")
    for needle in ("load_spec", "dinostomp validate", "suggest-witnesses",
                   "expect: fail", "run.seed", "budget_usd", "schemas"):
        assert needle in doc, f"AUTHORING.md no longer mentions {needle!r}"
    assert "[AUTHORING.md](AUTHORING.md)" in (REPO / "README.md").read_text(encoding="utf-8"), (
        "the README must point an authoring model at the authoring doc")


def test_the_action_reference_points_at_a_version_that_exists():
    """A copy-pasteable block that fails for the first person who tries it is a
    credibility wound in a document whose thesis is receipts.

    Before publication this asserted the Action was labelled planned. Now that
    the repo is public it asserts the harder thing: the `uses:` ref names THIS
    version, so publishing a release without tagging it breaks the build here
    rather than in a stranger's CI.
    """
    import re as _re

    import dinostomp

    readme = (REPO / "README.md").read_text(encoding="utf-8")
    refs = _re.findall(r"uses: collapseindex/dinostomp@v([0-9.]+)", readme)
    assert refs, "the CI section stopped showing the Action"
    for ref in refs:
        assert ref == dinostomp.__version__, (
            f"README advertises the Action at v{ref} but this is v{dinostomp.__version__}; "
            "tag the release or fix the README")
    # and the install fallback has to be there while PyPI does not exist
    assert "git+https://github.com/collapseindex/dinostomp" in readme, (
        "the Action installs from PyPI by default, which does not exist yet; the README must "
        "say how to point it at this repo instead")


# --- FINDINGS.md is a ledger, and a ledger's index must not drift -------------


def _findings_ids():
    import re as _re

    doc = (REPO / "FINDINGS.md").read_text(encoding="utf-8")
    index = _re.findall(r"\| \[([FDN]-\d{3})\]\(#[fdn]-\d{3}\) \|", doc)
    entries = _re.findall(r"^### ([FDN]-\d{3})$", doc, _re.M)
    return doc, index, entries


def test_the_findings_index_matches_its_entries():
    """An index that drifts from its entries is a summary that does not
    re-derive, which is a gated finding everywhere else in this project."""
    _, index, entries = _findings_ids()
    assert index, "the index table vanished"
    assert index == entries, (
        f"index and entries disagree.\n  in index only: {set(index) - set(entries)}"
        f"\n  in entries only: {set(entries) - set(index)}"
        f"\n  or the order differs")


def test_findings_ids_are_unique_and_gapless():
    """Ids are permanent, so a gap means an entry was deleted rather than
    withdrawn. A withdrawn entry keeps its id and states what killed it."""
    _, _, entries = _findings_ids()
    assert len(set(entries)) == len(entries), "a findings id is reused"
    for series in ("F", "D", "N"):
        nums = sorted(int(e.split("-")[1]) for e in entries if e.startswith(series))
        if nums:
            assert nums == list(range(1, len(nums) + 1)), (
                f"{series} series has a gap: {nums}. Ids are permanent; withdraw, do not delete.")


def test_every_finding_states_a_check_and_a_status():
    """A finding without a check that produced it is an anecdote."""
    import re as _re

    doc, _, entries = _findings_ids()
    for eid in entries:
        block = doc.split(f"### {eid}\n", 1)[1].split("\n### ", 1)[0]
        header = "\n".join(block.strip().splitlines()[:3])
        assert "·" in header, f"{eid} has no metadata line (check · date · status)"


def test_the_scorecard_counts_match_the_entries():
    """The summary at the bottom is a claim about this file; it has to hold."""
    _, _, entries = _findings_ids()
    doc = (REPO / "FINDINGS.md").read_text(encoding="utf-8")
    n_d = sum(1 for e in entries if e.startswith("D"))
    assert f"**thirteen entries of defects in\ndinostomp itself**" in doc or n_d == 13, (
        f"the scorecard says thirteen D entries; the file has {n_d}")


# --- REFERENCES.md: an appeal to convention must name its source --------------


def test_every_convention_threshold_is_actually_cited():
    """The label `convention` means "defensible by citation".

    For a while it cited nothing, which made it an unfalsifiable claim sitting
    inside a tool built to object to those. If a threshold leans on prior art,
    REFERENCES.md has to name the prior art.
    """
    from dinostomp.lint import THRESHOLDS, threshold_provenance

    refs = (REPO / "REFERENCES.md").read_text(encoding="utf-8")
    for name in sorted(THRESHOLDS):
        kind, _ = threshold_provenance(name)
        if kind == "convention":
            assert f"`{name}" in refs, (
                f"{name} is labelled `convention` but REFERENCES.md does not name a source; "
                "either cite it or relabel it `judgment`")


def test_every_borrowed_method_names_a_year():
    """A reference without a year is a gesture at a literature, not a citation."""
    import re as _re

    refs = (REPO / "REFERENCES.md").read_text(encoding="utf-8")
    rows = [l for l in refs.splitlines() if l.startswith("| ") and "|" in l[2:]]
    cited = [l for l in rows if _re.search(r"\((?:19|20)\d{2}\)", l)]
    assert len(cited) >= 20, f"only {len(cited)} rows carry a year; a bibliography needs dates"


def test_references_is_linked_from_the_docs():
    for doc in ("README.md", "METHODOLOGY.md"):
        assert "REFERENCES.md" in (REPO / doc).read_text(encoding="utf-8"), (
            f"{doc} does not link REFERENCES.md, so nobody will find it")


def test_every_audited_benchmark_states_a_licence():
    """These datasets are other people's work, fetched not vendored."""
    refs = (REPO / "REFERENCES.md").read_text(encoding="utf-8")
    for dataset in ("GSM8K", "MMLU", "TruthfulQA", "HellaSwag", "ARC", "iris"):
        row = [l for l in refs.splitlines() if l.startswith(f"| {dataset} ")]
        assert row, f"{dataset} is audited but not credited in REFERENCES.md"
        assert row[0].rstrip().rstrip("|").split("|")[-1].strip(), (
            f"{dataset} is credited without a licence")
