"""The report contract a viewer reads: `stage` on every finding, `refs` naming
the exact items behind a dataset finding, and `reproduce` carrying the command
that re-derives the report. A UI must never invent any of these, so the engine
has to emit them, and the schema has to agree with the engine."""

import csv
import json
from pathlib import Path

from dinostomp import validate_obj
from dinostomp.lint import (CHECKS, MAX_REFS, SCOPE_CHECKS, STAGE_NAMES, STAGES,
                            lint_dataset, lint_join)
from dinostomp.report import render_markdown

from tests.test_lint import choice_items

REPO = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((REPO / "src" / "dinostomp" / "schemas" / "report.schema.json")
                    .read_text(encoding="utf-8"))
FINDING_PROPS = SCHEMA["properties"]["findings"]["items"]["properties"]


def finding(report, cid):
    return next(f for f in report["findings"] if f["id"] == cid)


def write_jsonl(path: Path, items) -> Path:
    path.write_text("\n".join(json.dumps(i) for i in items) + "\n", encoding="utf-8")
    return path


# --- stage: total over the registry, and the schema is the same list -----------


def test_every_check_has_a_stage_and_the_schema_lists_the_same_stages():
    ids = {cid for cid, *_ in CHECKS}
    assert set(STAGES) == ids, (
        f"unstaged checks: {sorted(ids - set(STAGES))}; stale: {sorted(set(STAGES) - ids)}")
    assert set(STAGES.values()) <= set(STAGE_NAMES)
    assert FINDING_PROPS["stage"]["enum"] == list(STAGE_NAMES), \
        "report.schema.json and lint.STAGE_NAMES disagree; there is one list"


def test_scope_enum_matches_the_scopes_the_engine_emits():
    """The schema said `data` and `pod` while the engine emitted `table` and
    `join`, and nothing validated a report on write, so nobody was told."""
    assert set(SCHEMA["properties"]["summary"]["properties"]["scope"]["enum"]) == set(SCOPE_CHECKS)


def test_every_finding_in_a_report_carries_its_stage(tmp_path):
    report, issues, _ = lint_dataset(write_jsonl(tmp_path / "d.jsonl", choice_items()))
    assert report is not None, issues
    for f in report["findings"]:
        assert f["stage"] == STAGES[f["id"]], f["id"]
    assert validate_obj(report, "report") == []


# --- refs: the exact items, bounded --------------------------------------------


def _defective_choice_set():
    items = choice_items()
    items.append(dict(items[0], id="dup-of-c0"))                              # S1
    items[1]["choices"] = [items[1]["choices"][1]] + items[1]["choices"][1:]  # S5
    items[2]["target"] = "not-offered"                                         # S6
    # c3's own target is choices[3]; the same item keyed to choices[0] is S7
    items.append(dict(items[3], id="contra-of-c3", target=items[3]["choices"][0]))
    gold = items[4]["target"]
    items[4]["input"] = f"{gold} is the fruit for slot 4. Which is it?"        # S2
    return items


def test_gating_dataset_checks_emit_item_refs(tmp_path):
    items = _defective_choice_set()
    report, issues, _ = lint_dataset(write_jsonl(tmp_path / "d.jsonl", items))
    assert report is not None, issues
    known = {str(i["id"]) for i in items}

    expect = {"S1": ({"c0", "dup-of-c0"}, "input"),
              "S5": ({"c1"}, "choices"),
              "S6": ({"c2"}, "target"),
              "S7": ({"c3", "contra-of-c3"}, "target"),
              "S2": ({"c4"}, "input")}
    for cid, (ids, field) in expect.items():
        f = finding(report, cid)
        assert f["level"] == "fail", (cid, f["detail"])
        refs = f.get("refs") or []
        assert refs, f"{cid} fired with no refs"
        assert all(r["kind"] == "item" for r in refs), cid
        assert all(r["id"] in known for r in refs), f"{cid} names an id that is not in the dataset"
        assert ids <= {r["id"] for r in refs}, (cid, refs)
        assert all(r["field"] == field for r in refs), cid
    assert validate_obj(report, "report") == []


def test_refs_are_a_bounded_sample_and_witnesses_stay_the_count(tmp_path):
    # MAX_REFS + 10 distinct questions, each present twice: more duplicate groups
    # than refs may hold, while the question column still reads as questions
    # (four values repeated 42 times reads as a category label and is refused)
    base = choice_items(MAX_REFS + 10)
    items = base + [dict(i, id=f"dup-{i['id']}") for i in base]
    report, issues, _ = lint_dataset(write_jsonl(tmp_path / "d.jsonl", items))
    assert report is not None, issues
    s1 = finding(report, "S1")
    assert s1["level"] == "fail"
    assert len(s1["refs"]) == MAX_REFS
    assert s1["witnesses"] == len(items), "the count is the count; refs are the sample"
    assert validate_obj(report, "report") == []


def test_a_clean_dataset_emits_no_refs(tmp_path):
    report, issues, _ = lint_dataset(write_jsonl(tmp_path / "d.jsonl", choice_items()))
    assert report is not None, issues
    for cid in ("S1", "S2", "S5", "S6", "S7"):
        assert "refs" not in finding(report, cid), cid


# --- reproduce: the command the engine actually ran -----------------------------


def test_dataset_report_carries_the_command_that_made_it(tmp_path):
    path = write_jsonl(tmp_path / "quiz.jsonl", choice_items())
    report, _, _ = lint_dataset(path)
    assert report["reproduce"] == "dinostomp stomp quiz.jsonl"

    report, _, _ = lint_dataset(path, field_overrides={"target": "target"}, separator="|")
    assert report["reproduce"] == "dinostomp stomp quiz.jsonl --target-field target --separator '|'"


def test_dataset_report_names_its_reference_corpora(tmp_path):
    from dinostomp.overlap import load_reference

    path = write_jsonl(tmp_path / "quiz.jsonl", choice_items())
    ref = write_jsonl(tmp_path / "corpus.jsonl", choice_items(3))
    ref_items, errs, _ = load_reference(ref, {})
    assert ref_items and not errs, errs
    # cli.py keys references by basename; the command must name the file the same way
    report, _, _ = lint_dataset(path, references={ref.name: ref_items})
    assert report["reproduce"] == "dinostomp stomp quiz.jsonl --against corpus.jsonl"


def _two_tables(tmp_path):
    left = tmp_path / "villagers.csv"
    right = tmp_path / "songs.csv"
    with left.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["villager", "song"])
        for i in range(30):
            w.writerow([f"v{i}", f"song{i % 10}"])
    with right.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["name", "bpm"])
        for i in range(10):
            w.writerow([f"song{i}", 100 + i])
    return left, right


def test_join_report_pins_the_keys_it_used(tmp_path):
    left, right = _two_tables(tmp_path)
    report, issues, _ = lint_join(left, right, left_key="song", right_key="name")
    assert report is not None, issues
    assert report["summary"]["scope"] == "join"
    assert report["reproduce"] == (
        "dinostomp join villagers.csv songs.csv --left-key song --right-key name")
    assert validate_obj(report, "report") == [], "join reports were never validated before"


def test_table_report_validates_against_the_schema(tmp_path):
    path = tmp_path / "vendors.csv"
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["vendor", "city", "spend"])
        for i in range(40):
            w.writerow([f"vendor {i}", "Seoul" if i % 2 else "seoul", i * 10])
    report, issues, _ = lint_dataset(path)
    assert report is not None, issues
    assert report["summary"]["scope"] == "table"
    assert report["reproduce"] == "dinostomp stomp vendors.csv"
    assert validate_obj(report, "report") == [], "table reports were never validated before"


# --- parity: the markdown names what the JSON names -----------------------------


def test_markdown_prints_reproduce_and_refs(tmp_path):
    report, _, _ = lint_dataset(write_jsonl(tmp_path / "d.jsonl", _defective_choice_set()))
    md = render_markdown(report)
    assert "`dinostomp stomp d.jsonl`" in md
    assert "refs (item):" in md
    assert "`c1`" in md, "S5's item id is listed under its receipt"
