"""Cross-dataset contamination overlap.

The claim this must never make is "not in the training data". It compares
corpora you have, on disk, and the finding text says so. The tests below pin
both halves: it fires on real reuse, and it does not fire on similarity.
"""

import json

import pytest

from dinostomp.cli import main
from dinostomp.lint import lint_dataset
from dinostomp.overlap import find_overlap, jaccard, normalise, shingles


def write(tmp_path, rows, name):
    p = tmp_path / name
    p.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    return p


def finding(report, cid):
    return next(f for f in report["findings"] if f["id"] == cid)


# Distinct wording per item, not one template with a counter in it: template
# siblings are excluded from near-matching on purpose, and a fixture built out
# of them would be testing the exclusion instead of the check.
STEMS = ["tidal patterns on a rocky coast", "the melting point of an alloy",
         "why migratory birds navigate at night", "how sediment layers form in a river delta",
         "the behaviour of a pendulum in a vacuum", "how yeast metabolises sugar",
         "why glaciers carve U-shaped valleys", "the colour of a sunset over the ocean",
         "how antibiotics disrupt bacterial walls", "the formation of limestone caves",
         "why metals conduct electricity well", "how a rainbow separates light",
         "the role of enzymes in digestion", "why deserts cool sharply at night",
         "how sound travels through steel", "the cause of seasonal wind reversal",
         "why ice floats on liquid water", "how magnets align in a field",
         "the growth of coral in warm water", "why leaves change colour in autumn"]


def q(i, extra=""):
    return {"question": f"Which of the following best explains {STEMS[i % len(STEMS)]}{extra}?",
            "answer": f"a{i}"}


def test_a_dataset_against_itself_is_total_overlap():
    """The one case whose answer is known by construction."""
    items = [{"id": f"i{i}", "input": q(i)["question"], "target": "x"} for i in range(30)]
    hits, stats = find_overlap(items, {"self": items})
    assert len(hits) == 30
    assert stats["exact"] == 30 and stats["near"] == 0


def test_cosmetic_differences_are_caught_as_near_matches():
    a = [{"id": "a", "input": "Which of the following best explains the observed tidal pattern?",
          "target": "x"}]
    b = [{"id": "b", "input": "which of the following BEST explains the observed tidal pattern",
          "target": "x"}]
    hits, stats = find_overlap(a, {"ref": b})
    assert len(hits) == 1
    # punctuation and casing are normalised away, so this is exact, not near
    assert hits[0]["kind"] == "exact"


def test_merely_similar_questions_do_not_count():
    """Two benchmarks both asking about photosynthesis is not a finding."""
    a = [{"id": "a", "input": "Explain how photosynthesis converts light into chemical energy "
                              "inside a plant cell.", "target": "x"}]
    b = [{"id": "b", "input": "Describe the role of chlorophyll in the absorption of sunlight "
                              "during the light-dependent reactions.", "target": "x"}]
    hits, _ = find_overlap(a, {"ref": b})
    assert hits == []


def test_two_draws_from_one_template_are_not_reuse():
    """"What is 47 + 12?" and "What is 31 + 58?" are 90%+ similar by shingles.

    Without this exclusion a 3000-item arithmetic benchmark reports itself as
    almost entirely self-contaminated, and a check that cries wolf on GSM8K is
    a check people turn off.
    """
    from dinostomp.overlap import is_template_sibling

    assert is_template_sibling("What is 47 + 12 dollars worth of apples?",
                               "What is 31 + 58 dollars worth of apples?")
    assert not is_template_sibling("What is 47 + 12 dollars worth of apples?",
                                   "What is 47 + 12 dollars worth of pears?")
    a = [{"id": "a", "input": "Jenny bought 47 apples and 12 pears at the market stall.",
          "target": "x"}]
    b = [{"id": "b", "input": "Jenny bought 31 apples and 58 pears at the market stall.",
          "target": "x"}]
    hits, stats = find_overlap(a, {"ref": b})
    assert hits == []
    assert stats["template_siblings"] == 1


def test_short_questions_never_match_on_shingles():
    """"What is 2+2?" shares most of its 4-grams with every arithmetic question."""
    assert shingles("What is 2+2?") == set()
    a = [{"id": "a", "input": "What is 2+2?", "target": "4"}]
    b = [{"id": "b", "input": "What is 3+3?", "target": "6"}]
    assert find_overlap(a, {"ref": b})[0] == []


def test_s11_is_na_without_a_reference_not_a_pass(tmp_path):
    """"No overlap found against nothing" is the pass that teaches people a
    green line means safety."""
    rows = [q(i) for i in range(20)]
    report, _, _ = lint_dataset(write(tmp_path, rows, "d.jsonl"))
    f = finding(report, "S11")
    assert f["level"] == "n/a"
    assert "never checks training data" in f["detail"]


def test_s11_fires_and_says_what_it_cannot_conclude(tmp_path):
    rows = [q(i) for i in range(20)]
    src = write(tmp_path, rows, "d.jsonl")
    ref = write(tmp_path, rows[:5], "ref.jsonl")
    from dinostomp.overlap import load_reference
    ref_items, errs = load_reference(ref)
    assert not errs
    report, _, _ = lint_dataset(src, references={"ref.jsonl": ref_items})
    f = finding(report, "S11")
    assert f["level"] == "warn"
    assert "5 of 20" in f["detail"]
    assert "not evidence about training data" in f["detail"]


def test_the_cli_accepts_repeated_against_flags(tmp_path, capsys):
    rows = [q(i) for i in range(20)]
    src = write(tmp_path, rows, "d.jsonl")
    r1 = write(tmp_path, rows[:3], "r1.jsonl")
    r2 = write(tmp_path, rows[10:12], "r2.jsonl")
    main(["stomp", str(src), "--against", str(r1), "--against", str(r2)])
    out = capsys.readouterr().out
    assert "r1.jsonl" in out and "r2.jsonl" in out
    assert "5 of 20" in out


def test_an_unreadable_reference_is_skipped_loudly_not_silently(tmp_path, capsys):
    rows = [q(i) for i in range(20)]
    src = write(tmp_path, rows, "d.jsonl")
    bad = tmp_path / "bad.jsonl"
    bad.write_text("{not json\n", encoding="utf-8")
    main(["stomp", str(src), "--against", str(bad)])
    out = capsys.readouterr().out
    assert "[reference] skipped" in out


def test_normalise_and_jaccard_are_boring_on_purpose():
    assert normalise("  Hello,   WORLD!! ") == "hello world"
    assert jaccard(set(), {"a"}) == 0.0
    assert jaccard({"a", "b"}, {"a", "b"}) == 1.0
