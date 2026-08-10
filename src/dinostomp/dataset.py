"""Audit a bare dataset, with no spec, no pod, and no run.

The pod workflow is the destination. It is a bad front door. Every finding this
project has made in someone else's data (MMLU's double-keyed subtraction item,
its 90 duplicate rows, TruthfulQA's self-answering question) came from checks
that read the items at rest and needed nothing else: no scorer, no model, no
money, no YAML. Making people write a spec first to reach them is a tax on the
one thing the tool is demonstrably good at.

    dinostomp stomp mmlu.csv

So this module infers the smallest thing the item checks need (which column is
the question, which is the answer, which are the options) and says out loud what
it inferred, because a guess presented as a fact is the failure mode this whole
repo exists to catch. When the guess is ambiguous it refuses and names the
candidates rather than picking one.

What it deliberately does NOT do is pretend to be a pod audit. Everything that
needs a scorer, a run, or a claim comes back `n/a` with that reason, so the
coverage line stays honest: a dataset audit is a real audit of a smaller thing.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from dinostomp.spec import Issue, jsonl_lines, read_data_text

DATA_SUFFIXES = {".csv": "csv", ".jsonl": "jsonl", ".ndjson": "jsonl", ".json": "json"}

# Column names that mean the same canonical field, most specific first. Order
# matters: a row with both `question` and `text` wants `question`.
# Entries are compared against _norm()'d column names, so they must be written
# in _norm() form: lowercase, underscores. "correct answers" silently matched
# nothing until TruthfulQA's real header proved it.
CANDIDATES = {
    "id": ["id", "_id", "uid", "qid", "question_id", "item_id", "idx", "index", "ind"],
    "input": ["input", "question", "prompt", "query", "problem", "instruction", "stem",
              "sentence", "premise", "ctx", "context", "text"],
    "target": ["target", "answer", "answerkey", "answer_key", "label", "gold", "gold_label",
               "correct", "correct_answer", "correct_answers", "best_answer", "solution",
               "output", "reference"],
    "choices": ["choices", "options", "endings", "candidates", "alternatives", "answers"],
}

# A cell holding several values needs a separator to be expressable in CSV.
COMMON_SEPARATORS = ["|", ";", "\t"]

MAX_SNIFF_ROWS = 200
MAX_DATA_BYTES = 100 * 1024 * 1024


def looks_like_dataset(path: str | Path) -> bool:
    """Is this a data file rather than a spec? Extension only, deliberately.

    Sniffing content to decide would mean a malformed spec silently becomes a
    dataset audit and reports a cheerful verdict about the wrong thing.
    """
    return Path(path).suffix.lower() in DATA_SUFFIXES


def _norm(name: str) -> str:
    return str(name).strip().lower().replace("-", "_").replace(" ", "_")


def read_rows(path: Path) -> tuple[list[dict], list[Issue]]:
    """Load raw rows from csv / jsonl / json. No mapping, no validation yet."""
    try:
        size = path.stat().st_size
    except OSError as exc:
        return [], [Issue(loc=str(path), message=f"cannot stat file: {exc}", check="data")]
    if size > MAX_DATA_BYTES:
        return [], [Issue(loc=str(path), check="data",
                          message=f"dataset is {size / 1024 / 1024:.0f}MB, over the "
                                  f"{MAX_DATA_BYTES // 1024 // 1024}MB cap")]
    fmt = DATA_SUFFIXES[path.suffix.lower()]
    try:
        if fmt == "csv":
            with path.open(encoding="utf-8", newline="") as fh:
                return [dict(r) for r in csv.DictReader(fh)], []
        text = read_data_text(path)
    except OSError as exc:
        return [], [Issue(loc=str(path), message=f"cannot read file: {exc}", check="data")]
    except UnicodeDecodeError as exc:
        return [], [Issue(loc=str(path), message=f"not utf-8 text: {exc}", check="data")]

    rows: list[dict] = []
    if fmt == "jsonl":
        for lineno, line in enumerate(jsonl_lines(text), 1):
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                return [], [Issue(loc=f"{path}:{lineno}", message=f"invalid JSON: {exc}",
                                  check="data")]
            if isinstance(obj, dict) and obj.get("_canary"):
                continue
            if isinstance(obj, dict):
                rows.append(obj)
    else:
        try:
            obj = json.loads(text)
        except json.JSONDecodeError as exc:
            return [], [Issue(loc=str(path), message=f"invalid JSON: {exc}", check="data")]
        # A bare list, or the one-key-holds-the-list shape every export uses.
        if isinstance(obj, dict):
            lists = [v for v in obj.values() if isinstance(v, list)]
            if len(lists) != 1:
                return [], [Issue(loc=str(path), check="data",
                                  message="expected a JSON list of items, or an object with exactly "
                                          f"one list in it; found {len(lists)} lists")]
            obj = lists[0]
        if not isinstance(obj, list):
            return [], [Issue(loc=str(path), message="expected a JSON list of items", check="data")]
        rows = [r for r in obj if isinstance(r, dict)]
    return rows, []


def infer_mapping(rows: list[dict], overrides: dict | None = None
                  ) -> tuple[dict[str, str], list[str], list[Issue]]:
    """Guess which columns are id / input / target / choices.

    Returns (mapping, notes, issues). `notes` is printed verbatim, because the
    user has to be able to see the guess to disagree with it. An ambiguous or
    missing REQUIRED field is an Issue, never a silent pick: this tool's whole
    argument is that a confident wrong answer is worse than a refusal.
    """
    overrides = {k: v for k, v in (overrides or {}).items() if v}
    columns = list(rows[0].keys()) if rows else []
    by_norm = {_norm(c): c for c in columns}
    mapping: dict[str, str] = {}
    notes: list[str] = []
    issues: list[Issue] = []

    for canon, options in CANDIDATES.items():
        if canon in overrides:
            chosen = overrides[canon]
            if chosen not in columns:
                issues.append(Issue(loc=f"--{canon}-field", check="fields",
                                    message=f"column {chosen!r} is not in this dataset; "
                                            f"columns are {', '.join(columns)}"))
                continue
            mapping[canon] = chosen
            notes.append(f"{canon:8} <- {chosen}   (you said so)")
            continue
        hits = [by_norm[o] for o in options if o in by_norm]
        if not hits:
            continue
        if len(hits) > 1 and _norm(hits[0]) not in (options[0], options[1]):
            # Several equally plausible columns and no clear winner near the
            # front of the preference list: say so instead of coin-flipping.
            issues.append(Issue(loc=f"--{canon}-field", check="fields",
                                message=f"cannot tell which column is the {canon}: "
                                        f"{', '.join(hits)}. Pass --{canon}-field to choose."))
            continue
        if canon == "target" and _norm(hits[0]) in ("answer", "answers") and "choices" in mapping:
            pass  # a choice pod's answer column is normal; nothing to warn about
        mapping[canon] = hits[0]
        extra = f"   (also saw {', '.join(hits[1:])})" if len(hits) > 1 else ""
        notes.append(f"{canon:8} <- {hits[0]}{extra}")

    for required in ("input", "target"):
        if required not in mapping and not any(i.loc == f"--{required}-field" for i in issues):
            # Name the plausible columns first. Dumping an eight-column header
            # and saying "pick one" is a refusal that does not help.
            near = [c for c in columns
                    if any(tok in _norm(c) for tok in ("answer", "label", "gold", "target",
                                                       "solution", "correct"))]                 if required == "target" else                 [c for c in columns if any(tok in _norm(c) for tok in ("question", "prompt",
                                                                       "input", "text", "query"))]
            hint = (f"did you mean one of: {', '.join(near)}? " if near else "")
            # A ONE-COLUMN header containing a common delimiter is not a naming
            # problem, it is a parsing problem, and "no column looks like the
            # input. did you mean one of: id;input;target?" diagnoses the wrong
            # thing entirely. Semicolon CSV is the default Excel export in every
            # locale that uses a comma decimal separator, so this is somebody's
            # ordinary file rather than an exotic one (D-036).
            if len(columns) == 1 and not any(i.loc == "--separator" for i in issues):
                for delim, label in ((";", "semicolon"), ("\t", "tab"), ("|", "pipe")):
                    if delim in columns[0]:
                        issues.append(Issue(
                            loc="--separator", check="fields",
                            message=f"this file has ONE column, whose name contains "
                                    f"{label}s: {columns[0]!r}. It is most likely "
                                    f"{label}-delimited rather than comma-delimited, so no "
                                    f"field was split out at all. Re-export it comma-separated, "
                                    f"or declare `data.separator` in a spec"))
                        break
            issues.append(Issue(
                loc=f"--{required}-field", check="fields",
                message=f"no column looks like the {required}. {hint}"
                        f"Columns are: {', '.join(columns) or '(none)'}. "
                        f"Pass --{required}-field."))
    return mapping, notes, issues


def _resolve_choice_key(row: dict, target_col: str, choices: list) -> tuple[Any, bool]:
    """MMLU keys its answer as an INDEX, ARC as a LABEL, others as the text.

    All three have to become the option's text, because that is what the item
    schema means by a target and what every downstream check compares against.

    Returns (target, resolved). `resolved` says whether an index or a label was
    translated, and it has to be reported that way rather than inferred from
    the RESULT: a resolved target is by construction one of the choices, so
    "is the target in the choices" answers a different question and always
    said no translation happened.
    """
    raw = row.get(target_col)
    if isinstance(raw, bool):
        return raw, False
    if isinstance(raw, int) and 0 <= raw < len(choices):
        return choices[raw], True
    if isinstance(raw, str):
        stripped = raw.strip()
        if stripped.isdigit() and 0 <= int(stripped) < len(choices):
            return choices[int(stripped)], True
        # ARC: answerKey 'A'..'H' or '1'..'5' against a parallel label list
        if len(stripped) == 1 and stripped.isalpha() and stripped not in choices:
            idx = ord(stripped.upper()) - ord("A")
            if 0 <= idx < len(choices):
                return choices[idx], True
    return raw, False


def _extract_choices(value: Any) -> list[str] | None:
    """HuggingFace ships choices as a list, or as {text: [...], label: [...]}."""
    if isinstance(value, dict) and isinstance(value.get("text"), list):
        value = value["text"]
    if isinstance(value, list) and len(value) >= 2:
        return [str(v).strip() for v in value]
    return None


def build_items(rows: list[dict], mapping: dict[str, str], separator: str | None = None
                ) -> tuple[list[dict], list[str]]:
    """Canonical items from raw rows. Returns (items, notes)."""
    notes: list[str] = []
    id_col = mapping.get("id")
    in_col, tgt_col = mapping["input"], mapping["target"]
    ch_col = mapping.get("choices")
    items = []
    key_styles: set[str] = set()

    for i, row in enumerate(rows):
        item: dict[str, Any] = {"id": str(row[id_col]) if id_col and row.get(id_col) is not None
                                else f"row-{i:06d}"}
        item["input"] = str(row.get(in_col, "")).strip()
        # Carry an asset reference through UNTOUCHED. This function builds a
        # fresh dict rather than copying the row, so anything not named here is
        # silently gone, and `input_ref` going missing is not a cosmetic loss:
        # every image behind a shared prompt ("Which shape is in this image?")
        # then keys identically, and S1 and S7 report a whole dataset as
        # duplicated and self-contradictory. Found by running the first image
        # pod through `stomp`, which reported exactly that on ten distinct
        # pictures.
        ref = row.get("input_ref")
        if isinstance(ref, dict) and ref.get("uri"):
            item["input_ref"] = ref
        choices = _extract_choices(row.get(ch_col)) if ch_col else None
        if choices is None and ch_col and separator:
            raw = row.get(ch_col)
            if isinstance(raw, str) and separator in raw:
                choices = [c.strip() for c in raw.split(separator) if c.strip()]
        if choices:
            item["choices"] = choices
            target, resolved = _resolve_choice_key(row, tgt_col, choices)
            key_styles.add("key" if resolved else "text")
        else:
            target = row.get(tgt_col)
            if isinstance(target, list):
                target = [str(t) for t in target]
            elif isinstance(target, str) and separator and separator in target:
                target = [t.strip() for t in target.split(separator) if t.strip()]
        # Test the RAW value for absence, never its string form. MMLU keys one
        # organ-pipe question to the option "None", meaning none of the above,
        # and comparing str(target) against "None" silently deleted a perfectly
        # good item. Dropping data quietly is the flattering direction: fewer
        # items is fewer chances for a check to find anything.
        missing = target is None or (isinstance(target, str) and not target.strip())             or (isinstance(target, list) and not target)
        item["target"] = target if isinstance(target, list) else str(target).strip()
        # An item with an asset needs no inline prompt: a classification pod's
        # item IS the image. Requiring `input` here would drop every one of them
        # and report a clean audit over an empty dataset.
        if (not item["input"] and "input_ref" not in item) or missing:
            continue
        items.append(item)

    if "key" in key_styles:
        notes.append("the answer column indexes the options (a number or a letter) rather than "
                     "holding their text; resolved to the option text so the target survives "
                     "re-ordering")

    # A choices column that produced NO choices. The mapping line above already
    # printed `choices <- <column>`, so staying quiet here tells a reader the
    # option checks ran when they silently went n/a and every item was audited
    # as free-form (D-038). Naming the reason matters because the usual cause is
    # a delimited string from a CSV export, which `data.separator` exists to
    # split.
    if ch_col and not any("choices" in i for i in items):
        sample = next((row.get(ch_col) for row in rows if row.get(ch_col)), None)
        hint = ""
        if isinstance(sample, str):
            found = next((d for d in ("|", ";", ",", "/") if d in sample), None)
            hint = (f" The values look delimited ({sample[:40]!r}); declare "
                    f"`data.separator: \"{found}\"` in a spec to split them into options."
                    if found else
                    f" The values are plain strings ({sample[:40]!r}), not lists of options.")
        notes.append(f"the {ch_col!r} column was mapped to `choices` but yielded none, so every "
                     f"item was audited as FREE-FORM and the option checks did not run."
                     + hint)

    dropped = len(rows) - len(items)
    if dropped:
        notes.append(f"{dropped} row(s) dropped for an empty question or answer")
    return items, notes


def sniff_separator(rows: list[dict], mapping: dict[str, str]) -> str | None:
    """Which separator, if any, a flat target column is using.

    Only claimed when it appears in a clear majority of cells, because a stray
    semicolon in one answer is punctuation, not structure.
    """
    col = mapping.get("target")
    if not col:
        return None
    cells = [r.get(col) for r in rows[:MAX_SNIFF_ROWS]]
    cells = [c for c in cells if isinstance(c, str) and c.strip()]
    if len(cells) < 10:
        return None
    for sep in COMMON_SEPARATORS:
        if sum(1 for c in cells if sep in c) >= 0.6 * len(cells):
            return sep
    return None


# --- repair -------------------------------------------------------------------

# What a repair may and may not do, stated once. A tool that hands back a fixed
# file is run twice; a tool that hands back a verdict is run once. But a repair
# that GUESSES is worse than no repair, so every rule here is a deletion or a
# deduplication whose correctness a reader can check by eye. Nothing invents an
# answer, rewrites a question, or picks between conflicting keys.
REPAIRS = {
    "S1": "drop later copies of a duplicated item (question plus options)",
    "S5": "drop items that offer the same option twice",
    "S6": "drop items whose keyed answer is not among their options",
}

UNREPAIRABLE = {
    "S2": "an answer leaking into its question needs the question rewritten, which is authoring",
    "S7": "conflicting keys for one question need a human to say which is right",
    "S3": "position skew is fixed by re-keying the dataset, not by deleting items",
    "S4": "length skew is fixed by rewriting distractors, not by deleting items",
    "S9": "a surface shortcut is a property of how the options were written",
}


def repair_items(items: list[dict], report: dict) -> tuple[list[dict], list[str]]:
    """Apply only the mechanical repairs. Returns (kept, log).

    Deliberately conservative: it deletes, it never edits. Every dropped item is
    logged with the check that condemned it, so the diff is auditable line by
    line rather than trusted wholesale.
    """
    from dinostomp.lint import _item_key

    fired = {f["id"] for f in report["findings"] if f["level"] in ("fail", "warn")}
    log: list[str] = []
    kept: list[dict] = []
    seen: set[str] = set()

    for item in items:
        reason = None
        if "S5" in fired and "choices" in item and len(set(item["choices"])) < len(item["choices"]):
            reason = "S5: offers the same option twice"
        elif "S6" in fired and "choices" in item:
            targets = item["target"] if isinstance(item["target"], list) else [item["target"]]
            if not any(str(t) in item["choices"] for t in targets):
                reason = "S6: keyed answer is not among its options"
        elif "S1" in fired:
            key = _item_key(item)
            if key in seen:
                reason = "S1: duplicate of an earlier item"
            else:
                seen.add(key)
        if reason:
            log.append(f"{item['id']}: dropped, {reason}")
        else:
            kept.append(item)
    return kept, log


def unrepairable_findings(report: dict) -> list[str]:
    """Findings a mechanical repair must not touch, with the reason.

    Printed beside the fixes so nobody reads a repaired file as a clean one.
    """
    out = []
    for f in report["findings"]:
        if f["level"] in ("fail", "warn") and f["id"] in UNREPAIRABLE:
            out.append(f"{f['id']} ({f['check']}): {UNREPAIRABLE[f['id']]}")
    return out
