"""The zero-spec dataset audit.

House rule applies here too: every behaviour that could silently mislead has a
test that breaks it on purpose. The two that matter most are (a) inference must
REFUSE rather than guess when a dataset is ambiguous, and (b) it must never drop
a row quietly, because a shrinking denominator is the flattering direction.
"""

import json

import pytest

from dinostomp.cli import main
from dinostomp.dataset import build_items, infer_mapping, looks_like_dataset, read_rows
from dinostomp.lint import lint_dataset


def write_jsonl(tmp_path, rows, name="data.jsonl"):
    p = tmp_path / name
    p.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    return p


def write_csv(tmp_path, header, rows, name="data.csv"):
    p = tmp_path / name
    lines = [",".join(header)] + [",".join(r) for r in rows]
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return p


def finding(report, cid):
    return next(f for f in report["findings"] if f["id"] == cid)


# --- routing ------------------------------------------------------------------


@pytest.mark.parametrize("name, expected", [
    ("x.csv", True), ("x.jsonl", True), ("x.ndjson", True), ("x.json", True),
    ("eval.yaml", False), ("eval.yml", False), ("spec", False),
])
def test_routing_is_by_extension_only(name, expected):
    """Sniffing content to decide would let a malformed spec quietly become a
    cheerful verdict about the wrong thing."""
    assert looks_like_dataset(name) is expected


# --- inference: refuse rather than guess --------------------------------------


def test_ambiguous_answer_column_refuses_and_names_the_candidates():
    """TruthfulQA ships `Best Answer` AND `Correct Answers`.

    Picking one silently would put every downstream finding on a coin flip.
    """
    rows = [{"Question": "q", "Best Answer": "a", "Correct Answers": "a; b"}]
    mapping, _, issues = infer_mapping(rows)
    assert "target" not in mapping
    assert len(issues) == 1
    msg = issues[0].message
    assert "Correct Answers" in msg and "Best Answer" in msg
    assert "--target-field" in issues[0].loc


def test_an_override_settles_it():
    rows = [{"Question": "q", "Best Answer": "a", "Correct Answers": "a; b"}]
    mapping, notes, issues = infer_mapping(rows, {"target": "Correct Answers"})
    assert not issues
    assert mapping["target"] == "Correct Answers"
    assert any("you said so" in n for n in notes)


def test_an_override_naming_a_missing_column_is_an_error_not_a_fallback():
    rows = [{"question": "q", "answer": "a"}]
    _, _, issues = infer_mapping(rows, {"target": "nope"})
    assert any("not in this dataset" in i.message for i in issues)


def test_missing_required_column_names_the_near_misses():
    rows = [{"headline": "h", "verdict_text": "v"}]
    _, _, issues = infer_mapping(rows)
    assert {i.loc for i in issues} == {"--input-field", "--target-field"}
    assert all("Columns are:" in i.message for i in issues)


def test_candidate_names_are_written_in_normalised_form():
    """`correct answers` with a space matched nothing until a real header
    proved it. Column names are normalised before comparison, so the candidate
    list has to be normalised too."""
    from dinostomp.dataset import CANDIDATES, _norm

    for canon, options in CANDIDATES.items():
        for opt in options:
            assert opt == _norm(opt), f"{canon} candidate {opt!r} is not in _norm() form"


# --- building items: never drop a row quietly ---------------------------------


def test_the_string_None_is_a_legitimate_answer():
    """MMLU keys an organ-pipe question to the option "None", meaning none of
    the above. Testing str(target) against "None" deleted the item."""
    rows = [{"question": "which harmonics?", "choices": ["50 Hz", "100 Hz", "None"], "answer": 2}]
    mapping, _, issues = infer_mapping(rows)
    assert not issues
    items, notes = build_items(rows, mapping)
    assert len(items) == 1, "a row was dropped for answering 'None'"
    assert items[0]["target"] == "None"
    assert not any("dropped" in n for n in notes)


def test_a_genuinely_empty_answer_is_dropped_and_counted():
    rows = [{"question": "a", "answer": "x"}, {"question": "b", "answer": ""},
            {"question": "c", "answer": None}]
    mapping, _, _ = infer_mapping(rows)
    items, notes = build_items(rows, mapping)
    assert len(items) == 1
    assert any("2 row(s) dropped" in n for n in notes), "a silent drop is the flattering direction"


def test_an_integer_answer_key_resolves_to_the_option_text():
    """MMLU keys by index; the target has to become the text so it survives
    re-ordering, which is what the shuffle probe does to it."""
    rows = [{"question": "q", "choices": ["alpha", "beta", "gamma"], "answer": 1}]
    mapping, _, _ = infer_mapping(rows)
    items, notes = build_items(rows, mapping)
    assert items[0]["target"] == "beta"
    assert any("indexes the options" in n for n in notes)


def test_a_letter_answer_key_resolves_too():
    """ARC keys 'A'..'D' against a parallel label list."""
    rows = [{"question": "q", "choices": {"text": ["alpha", "beta"], "label": ["A", "B"]},
             "answerKey": "B"}]
    mapping, _, _ = infer_mapping(rows)
    items, _ = build_items(rows, mapping)
    assert items[0]["choices"] == ["alpha", "beta"]
    assert items[0]["target"] == "beta"


# --- the audit itself ---------------------------------------------------------


def test_a_duplicate_question_gates_with_no_spec_at_all(tmp_path):
    rows = [{"question": f"q{i}", "answer": f"a{i}"} for i in range(20)]
    rows.append({"question": "q3", "answer": "a3"})
    report, issues, ctx = lint_dataset(write_jsonl(tmp_path, rows))
    assert not issues
    assert finding(report, "S1")["level"] == "fail"
    assert report["summary"]["verdict"] == "broken"
    assert ctx["mapping"]["input"] == "question"


def test_run_checks_are_na_with_a_reason_not_silently_absent(tmp_path):
    """A dataset audit is a real audit of a smaller thing. The coverage line
    only means that if every unreached check says why."""
    rows = [{"question": f"q{i}", "answer": f"a{i}"} for i in range(20)]
    report, _, _ = lint_dataset(write_jsonl(tmp_path, rows))
    for cid in ("R1", "R8", "P2", "T1", "J1", "C1", "W1"):
        f = finding(report, cid)
        assert f["level"] == "n/a"
        assert "dataset audit" in f["detail"]
    assert report["coverage"]["declared_total"] > report["coverage"]["ran"]


def test_an_empty_dataset_never_looks_green(tmp_path):
    p = tmp_path / "empty.jsonl"
    p.write_text("", encoding="utf-8")
    report, issues, _ = lint_dataset(p)
    assert report is None
    assert any("empty" in i.message for i in issues)


def test_a_wrong_mapping_that_empties_the_dataset_refuses(tmp_path):
    rows = [{"question": f"q{i}", "answer": f"a{i}", "notes": ""} for i in range(20)]
    report, issues, _ = lint_dataset(write_jsonl(tmp_path, rows),
                                     field_overrides={"target": "notes"})
    assert report is None
    assert any("field mapping is probably wrong" in i.message for i in issues)


def test_csv_with_a_sniffed_separator(tmp_path):
    header = ["question", "answer"]
    rows = [[f"q{i}", f"a{i};b{i}"] for i in range(20)]
    report, issues, ctx = lint_dataset(write_csv(tmp_path, header, rows))
    assert not issues
    assert report["dataset"]["separator"] == ";"


def test_a_stray_separator_in_one_cell_is_punctuation_not_structure(tmp_path):
    header = ["question", "answer"]
    rows = [[f"q{i}", f"a{i}"] for i in range(20)]
    rows[0][1] = "a0; also this"
    report, _, _ = lint_dataset(write_csv(tmp_path, header, rows))
    assert report["dataset"]["separator"] is None


def test_the_cli_routes_a_data_file_to_the_dataset_audit(tmp_path, capsys):
    rows = [{"question": f"q{i}", "answer": f"a{i}"} for i in range(20)]
    rows.append({"question": "q3", "answer": "a3"})
    assert main(["stomp", str(write_jsonl(tmp_path, rows))]) == 1
    out = capsys.readouterr().out
    assert "DATASET AUDIT" in out
    assert "input    <- question" in out, "the inferred mapping must be visible to be correctable"
    assert "Scope:" in out


# --- repair: deletes, never invents -------------------------------------------


def test_emit_fixes_closes_the_loop(tmp_path, capsys):
    rows = [{"question": f"q{i}", "answer": f"a{i}"} for i in range(20)]
    rows.append({"question": "q3", "answer": "a3"})
    src = write_jsonl(tmp_path, rows)
    assert main(["stomp", str(src), "--emit-fixes"]) == 1
    fixed = src.with_name("data.fixed.jsonl")
    log = src.with_name("data.fixed.fixes.txt")
    assert fixed.is_file() and log.is_file()
    assert "S1: duplicate of an earlier item" in log.read_text(encoding="utf-8")
    capsys.readouterr()
    assert main(["stomp", str(fixed)]) == 0, "the repaired file must actually come out clean"


def test_a_repair_never_invents_an_answer(tmp_path):
    """Every rule is a deletion whose correctness a reader can check by eye."""
    from dinostomp.dataset import REPAIRS, UNREPAIRABLE

    assert not (set(REPAIRS) & set(UNREPAIRABLE)), "a check cannot be both"
    for text in REPAIRS.values():
        assert text.startswith("drop"), f"repair {text!r} does something other than delete"


def test_emit_fixes_does_not_silence_what_it_cannot_repair(tmp_path, capsys):
    """The dangerous failure: a repaired file read as a clean file.

    An answer leaking into its question cannot be fixed by deleting anything,
    so the output has to say so out loud rather than quietly leaving it in.
    """
    caps = ["France", "Japan", "Canada", "Norway", "Peru", "Egypt", "Ireland", "Greece",
            "Vietnam", "Cuba", "Poland", "Austria", "Morocco", "Jordan", "Ecuador", "Kenya",
            "Portugal", "Finland", "Sweden", "Hungary"]
    rows = [{"question": f"Which country is city {i}?", "answer": c} for i, c in enumerate(caps)]
    rows[4]["question"] += " (hint: it is Peru)"
    src = write_jsonl(tmp_path, rows)
    assert main(["stomp", str(src), "--emit-fixes"]) == 1
    out = capsys.readouterr().out
    assert "NOT repaired" in out
    assert "S2" in out
    assert "The repaired file is not a clean file" in out


def test_a_custom_fixes_path_is_honoured(tmp_path):
    rows = [{"question": f"q{i}", "answer": f"a{i}"} for i in range(20)]
    rows.append({"question": "q3", "answer": "a3"})
    src = write_jsonl(tmp_path, rows)
    dest = tmp_path / "elsewhere" / "clean.jsonl"
    dest.parent.mkdir()
    assert main(["stomp", str(src), "--emit-fixes", str(dest)]) == 1
    assert dest.is_file()


def test_repair_is_a_no_op_when_nothing_fired(tmp_path):
    """A clean dataset must come back byte-identical in content, not reshuffled."""
    from dinostomp.dataset import repair_items

    rows = [{"question": f"q{i}", "answer": f"a{i}"} for i in range(20)]
    report, _, ctx = lint_dataset(write_jsonl(tmp_path, rows))
    kept, log = repair_items(ctx["items"], report)
    assert kept == ctx["items"]
    assert log == []


# --- what a stranger's first file actually looks like -------------------------


def test_a_utf8_bom_does_not_refuse_a_valid_file(tmp_path):
    """Excel, Notepad and PowerShell's Out-File all write one by default.

    The file is valid JSONL; only a three-byte prefix differs. It was refused
    with `invalid JSON: Unexpected UTF-8 BOM (decode using utf-8-sig)`, an error
    that named its own fix without applying it (D-035).
    """
    from dinostomp.lint import lint_dataset

    rows = [{"id": f"b{i}", "input": f"What is {i}+{i}?", "target": str(2 * i)}
            for i in range(12)]
    body = "\n".join(json.dumps(r) for r in rows) + "\n"
    p = tmp_path / "bom.jsonl"
    p.write_bytes(b"\xef\xbb\xbf" + body.encode("utf-8"))

    report, issues, ctx = lint_dataset(p)
    assert report is not None, [i.message for i in issues]
    assert report["summary"]["verdict"] in ("sound", "ok", "incomplete", "broken")


def test_a_file_without_a_bom_is_unchanged(tmp_path):
    """The negative direction: utf-8-sig must be a no-op on ordinary files, and
    must not start silently stripping bytes that are not a BOM."""
    from dinostomp.lint import lint_dataset

    rows = [{"id": f"n{i}", "input": f"What is {i}+{i}?", "target": str(2 * i)}
            for i in range(12)]
    p = tmp_path / "plain.jsonl"
    p.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    with_bom = tmp_path / "same_with_bom.jsonl"
    with_bom.write_bytes(b"\xef\xbb\xbf" + p.read_bytes())

    a, _, _ = lint_dataset(p)
    b, _, _ = lint_dataset(with_bom)
    assert a is not None and b is not None
    assert a["summary"] == b["summary"], "a BOM changed the verdict"


def test_a_semicolon_csv_is_diagnosed_as_a_delimiter_problem(tmp_path):
    """Excel exports semicolon CSV in every comma-decimal locale.

    The old message said "no column looks like the input. did you mean one of:
    id;input;target?" — offering the entire header line as a column name, which
    diagnoses the wrong thing (D-036).
    """
    from dinostomp.lint import lint_dataset

    p = tmp_path / "euro.csv"
    p.write_text("id;input;target\n1;what?;yes\n2;how?;no\n", encoding="utf-8")
    report, issues, _ = lint_dataset(p)
    assert report is None
    msgs = [i.message for i in issues]
    assert any("semicolon" in m and "delimited" in m for m in msgs), msgs


def test_a_genuine_one_column_file_is_not_blamed_on_a_delimiter(tmp_path):
    """The negative test: a single column with no delimiter in its name must
    NOT get the delimiter hint, or the guard fires on every narrow file."""
    from dinostomp.lint import lint_dataset

    p = tmp_path / "one.csv"
    p.write_text("notes\nhello\nworld\n", encoding="utf-8")
    report, issues, _ = lint_dataset(p)
    assert report is None
    assert not any("delimited" in i.message for i in issues), [i.message for i in issues]


def test_a_choices_column_that_yields_no_choices_says_so(tmp_path):
    """The mapping line prints `choices <- choices`, so silence here tells a
    reader the option checks ran when every item was audited free-form (D-038).
    """
    from dinostomp.lint import lint_dataset

    p = tmp_path / "delim.jsonl"
    p.write_text("\n".join(json.dumps(
        {"id": f"c{i}", "input": f"Question {i}?", "choices": "a|b|c", "target": "a"})
        for i in range(12)) + "\n", encoding="utf-8")
    report, issues, ctx = lint_dataset(p)
    assert report is not None, [i.message for i in issues]
    notes = " ".join(ctx.get("notes") or [])
    assert "FREE-FORM" in notes and "did not run" in notes, notes
    assert 'data.separator: "|"' in notes, "the actionable fix is not named"


def test_a_real_choices_column_produces_no_such_note(tmp_path):
    """The negative direction: the note must not fire on a working choice pod."""
    from dinostomp.lint import lint_dataset

    p = tmp_path / "real.jsonl"
    p.write_text("\n".join(json.dumps(
        {"id": f"r{i}", "input": f"Question {i}?", "choices": ["a", "b", "c", "d"],
         "target": "a"}) for i in range(12)) + "\n", encoding="utf-8")
    report, issues, ctx = lint_dataset(p)
    assert report is not None
    assert "FREE-FORM" not in " ".join(ctx.get("notes") or [])
