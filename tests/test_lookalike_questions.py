"""S19 lookalike-questions: a duplicate question hiding behind an encoding
variant, a smart quote, an NFC-vs-NFD accent, or a Cyrillic homoglyph, that S1's
exact dedup sails past. This is the contamination-evasion case, so it is
negative-tested on the encodings it must fold, the collisions it must NOT invent,
and its deference to S1 on exact duplicates.
"""
import json
import unicodedata
from pathlib import Path

import pytest
import yaml

from dinostomp.lint import _skeleton, lint_dataset, lint_eval


def _jsonl(tmp, rows):
    p = tmp / "data.jsonl"
    p.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    return p


def finding(rep, cid):
    return next((f for f in rep["findings"] if f["id"] == cid), None)


def s19(tmp, rows):
    rep, issues, _ = lint_dataset(_jsonl(tmp, rows))
    assert rep is not None, issues
    return finding(rep, "S19")


def _pool(n=4):
    return [{"id": f"p{i}", "question": f"How many sides does a {'triangle square pentagon hexagon'.split()[i % 4]} number {i} have?",
             "answer": str(i)} for i in range(n)]


# --- the encodings it must fold ----------------------------------------------

def test_s19_catches_a_smart_quote_duplicate(tmp_path):
    rows = _pool() + [
        {"id": "x1", "question": "What's the largest ocean on Earth?", "answer": "Pacific"},
        {"id": "x2", "question": "What’s the largest ocean on Earth?", "answer": "Pacific"}]
    f = s19(tmp_path, rows)
    assert f["level"] == "warn", f
    assert any("x1" in ex and "x2" in ex for ex in f["examples"])


def test_s19_catches_an_nfc_vs_nfd_duplicate(tmp_path):
    q = "Is the résumé spelled with accents?"
    rows = _pool() + [
        {"id": "n1", "question": unicodedata.normalize("NFC", q), "answer": "yes"},
        {"id": "n2", "question": unicodedata.normalize("NFD", q), "answer": "yes"}]
    f = s19(tmp_path, rows)
    assert f["level"] == "warn"
    assert any("n1" in ex and "n2" in ex for ex in f["examples"])


def test_s19_catches_a_cyrillic_homoglyph_duplicate(tmp_path):
    rows = _pool() + [
        {"id": "h1", "question": "What color is fresh grass in summer?", "answer": "green"},
        # 'о' in 'color' and 'с' in 'grass'... use a clean single swap: Cyrillic 'о'
        {"id": "h2", "question": "What cоlor is fresh grass in summer?", "answer": "green"}]
    f = s19(tmp_path, rows)
    assert f["level"] == "warn"
    assert any("h1" in ex and "h2" in ex for ex in f["examples"])


# --- the collisions it must NOT invent ---------------------------------------

def test_s19_clean_distinct_questions_pass(tmp_path):
    assert s19(tmp_path, _pool(6))["level"] == "pass"


def test_s19_does_not_collide_a_shared_stem_with_different_options(tmp_path):
    # The MMLU trap S1's key already guards: same stem, different options, is two
    # items. S19 mirrors that key, so it must not group them either.
    rows = [{"id": f"m{i}", "question": "Which of the following statements is correct?",
             "choices": [f"opt {i}A long enough", f"opt {i}B long enough",
                         f"opt {i}C long enough", f"opt {i}D long enough"],
             "answer": f"opt {i}A long enough"} for i in range(5)]
    assert s19(tmp_path, rows)["level"] == "pass"


def test_s19_does_not_fold_a_genuine_cyrillic_question(tmp_path):
    # A real Russian question must not collide with an unrelated Latin one just
    # because some of its letters map to Latin lookalikes.
    rows = _pool() + [
        {"id": "ru", "question": "Какая столица у Франции?", "answer": "Paris"},
        {"id": "en", "question": "What is the capital city of France today?", "answer": "Paris"}]
    f = s19(tmp_path, rows)
    assert f["level"] == "pass", f


def test_s19_short_different_questions_do_not_collide(tmp_path):
    # Below MIN_SKELETON, a handful of shared letters must not be read as a match.
    rows = [{"id": "s1", "question": "2 + 2 = ?", "answer": "4"},
            {"id": "s2", "question": "2 - 2 = ?", "answer": "0"},
            {"id": "s3", "question": "9 * 9 = ?", "answer": "81"}]
    assert s19(tmp_path, rows)["level"] == "pass"


def test_s19_defers_an_exact_duplicate_to_s1(tmp_path):
    # A byte-identical duplicate is S1's (gating) finding, not S19's; S19 must not
    # double-report it.
    rows = _pool() + [
        {"id": "e1", "question": "What is the boiling point of water in Celsius?", "answer": "100"},
        {"id": "e2", "question": "What is the boiling point of water in Celsius?", "answer": "100"}]
    assert finding(s19_rep := lint_dataset(_jsonl(tmp_path, rows))[0], "S1")["level"] == "fail"
    assert finding(s19_rep, "S19")["level"] == "pass"


# --- scope -------------------------------------------------------------------

def test_s19_ignores_asset_items_that_share_a_prompt(tmp_path):
    # A classification pod asks the same question over different images; those are
    # distinct items keyed by their asset, not encoding duplicates. S19 must skip
    # them (S1 and S15 own the asset side). This is the trials false alarm, unit
    # tested so it cannot come back.
    rows = [{"id": f"img{i}", "input": "What shape is in this image?",
             "input_ref": {"uri": f"shapes/{i}.png", "kind": "image",
                           "sha256": f"{i:064x}"}, "target": ["circle", "square", "triangle"][i % 3]}
            for i in range(6)]
    f = s19(tmp_path, rows)
    assert f["level"] in ("pass", "n/a"), f


def test_s19_na_on_a_single_item(tmp_path):
    assert s19(tmp_path, [{"id": "only", "question": "the one and only question here?", "answer": "yes"}])["level"] == "n/a"


def test_s19_runs_in_a_pod(tmp_path):
    q1 = "What's the tallest mountain above sea level anywhere?"
    q2 = "What’s the tallest mountain above sea level anywhere?"  # curly quote
    (tmp_path / "items.jsonl").write_text(
        '{"_canary": "dinostomp canary DO NOT TRAIN test"}\n'
        + json.dumps({"id": "q1", "input": q1, "target": "Everest"}) + "\n"
        + json.dumps({"id": "q2", "input": q2, "target": "Everest"}) + "\n"
        + json.dumps({"id": "q3", "input": "Name a river longer than a thousand miles please.", "target": "Nile"}) + "\n",
        encoding="utf-8")
    spec = {"name": "p", "version": "0.1.0", "question": "Does the model name world geography facts?",
            "data": {"path": "items.jsonl", "format": "jsonl"},
            "models": [{"provider": "dry", "model": "dry-strong"}],
            "scorer": {"kind": "exact", "witnesses": [
                {"output": "Everest", "target": "Everest", "expect": "pass"},
                {"output": "K2", "target": "Everest", "expect": "fail"}]},
            "run": {"n": 3, "seed": 7, "budget_usd": 0}}
    p = tmp_path / "eval.yaml"
    p.write_text(yaml.safe_dump(spec), encoding="utf-8")
    rep, issues = lint_eval(p)
    assert rep is not None, issues
    assert finding(rep, "S19")["level"] == "warn"


def test_skeleton_folds_the_three_families():
    assert _skeleton("What's") == _skeleton("What’s")               # smart quote
    assert _skeleton(unicodedata.normalize("NFD", "café")) == _skeleton("café")  # NFC/NFD
    assert _skeleton("color") == _skeleton("cоlor")                 # Cyrillic o
    assert _skeleton("cat") != _skeleton("dog")                          # not everything collapses
