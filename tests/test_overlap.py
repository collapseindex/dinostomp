"""Cross-dataset contamination overlap.

The claim this must never make is "not in the training data". It compares
corpora you have, on disk, and the finding text says so. The tests below pin
both halves: it fires on real reuse, and it does not fire on similarity.
"""

import json

import pytest

from dinostomp.cli import main
from dinostomp.lint import lint_dataset
from dinostomp.overlap import (find_overlap, jaccard, load_reference, normalise,
                               shingles)


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
    ref_items, errs, _ = load_reference(ref)
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


# --against had two holes, both found by pointing a real audit at a real
# reference corpus (CUDA-Agent-Ops-6K against KernelBench, 2026-08-16). The
# reference was refused for reasons that have nothing to do with overlap, and
# S11 then reported n/a with a reason that named the wrong cause.

def test_a_reference_is_read_with_the_fields_the_caller_named(tmp_path):
    """D-076: --input-field applies to the audited file only.

    A corpus whose question column is called something the inference does not
    know -- `code`, `passage`, `snippet` -- is refused before it is ever
    compared, and the audit continues without the check the user asked for.
    """
    fields = {"input": "code", "target": "ops", "id": "id"}
    rows = [{"id": f"i{i}", "code": q(i)["question"], "ops": "x"} for i in range(20)]
    src = write(tmp_path, rows, "d.jsonl")
    ref = write(tmp_path, rows[:5], "ref.jsonl")

    items, errs, _ = load_reference(ref, fields)
    assert not errs, errs
    assert len(items) == 5

    report, _, _ = lint_dataset(src, field_overrides=fields,
                                references={"ref.jsonl": items})
    f = finding(report, "S11")
    assert f["level"] == "warn", f["detail"]
    assert "5 of 20" in f["detail"]


def test_a_reference_needs_no_answer_key(tmp_path):
    """D-077: overlap never reads the target, but loading demanded one.

    `comparable()` compares the question and its options. A reference corpus
    with no answer column -- every no-gold eval, every bare prompt set -- was
    rejected for missing a field the comparison does not use.
    """
    ref = write(tmp_path, [{"id": f"i{i}", "question": q(i)["question"]} for i in range(5)],
                "ref.jsonl")
    items, errs, _ = load_reference(ref)
    assert not errs, errs
    assert len(items) == 5
    report, _, _ = lint_dataset(write(tmp_path, [q(i) for i in range(20)], "d.jsonl"),
                                references={"ref.jsonl": items})
    assert finding(report, "S11")["level"] == "warn"


def test_a_refused_reference_does_not_read_as_no_reference(tmp_path):
    """D-078: the n/a reason blamed the user for not passing what they passed."""
    ref = write(tmp_path, [{"id": "i0", "blob": "unmappable"}], "ref.jsonl")
    items, errs, _ = load_reference(ref)
    assert errs and not items
    report, _, _ = lint_dataset(write(tmp_path, [q(i) for i in range(20)], "d.jsonl"),
                                references={}, reference_errors=errs)
    f = finding(report, "S11")
    assert f["level"] == "n/a"
    assert "no reference dataset supplied" not in f["detail"]
    assert "refused" in f["detail"] or "could not" in f["detail"]


def test_the_cli_reports_a_reference_it_could_not_read(tmp_path, capsys):
    """The skip line was already honest. The report it wrote was not."""
    rows = [q(i) for i in range(20)]
    src = write(tmp_path, rows, "d.jsonl")
    ref = write(tmp_path, [{"id": "i0", "blob": "unmappable"}], "ref.jsonl")
    out_json = tmp_path / "report.json"
    main(["stomp", str(src), "--against", str(ref), "--json", str(out_json)])
    assert "[reference] skipped" in capsys.readouterr().out
    f = finding(json.loads(out_json.read_text(encoding="utf-8")), "S11")
    assert f["level"] == "n/a"
    assert "WAS supplied and was refused" in f["detail"]
    assert "no reference dataset supplied" not in f["detail"]


def test_the_cli_says_which_columns_it_read_the_reference_as(tmp_path, capsys):
    """A guess the user cannot see is a guess the user cannot correct."""
    fields = ["--input-field", "code", "--target-field", "ops"]
    rows = [{"id": f"i{i}", "code": q(i)["question"], "ops": "x"} for i in range(20)]
    src = write(tmp_path, rows, "d.jsonl")
    ref = write(tmp_path, rows[:5], "ref.jsonl")
    main(["stomp", str(src), "--against", str(ref), *fields])
    out = capsys.readouterr().out
    assert "[reference] ref.jsonl: 5 item(s), read as" in out
    assert "input<-code" in out
    assert "5 of 20" in out
