"""Dataset loader tests: format handling, field mapping, and the loader's
own refusals (empty data, colliding ids, garbage lines)."""

import json
from pathlib import Path

from dinostomp.items import load_items


def load(tmp_path: Path, text: str, fmt: str = "jsonl", fields: dict | None = None, name: str = "d"):
    ext = "jsonl" if fmt == "jsonl" else "csv"
    path = tmp_path / f"{name}.{ext}"
    path.write_text(text, encoding="utf-8")
    cfg = {"path": path.name, "format": fmt}
    if fields:
        cfg["fields"] = fields
    return load_items(cfg, tmp_path)


def test_jsonl_happy_path(tmp_path):
    items, issues = load(tmp_path, '{"id": "a", "input": "1+1?", "target": "2"}\n')
    assert issues == []
    assert items[0]["target"] == "2"


def test_csv_with_field_mapping(tmp_path):
    text = "qid,question,gold\nx1,What is 1+1?,2\nx2,What is 2+2?,4\n"
    items, issues = load(tmp_path, text, fmt="csv",
                         fields={"id": "qid", "input": "question", "target": "gold"})
    assert issues == []
    assert [i["id"] for i in items] == ["x1", "x2"]
    assert items[1]["input"] == "What is 2+2?"


def test_empty_dataset_is_an_error(tmp_path):
    items, issues = load(tmp_path, "\n\n")
    assert items == []
    assert any("empty" in i.message for i in issues)


def test_unsupported_format_is_an_error(tmp_path):
    _, issues = load(tmp_path, "whatever", fmt="parquet")
    assert any("unsupported" in i.message for i in issues)


def test_garbage_line_reported_with_line_number(tmp_path):
    text = '{"id": "a", "input": "q?", "target": "t"}\n{not json\n'
    items, issues = load(tmp_path, text)
    assert items == []
    assert any(":2" in i.loc for i in issues)


def test_duplicate_ids_rejected(tmp_path):
    text = ('{"id": "a", "input": "q1?", "target": "t"}\n'
            '{"id": "a", "input": "q2?", "target": "t"}\n')
    items, issues = load(tmp_path, text)
    assert items == []
    assert any("duplicate" in i.message for i in issues)


def test_int_and_string_ids_collide(tmp_path):
    """Ids 1 and "1" collapse into one resume key downstream; the loader must
    refuse them rather than let an item silently never run."""
    text = ('{"id": 1, "input": "q1?", "target": "t"}\n'
            '{"id": "1", "input": "q2?", "target": "t"}\n')
    items, issues = load(tmp_path, text)
    assert items == []
    assert any("duplicate" in i.message for i in issues)


def test_canary_line_is_skipped_not_an_item(tmp_path):
    text = ('{"_canary": "dinostomp canary DO NOT TRAIN abc123"}\n'
            '{"id": "a", "input": "q?", "target": "t"}\n')
    items, issues = load(tmp_path, text)
    assert issues == []
    assert len(items) == 1, "the canary is hashed provenance, never an item"


def test_schema_violation_reported_with_location(tmp_path):
    text = '{"id": "a", "input": "q?"}\n'  # target missing
    items, issues = load(tmp_path, text)
    assert items == []
    assert any("target" in i.message for i in issues)
