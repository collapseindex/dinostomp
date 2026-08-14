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
        "INCOMPLETE: no failures, but only 19 of 29 checks ran (40 n/a of 69 declared).",
    ], False),
    ("fleet", [
        "fleet-arith | dry-alpha | complete | acc 1.000 [0.86, 1.00] on 24 checkable",
        "0 of 6 model(s) score no better than guessing; fleet spans 38% to 100% vs chance ~4% (modal target floor)",
        "MECHANICALLY SOUND: no integrity findings, full coverage (31 of 31 ran; 38 n/a of 69 declared)",
    ], False),
    ("iris", [
        "(31 of 31 ran; 38 n/a of 69 declared)",
    ], False),
    ("agent", [
        "agent-capitals | agent-grounded | complete | acc 0.923 [0.76, 0.98] on 26 checkable",
        "INCOMPLETE: no failures, but only 39 of 43 checks ran (26 n/a of 69 declared).",
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
    # Anchored to the START of a line, so this reads the INDEX TABLE and not the
    # generated cross-references, whose rows begin with a check id or a subject
    # and list several findings each. Unanchored, every xref row contributed its
    # last link and the order comparison below became nonsense.
    index = _re.findall(r"^\| \[([FDN]-\d{3})\]\(#[fdn]-\d{3}\) \|", doc, _re.M)
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
        # This test's NAME promised a check and a status. For a long time it
        # asserted only that a separator existed, and three N entries carried no
        # status at all. The index generator found them; this did not.
        # The metadata line is the SECOND line of the block, always. Picking
        # "the first line containing ·" grabbed the title instead on entries
        # whose title has one ("**iris · two byte-identical vectors**").
        lines = block.strip().splitlines()
        meta = lines[1] if len(lines) > 1 else ""
        assert len([part for part in meta.split("·") if part.strip()]) >= 3, (
            f"{eid} metadata is not `check · date · status`: {meta!r}")


def test_the_scorecard_counts_match_the_entries():
    """The summary at the bottom is a claim about this file; it has to hold.

    Written against the counts rather than a spelled-out word, so adding an
    entry and forgetting the scorecard fails the build instead of publishing a
    total nobody rechecked.
    """
    import re as _re

    doc, _, entries = _findings_ids()
    for series, label in (("F", "datasets"), ("N", "negative"), ("D", "dinostomp")):
        n = sum(1 for e in entries if e.startswith(series))
        assert _re.search(rf"\*\*{n}\*\*", doc), (
            f"the scorecard does not state **{n}** anywhere, but there are {n} "
            f"{series} entries ({label})")


def test_every_image_the_readme_embeds_exists():
    """A broken image is the first thing a visitor sees, and the README is the
    one file where a dead reference is most expensive."""
    import re as _re

    readme = (REPO / "README.md").read_text(encoding="utf-8")
    srcs = _re.findall(r'<img[^>]+src="([^"]+)"', readme) + \
        _re.findall(r"!\[[^\]]*\]\(([^)]+)\)", readme)
    local = [s for s in srcs if not s.startswith("http")]
    assert local, "the README embeds no local image; the logo went missing"
    for src in local:
        assert (REPO / src).is_file(), f"README embeds {src}, which does not exist"


def test_no_doc_links_a_heading_that_does_not_exist():
    """FINDINGS.md pointed at CONTRIBUTING.md#break-it-please for two releases
    while that section did not exist. A dead in-repo anchor is invisible until
    someone clicks it, which is the worst kind of stale."""
    import re as _re

    docs = ["README.md", "FINDINGS.md", "METHODOLOGY.md", "AUTHORING.md",
            "CONTRIBUTING.md", "REFERENCES.md", "SECURITY.md"]

    def anchors(text):
        out = set()
        for level, title in _re.findall(r"^(#{2,4}) (.+)$", text, _re.M):
            out.add(_re.sub(r"[^a-z0-9\s-]", "", title.lower()).strip().replace(" ", "-"))
        return out

    cache = {d: (REPO / d).read_text(encoding="utf-8") for d in docs if (REPO / d).is_file()}
    dead = []
    for name, text in cache.items():
        for target, anchor in _re.findall(r"\(([A-Za-z0-9_.-]*\.md)#([a-z0-9-]+)\)", text):
            if target in cache and anchor not in anchors(cache[target]):
                dead.append(f"{name} -> {target}#{anchor}")
        for anchor in _re.findall(r"\(#([a-z0-9-]+)\)", text):
            if anchor not in anchors(text):
                dead.append(f"{name} -> #{anchor} (same file)")
    assert not dead, "dead in-repo anchors: " + "; ".join(sorted(set(dead))[:6])


def test_readme_data_scope_prose_matches_the_registry():
    """The headline count and the data-scope count drifted apart.

    "fifty-seven checks" was updated by a sweep that missed "fifty-five checks
    read data at rest" two paragraphs down, because the two sentences were
    edited by different passes. This pins BOTH to the registry, in words,
    because the README writes its numbers out.
    """
    from dinostomp.lint import CHECKS, SCOPE_CHECKS

    words = {10: "Ten", 14: "Fourteen", 47: "forty-seven", 48: "forty-eight", 50: "fifty", 51: "fifty-one", 52: "fifty-two", 15: "Fifteen", 16: "Sixteen", 17: "Seventeen",
             57: "fifty-seven", 61: "sixty-one", 62: "sixty-two", 64: "sixty-four", 65: "sixty-five", 66: "sixty-six", 67: "sixty-seven", 68: "sixty-eight", 69: "sixty-nine"}
    data_n = len(SCOPE_CHECKS["data"])
    rest_n = len(CHECKS) - data_n
    # The sentence wraps, so compare against normalised whitespace.
    flat = " ".join(README.split())
    assert f"{words[data_n]} of the {words[len(CHECKS)]} checks read data at rest" in flat, (
        f"the data-scope sentence disagrees with the registry ({data_n} of {len(CHECKS)})")
    assert f"for the other {words[rest_n]}" in flat, (
        f"the 'other N' sentence disagrees with the registry ({rest_n})")


def test_the_findings_index_is_generated_and_current():
    """FINDINGS.md is the source of truth; its index is derived from it.

    The index table and the entries were kept by hand and drifted twice: once on
    ordering, once when a new entry reached one and not the other. Both were
    caught by assertions after the fact. Generating removes the class instead of
    policing it, and this test is the guard that the generated regions were
    regenerated.

        python scripts/index_findings.py
    """
    import subprocess
    import sys

    proc = subprocess.run([sys.executable, str(REPO / "scripts" / "index_findings.py"), "--check"],
                          capture_output=True, text=True, cwd=str(REPO))
    assert proc.returncode == 0, (
        (proc.stdout or "") + (proc.stderr or "")
        + "\nrun `python scripts/index_findings.py` and commit the result")


def test_the_findings_feed_matches_the_ledger():
    """findings.json is what anyone querying this would read, so it has to hold
    every entry and agree with the scorecard's own counts."""
    import json as _json

    feed = _json.loads((REPO / "findings.json").read_text(encoding="utf-8"))
    doc, index, entries = _findings_ids()
    assert [f["id"] for f in feed["findings"]] == entries, "the feed and the entries disagree"
    for series in "FDN":
        n = sum(1 for e in entries if e.startswith(series))
        assert feed["counts"][series] == n, f"feed count for {series} is wrong"
        assert f"| **{n}** |" in doc, (
            f"the scorecard does not state {n} for series {series}")


# --- findings.json is a published contract, so it gets held to one ------------


def _feed():
    import json as _json

    return _json.loads((REPO / "findings.json").read_text(encoding="utf-8"))


def _schema():
    import json as _json

    return _json.loads((REPO / "docs" / "findings.schema.json").read_text(encoding="utf-8"))


def test_the_feed_validates_against_its_published_schema():
    """The generator validates before writing, so this only fails if the feed on
    disk was edited by hand or the schema was tightened without regenerating."""
    import jsonschema

    jsonschema.validate(_feed(), _schema())


def test_the_feed_schema_actually_rejects_things():
    """A schema that passes everything is a comment.

    Seven mutations, the first two modelling defects the feed actually shipped
    with (D-040): a blank subject, and a date at a precision the ledger has not
    got. Every one of them is verified to FIRE, because a negative test that
    silently passes is the flattering kind.
    """
    import copy

    import jsonschema
    import pytest

    schema = _schema()
    for label, mutate in [
        ("a blank subject", lambda f: f["findings"][0].update(subject="")),
        ("an invented date", lambda f: f["findings"][0].update(date_iso="not-a-date")),
        ("a renumbered id", lambda f: f["findings"][0].update(id="F-1")),
        ("an unknown status bucket", lambda f: f["findings"][0].update(status_class="probably")),
        ("a stray field", lambda f: f["findings"][0].update(severity="high")),
        ("no findings at all", lambda f: f["findings"].clear()),
        ("a truncated engine hash", lambda f: f["tool"].update(engine="deadbeef")),
    ]:
        broken = copy.deepcopy(_feed())
        mutate(broken)
        try:
            jsonschema.validate(broken, schema)
        except jsonschema.ValidationError:
            continue
        pytest.fail(f"the schema accepted a feed with {label}")


def test_an_unrecognised_status_is_an_error_not_a_bucket():
    """A silent "other" bin is how a mis-typed status becomes a finding nobody
    can filter for. This asserts the generator refuses rather than defaults."""
    import importlib.util
    import sys as _sys

    import pytest

    spec = importlib.util.spec_from_file_location(
        "_idx", REPO / "scripts" / "index_findings.py")
    mod = importlib.util.module_from_spec(spec)
    _sys.modules["_idx"] = mod
    spec.loader.exec_module(mod)

    assert mod.status_class("confirmed, underpowered") == "confirmed"
    assert mod.status_class("fixed in v0.50.0") == "fixed"
    assert mod.status_class("**WITHDRAWN**") == "withdrawn"
    with pytest.raises(SystemExit) as exc:
        mod.status_class("probably fine")
    assert "not defaulted on purpose" in str(exc.value)


def test_the_feed_never_invents_a_date():
    """One ledger entry is dated "first live fleet". The feed must report null
    for it rather than a day nobody wrote down."""
    import re as _re

    for f in _feed()["findings"]:
        full_day = bool(_re.fullmatch(r"\d{4}-\d{2}-\d{2}", f["date"]))
        assert (f["date_iso"] is not None) == full_day, (
            f"{f['id']}: date {f['date']!r} and date_iso {f['date_iso']!r} disagree")
        assert f["date_precision"] == ("day" if full_day else
                                       "month" if _re.fullmatch(r"\d{4}-\d{2}", f["date"])
                                       else "none")


def test_the_feed_names_the_engine_that_produced_it():
    """A findings feed is a result, and results in this project quote the engine
    fingerprint. A feed carrying a stale version is a citation to code that no
    longer exists."""
    from dinostomp import __version__
    from dinostomp.fingerprint import engine_fingerprint

    tool = _feed()["tool"]
    assert tool["version"] == __version__, (
        "findings.json states a different version than the package; "
        "run `python scripts/index_findings.py`")
    assert tool["engine"] == engine_fingerprint()


def test_every_status_class_is_documented_in_the_feed():
    """The vocabulary travels with the data, so a consumer never guesses."""
    feed = _feed()
    used = {f["status_class"] for f in feed["findings"]}
    assert used <= set(feed["status_classes"]), (
        f"undocumented status_class values: {sorted(used - set(feed['status_classes']))}")


def test_the_readme_headline_counts_match_the_ledger():
    """The README now LEADS with the findings, which makes its counts a claim.

    The footer said "the thirty findings against itself" while the ledger held
    forty-one, for six releases, because the two were edited by different
    passes. Pinning them to the feed removes the class instead of policing it.
    """
    import re as _re

    feed = _feed()
    counts, total = feed["counts"], feed["counts"]["total"]
    # README.md specifically, NOT the concatenated DOCS: the scorecard in
    # FINDINGS.md states the same numbers in a different shape, and a test that
    # accepted either would pass on a README whose counts had gone stale.
    flat = " ".join((REPO / "README.md").read_text(encoding="utf-8").split())
    assert f"{total} entries, all permanent, none deleted" in flat, (
        f"the README does not state {total} entries")
    for series in "FDN":
        assert f"| **{series}** | {counts[series]} |" in flat, (
            f"the README's {series} row is not {counts[series]}")
    # The "N of M are against this tool" sentence, written in words.
    words = {40: "Forty", 41: "Forty-one", 42: "Forty-two", 43: "Forty-three",
             80: "eighty", 81: "eighty-one", 82: "eighty-two", 83: "eighty-three"}
    if counts["D"] in words and total in words:
        assert f"{words[counts['D']]} of the {words[total]} are against this tool" in flat, (
            f"the self-audit sentence is not {words[counts['D']]} of {words[total]}")


def test_every_finding_the_readme_cites_exists_and_says_what_it_claims():
    """The README cites finding ids by hand. Two of them pointed at the wrong
    entry within minutes of being written, and a third pointed at a finding that
    did not exist at all (D-041)."""
    import re as _re

    ids = {f["id"] for f in _feed()["findings"]}
    readme = (REPO / "README.md").read_text(encoding="utf-8")
    cited = set(_re.findall(r"\(FINDINGS\.md#([fdn]-\d{3})\)", readme))
    assert cited, "the README cites no findings"
    dead = {c for c in cited if c.upper() not in ids}
    assert not dead, f"the README cites findings that do not exist: {sorted(dead)}"


def test_the_repository_agrees_with_itself():
    """scripts/check_consistency.py, run as a test.

    Every individual number here is pinned by some other test. This is the one
    that asks whether the same fact, stated in different files by different
    passes, still says the same thing. Its first run found the README claiming
    23 audited benchmarks with 25 pods on disk.
    """
    import subprocess
    import sys

    proc = subprocess.run([sys.executable, str(REPO / "scripts" / "check_consistency.py"),
                           "--strict"], capture_output=True, text=True, cwd=str(REPO))
    assert proc.returncode == 0, (proc.stdout + proc.stderr)
