"""Dataset loading: JSONL or CSV, with optional field mapping, schema-checked.

Loading is strict on purpose. A malformed line, a schema violation, or a
duplicate id is an error with a line number, not a silently dropped row.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from dinostomp.spec import Issue, jsonl_lines, read_data_text, validate_obj

CANONICAL_FIELDS = ("id", "input", "target", "choices")

# Datasets are read whole, so a hostile or accidental multi-gigabyte file would
# be an out-of-memory crash rather than an error message. Evals do not need
# anything near this; the cap exists so the failure is a sentence, not a kill.
MAX_DATA_BYTES = 100 * 1024 * 1024


# Fields that may legitimately hold several values. A CSV cell holds one
# string, so without a declared separator a multi-target item is unexpressable
# in CSV; a pod that tried loaded "46|46.0" as one literal target no model
# could ever match, and every record came back uncheckable.
SPLITTABLE_FIELDS = ("target", "choices")


def _apply_mapping(row: dict, mapping: dict, separator: str | None = None) -> dict:
    """Rename dataset columns onto canonical fields; keep the rest as metadata.

    With a `separator` declared, `target` and `choices` cells are split into
    lists, which is the only way a flat format can express an item with several
    acceptable answers or a set of options. A cell with no separator in it stays
    a plain string, so declaring one never reshapes single-valued data.
    """
    out = dict(row)
    for canon, source in (mapping or {}).items():
        if source in out and canon != source:
            out[canon] = out.pop(source)
    if separator:
        for field in SPLITTABLE_FIELDS:
            value = out.get(field)
            if isinstance(value, str) and separator in value:
                parts = [v.strip() for v in value.split(separator) if v.strip()]
                if parts:
                    out[field] = parts
    return out


def load_items(data_cfg: dict, base_dir: Path) -> tuple[list[dict], list[Issue]]:
    """Load and validate every item. Returns (items, issues); items is empty
    when any issue is fatal, because a partially loaded dataset is a lie."""
    path = base_dir / data_cfg["path"]
    mapping = data_cfg.get("fields") or {}
    fmt = data_cfg["format"]
    issues: list[Issue] = []
    rows: list[tuple[int, dict]] = []

    try:
        size = path.stat().st_size
        if size > MAX_DATA_BYTES:
            return [], [Issue(
                loc="$.data.path", check="data",
                message=f"dataset is {size / 1024 / 1024:.0f}MB, over the "
                        f"{MAX_DATA_BYTES // 1024 // 1024}MB cap; refusing to read it into memory")]
    except OSError as exc:
        return [], [Issue(loc="$.data.path", message=f"cannot stat data: {exc}", check="data")]

    try:
        if fmt == "jsonl":
            for lineno, line in enumerate(jsonl_lines(read_data_text(path)), 1):
                if not line.strip():
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError as exc:
                    issues.append(Issue(loc=f"{data_cfg['path']}:{lineno}", message=f"invalid JSON: {exc}", check="data"))
                    continue
                if isinstance(obj, dict) and obj.get("_canary"):
                    continue  # contamination canary line: hashed, never an item
                rows.append((lineno, obj))
        elif fmt == "csv":
            with path.open(encoding="utf-8", newline="") as fh:
                for lineno, row in enumerate(csv.DictReader(fh), 2):
                    rows.append((lineno, dict(row)))
        else:
            return [], [Issue(loc="$.data.format", message=f"unsupported format {fmt!r}", check="data")]
    except OSError as exc:
        return [], [Issue(loc="$.data.path", message=f"cannot read data: {exc}", check="data")]

    if not rows and not issues:
        return [], [Issue(loc="$.data.path", message="dataset is empty; an empty run must never look green", check="data")]

    items: list[dict] = []
    # Dedupe on str(id): ids 1 and "1" would collapse into one resume key
    # downstream, silently skipping an item, so they are rejected here.
    seen: dict[str, int] = {}
    for lineno, raw in rows:
        item = _apply_mapping(raw, mapping, data_cfg.get("separator"))
        for issue in validate_obj(item, "items"):
            issues.append(Issue(loc=f"{data_cfg['path']}:{lineno} {issue.loc}", message=issue.message, check="data"))
        item_id = item.get("id")
        key = str(item_id)
        if item_id is not None and key in seen:
            issues.append(
                Issue(
                    loc=f"{data_cfg['path']}:{lineno}",
                    message=f"duplicate id {item_id!r} (first seen line {seen[key]}; ids matching as strings collide)",
                    check="data",
                )
            )
        elif item_id is not None:
            seen[key] = lineno
        items.append(item)

    if issues:
        return [], issues
    return items, []
