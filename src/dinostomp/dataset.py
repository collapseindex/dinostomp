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
import re
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
    # ORDER IS PREFERENCE. A name that can only mean the answer key comes before
    # one that is ambiguous, which is why every `correct_*` and `ground_truth`
    # form sits ahead of `solution`: `solution` is the answer in a maths dataset
    # and a worked derivation in an exam dataset (D-064). That finding happened
    # because `correct_option` was not on this list at all, so `solution` won
    # unopposed. The names below were read off the columns of datasets a public
    # sweep refused, not invented.
    "input": ["input", "question", "question_text", "prompt", "query", "query_text",
              "problem", "problem_statement", "instruction", "stem",
              "sentence", "premise", "ctx", "context", "text"],
    "target": ["target", "answer", "answerkey", "answer_key", "label", "gold", "gold_label",
               "ground_truth", "groundtruth", "correct", "correct_answer", "correct_answers",
               "correct_option", "correct_choice", "gold_answer", "true_answer",
               "expected_answer", "best_answer", "solution", "output", "reference"],
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

    # Options stored one per column, assembled into a list. Done AFTER the
    # name-based pass so an explicit `choices`/`options` column always wins, and
    # never against an explicit --choices-field.
    if "choices" not in mapping and "choices" not in overrides:
        family = option_family(columns)
        if family:
            mapping["choices"] = family
            notes.append(f"{'choices':8} <- {' + '.join(family)}   (assembled, one per column)")

    # Tabular audit: when the caller names a target explicitly and no column
    # looks like a question, this is a feature table (churn, fraud, a label plus
    # predictors), not a Q&A eval. Treat every other column as a feature and run
    # the leak scan (S17) rather than demanding a question that does not exist.
    if "target" in overrides and "input" not in mapping and len(columns) >= 2 \
            and not any(i.loc == "--target-field" for i in issues):
        mapping["_tabular"] = True
        notes.append("tabular audit: no question column, so every non-target "
                     "column is treated as a feature for the leak scan")
        return mapping, notes, issues

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

    # Not when the user has already said what the input is. These guards exist
    # to stop an INFERENCE going confidently wrong; re-raising them against an
    # explicit --input-field turns a warning into an unanswerable refusal, and
    # cost a real finding on the first dataset tried.
    if "input" not in overrides:
        issues.extend(_mapping_smells(rows, columns, mapping))
    return mapping, notes, issues


# Columns that carry the CONTEXT a question is asked about. Dropping one leaves
# the question stranded, and two unrelated items can then read identically.
def option_family(columns: list[str]) -> tuple[str, ...] | None:
    """Options split one per column: `choice_1..4`, `ending0..3`, `answer_a..d`.

    Returns the columns IN OPTION ORDER, or None if there is no unambiguous
    family. This is the single commonest layout the audit used to refuse: of
    twelve refused datasets that had a question and an answer column, nine
    stored their options this way, and the refusal told the author to combine
    the columns by hand. Doing it for them removes the reason for the refusal
    rather than relaxing it: with the options invisible, S1 and S7 compared
    questions stripped of the candidates that distinguish them, which is the
    false-contradiction failure D-057 recorded.

    Strict on purpose. The suffixes must form a complete run from 0, 1 or 'a',
    every column must exist, and there must be at least two. A partial or
    gappy family is exactly the case where guessing an order would silently
    mis-key every item, so it returns None and the refusal stands.
    """
    groups: dict[tuple[str, str], dict[int, str]] = {}
    for col in columns:
        m = re.fullmatch(r"(.*?)[ _-]?([0-9]|[a-jA-J])", _norm(col).strip())
        if not m:
            continue
        prefix, suffix = m.group(1).strip(" _-"), m.group(2)
        if not prefix or prefix in ("input", "id", "row"):
            continue
        kind = "digit" if suffix.isdigit() else "alpha"
        index = int(suffix) if kind == "digit" else ord(suffix.lower()) - ord("a")
        groups.setdefault((prefix, kind), {})[index] = col

    best: tuple[str, ...] | None = None
    for (_prefix, _kind), found in groups.items():
        if len(found) < 2:
            continue
        keys = sorted(found)
        # A complete run starting at 0 or at 1. Anything else is a gap, and a
        # gap means the order on offer is a guess.
        if keys != list(range(keys[0], keys[0] + len(keys))) or keys[0] not in (0, 1):
            continue
        ordered = tuple(found[k] for k in keys)
        if best is None or len(ordered) > len(best):
            best = ordered
    return best


CONTEXT_COLUMNS = ("body", "passage", "context", "premise", "paragraph", "para",
                   "article", "story", "document", "background")

# Columns that hold WORKING rather than the answer. Ambiguous by nature: these
# names are the target in a maths dataset and a derivation in an exam dataset,
# so their presence beside a real answer column is a question for the author.
EXPLANATION_COLUMNS = ("solution", "explanation", "rationale", "reasoning",
                       "derivation", "working", "steps")

# An input column whose values repeat this hard is not a question column. Set
# where it separates a type tag from a question bank: COPA's `question` column
# holds two distinct values across 500 rows (0.4%), while the thinnest genuine
# question column measured here is 99.0% distinct. Nothing observed lands
# between 0.4% and 99%, so the threshold is not finely poised.
INPUT_CARDINALITY_MIN = 0.10


def _mapping_smells(rows, columns, mapping) -> list[Issue]:
    """Refuse a mapping that is present but wrong, not merely absent.

    The refusal above catches "no column looks like the input". It does not
    catch "the wrong column is named `question`", which is a different failure
    and the more dangerous one: the audit does not go quiet, it reports
    confident findings about the wrong columns. An automated sweep of 4 public
    datasets produced 3 false findings this way before these guards existed
    (D-057), every one of them a duplicate-question or conflicting-key flag
    manufactured by the mapping rather than found in the data.
    """
    out: list[Issue] = []
    in_col = mapping.get("input")
    if not in_col or not rows:
        return out

    values = [str(r.get(in_col, "")) for r in rows]
    distinct = len(set(values))
    if len(values) >= 20 and distinct / len(values) < INPUT_CARDINALITY_MIN:
        sample = sorted({v[:24] for v in values})[:4]
        out.append(Issue(
            loc="--input-field", check="fields",
            message=f"column {in_col!r} was read as the input, but it holds only {distinct} "
                    f"distinct value(s) across {len(values)} rows "
                    f"({distinct/len(values):.1%}), e.g. {sample}. That is a category label, "
                    f"not a question, and auditing it would report every row as a duplicate. "
                    f"Pass --input-field with the column that holds the actual text."))

    # `choices` may be a TUPLE of columns when the options were assembled one
    # per column, so a flat `in mapping.values()` would leave every one of them
    # looking unmapped and re-raise the guard that assembling just answered.
    used: set[str] = set()
    for value in mapping.values():
        used.update(value if isinstance(value, tuple) else (value,))
    unmapped = [c for c in columns if c not in used]

    # Options split across one column per candidate: answer_0..answer_3,
    # choice1/choice2, option_A..option_D. Nothing assembles them, so `choices`
    # stays unmapped and every check that needs an option list goes quiet while
    # S1 and S7 compare questions stripped of the candidates that distinguish
    # them. That is how a recommendation benchmark whose items legitimately
    # repeat a prompt with different candidates got reported as contradictory.
    if "choices" not in mapping:
        numbered = [c for c in unmapped
                    if re.fullmatch(r"(answer|choice|option|ending|sol)[ _-]?[0-9a-dA-D]",
                                    _norm(c).replace(" ", ""))]
        if len(numbered) >= 2:
            out.append(Issue(
                loc="--choices-field", check="fields",
                message=f"columns {', '.join(sorted(numbered))} look like one option per column, "
                        f"and no single column holds the option list. Nothing assembles them, so "
                        f"every option-based check would be skipped and two items sharing a "
                        f"prompt but offering different candidates would be reported as "
                        f"contradictory. Combine them into one list column, or pass "
                        f"--choices-field."))

    # A STRUCTURED value read as the answer key. An extractive-QA column like
    # `answer: {"start": 108, "text": "..."}` is a span, not a choice, and
    # comparing a dict against option strings makes every item look unanswerable:
    # found flagging 100 of 100 items in a dataset that also carried a plain
    # `label` holding the real key (D-066). This is a structural fact about the
    # value, not a preference between columns, which is why it can refuse
    # without repeating D-064's mistake of choosing whatever scores best.
    tgt_struct = mapping.get("target")
    if tgt_struct and rows:
        values = [r.get(tgt_struct) for r in rows if r.get(tgt_struct) is not None]
        dicts = [v for v in values if isinstance(v, dict)]
        if values and len(dicts) / len(values) > 0.9:
            rivals = sorted(c for c in unmapped
                            if any(tok in _norm(c)
                                   for tok in ("label", "correct", "key", "gold", "target")))
            hint = (f" {', '.join(rivals)} holds a plain value and may be the key."
                    if rivals else "")
            out.append(Issue(
                loc="--target-field", check="fields",
                message=f"column {tgt_struct!r} was read as the target, but its values are "
                        f"objects rather than answers (e.g. {str(dicts[0])[:60]}). That is an "
                        f"extractive span or a structured record, and comparing it against "
                        f"option text reports every item as having no correct answer.{hint} "
                        f"Pass --target-field."))

    # An EXPLANATION column read as the answer. `solution` is genuinely the
    # target in a maths dataset and genuinely a worked derivation in an exam
    # dataset, and nothing in the name distinguishes them. Picked over
    # `correct_option` in a public exam set, it made S6 report 85 of 100 items
    # as having no correct answer (D-064).
    #
    # This refuses rather than preferring whichever column makes S6 quiet.
    # Choosing the mapping that produces the cleanest verdict is a flattering
    # selection rule: it would hide exactly the wrong-key defects S6 exists for.
    tgt = mapping.get("target")
    if tgt and _norm(tgt) in EXPLANATION_COLUMNS:
        rivals = sorted(c for c in unmapped
                        if any(tok in _norm(c)
                               for tok in ("correct", "answer", "label", "key", "gold")))
        if rivals:
            out.append(Issue(
                loc="--target-field", check="fields",
                message=f"column {tgt!r} was read as the target, but {', '.join(rivals)} "
                        f"also looks like an answer key. A column called {tgt!r} is the "
                        f"answer in a maths dataset and a worked explanation in an exam "
                        f"dataset, and auditing the explanation reports almost every item "
                        f"as having no correct answer. Pass --target-field to say which one "
                        f"holds the key."))

    context = [c for c in unmapped if _norm(c) in CONTEXT_COLUMNS]
    if context:
        out.append(Issue(
            loc="--input-field", check="fields",
            message=f"column(s) {', '.join(context)} look like the CONTEXT a question is asked "
                    f"about, and none of them is part of the input. Two different items can "
                    f"then share an identical question ('How much money did she have left?') "
                    f"and be reported as duplicates. Combine them into one column, or pass "
                    f"--input-field to say this dataset really is context-free."))
    return out


def numeric_key_base(rows: list[dict], target_col: str,
                     choices_of) -> int | None:
    """Is a numeric answer key 0-based or 1-based? Decided over the whole file.

    MMLU is 0-based and the resolver assumed everyone is. A 1-based dataset
    then mis-keys almost silently: with four options, keys 1, 2 and 3 all pass
    the bounds check and resolve to the WRONG option, and only key 4 falls out
    and raises S6. The loud symptom covers a quarter of the damage.

    Returns 0, 1, or None when the evidence does not settle it. None means the
    numeric path is skipped entirely, so the target stays as written and S6
    reports it plainly. An unresolved key is a visible problem; a key resolved
    against the wrong base is an invisible one.
    """
    seen: list[int] = []
    widths: list[int] = []
    for row in rows:
        raw = row.get(target_col)
        if isinstance(raw, list) and len(raw) == 1:
            raw = raw[0]
        if isinstance(raw, bool):
            return None
        text = str(raw).strip()
        if not text.isdigit():
            continue
        choices = choices_of(row)
        if not choices:
            continue
        seen.append(int(text))
        widths.append(len(choices))
    if not seen:
        return None
    low, high, width = min(seen), max(seen), max(widths)
    saw_zero = low == 0
    saw_width = high == width       # `4` alongside four options cannot be 0-based
    if saw_zero and saw_width:
        # Both a 0 and an index equal to the option count. No base explains
        # every row, so the file is inconsistent and neither reading is honest.
        return None
    if saw_width:
        return 1
    # DEFAULT 0, which is what MMLU does and what this resolver always assumed.
    # An earlier version returned None whenever the evidence was merely
    # insufficient, which is most small files: a single row keyed `1` over three
    # options is compatible with both bases, and refusing there stopped
    # resolving ordinary MMLU-shaped data. The residual risk is a 1-based file
    # that never keys its last option, which stays mis-read; that is strictly
    # narrower than what this replaced, and it is not silent, because the base
    # actually used is printed in the mapping notes.
    return 0


def _resolve_choice_key(row: dict, target_col: str, choices: list,
                        choice_cols: tuple[str, ...] | None = None,
                        base: int | None = 0) -> tuple[Any, bool]:
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
    # The key NAMES THE COLUMN holding the answer: `correct_answer: "answer_d"`
    # beside `answer_a..answer_d`. Read as text it matches no option, so S6
    # reports the item as unanswerable. Only consulted when the options were
    # assembled from columns, so the names are known rather than guessed.
    if choice_cols and isinstance(raw, str) and raw.strip() in choice_cols:
        value = str(row.get(raw.strip(), "")).strip()
        if value:
            return value, True
    # A SINGLE-ELEMENT LIST wrapping the key: `correct_option: [1]`. The three
    # forms below already handled a bare index and a letter label, so a public
    # exam dataset using the list form fell through unresolved and S6 reported
    # 85 of its 100 items as having no correct answer (D-064). A list with more
    # than one entry is a genuinely multi-answer item and is left alone: picking
    # one of them would invent a key the dataset does not claim.
    if isinstance(raw, list) and len(raw) == 1:
        raw = raw[0]
        if isinstance(raw, bool):
            return raw, False
    # A value that is ITSELF one of the options is that option, not a position
    # into them. A maths MCQ keyed 2 with "2" among its choices is answering with
    # the number, not indexing the third option, and reading it as an index both
    # mis-resolves the target and stamps the whole column "indexes the options"
    # in the mapping banner when it plainly holds answer text. Checking verbatim
    # membership first is what keeps a numeric-but-textual answer honest. Found by
    # Fable's first outside red-team, whose text answer column carried "96"/"7"/
    # "2"/"1945" and was reported as index-keyed while sounding certain.
    if str(raw).strip() in choices:
        return str(raw).strip(), False
    # `base` is decided over the whole file by numeric_key_base, not per row.
    # None means the file did not settle it, so the numeric path is skipped and
    # the key is left as written for S6 to report.
    if isinstance(raw, int) and base is not None and 0 <= raw - base < len(choices):
        return choices[raw - base], True
    if isinstance(raw, str):
        stripped = raw.strip()
        if (stripped.isdigit() and base is not None
                and 0 <= int(stripped) - base < len(choices)):
            return choices[int(stripped) - base], True
        # ARC: answerKey 'A'..'H' or '1'..'5' against a parallel label list
        if len(stripped) == 1 and stripped.isalpha() and stripped not in choices:
            idx = ord(stripped.upper()) - ord("A")
            if 0 <= idx < len(choices):
                return choices[idx], True
    return raw, False


def _extract_choices(value: Any) -> list[str] | None:
    """HuggingFace ships choices as a list, or as {text: [...], label: [...]}.

    A ONE-ELEMENT list is still a choice list. The threshold used to be two, on
    the reasonable-sounding grounds that a single option is not a choice, and it
    put a hole through a gating check: an option list reduced to one is exactly
    what "the keyed answer is not among the options" looks like on a binary
    item. Returning None there dropped the `choices` key, reclassified the item
    as free-form, and took S3, S4, S5 and the S6 gate quiet with it. A dataset
    that had lost the correct answer from a two-option item passed.

    Found by planting `target-not-offered` into image items, which are binary.
    Every text pool in the corpus offers four options, so removing one still
    left three and the hole never showed in 1,456 instances.

    An EMPTY list still returns None: an item with no options at all is
    genuinely not a choice item.
    """
    if isinstance(value, dict) and isinstance(value.get("text"), list):
        value = value["text"]
    if isinstance(value, list) and len(value) >= 1:
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

    def _choices_of(row: dict) -> list[str] | None:
        if isinstance(ch_col, tuple):
            return [str(row.get(c, "")).strip() for c in ch_col
                    if str(row.get(c, "")).strip()] or None
        return _extract_choices(row.get(ch_col)) if ch_col else None

    key_base = numeric_key_base(rows, tgt_col, _choices_of) if ch_col else 0
    if key_base == 1:
        notes.append("target   <- numeric key read as ONE-based "
                     "(its largest value equals the number of options)")
    elif key_base is None and ch_col:
        notes.append("target   <- numeric key NOT resolved: the file contains both a 0 "
                     "and an index equal to the option count, so no base fits every row")

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
        if isinstance(ch_col, tuple):
            # Assembled one-per-column. A blank cell is a real absent option
            # (a three-option item in a four-column layout), not padding to
            # keep, because a "" option would read as a duplicate of any other
            # blank and manufacture an S5 flag.
            assembled = [str(row.get(c, "")).strip() for c in ch_col]
            choices = [c for c in assembled if c] or None
        else:
            choices = _extract_choices(row.get(ch_col)) if ch_col else None
        if choices is None and ch_col and not isinstance(ch_col, tuple) and separator:
            raw = row.get(ch_col)
            if isinstance(raw, str) and separator in raw:
                choices = [c.strip() for c in raw.split(separator) if c.strip()]
        if choices:
            item["choices"] = choices
            target, resolved = _resolve_choice_key(
                row, tgt_col, choices,
                ch_col if isinstance(ch_col, tuple) else None, key_base)
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

    if "key" in key_styles and "text" in key_styles:
        # A MIXED column: some answers matched an option verbatim, some were read
        # as an index or label. Reporting it as cleanly index-keyed is the
        # confident-and-wrong failure the tool exists to catch, so the banner
        # says mixed and leaves the reader to look, rather than asserting a shape.
        notes.append("the answer column is MIXED: some answers hold the option text, some read "
                     "as an index or label into the options; each was resolved to the option "
                     "text, but a mixed key column is worth a look before you trust it")
    elif "key" in key_styles:
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


_LEAK_NULLS = {"", "na", "nan", "null", "none", "n/a"}


def _entropy(counts, n: int) -> float:
    import math
    return -sum((c / n) * math.log(c / n) for c in counts if c)


def _normalized_mi(feature: list, targets: list) -> float:
    """Normalized mutual information I(F;T)/H(T) in [0,1].

    Base-rate robust on purpose: a feature that DETERMINES the target scores 1.0
    whether the target is 50/50 or 92/8, where accuracy-over-base-rate cannot,
    an 8%-positive label is 'predicted' at 92% by a coin. 0 means independent.
    """
    import math
    from collections import Counter

    n = len(targets)
    tcount = Counter(targets)
    ht = _entropy(tcount.values(), n)
    if ht == 0:
        return 0.0                        # a constant target is unpredictable, not leaked
    fcount = Counter(feature)
    mi = 0.0
    for (f, t), c in Counter(zip(feature, targets)).items():
        pjt = c / n
        mi += pjt * math.log(pjt / ((fcount[f] / n) * (tcount[t] / n)))
    return max(0.0, mi / ht)


def target_is_classlike(rows: list[dict], target: str, max_classes: int = 20) -> bool:
    """A leak scan only makes sense against a class LABEL. A free-text answer
    column (one distinct value per row) is a Q&A eval, not a table to audit for
    feature leakage, and its question column would flag as a 'leak' every time."""
    vals = [str(r.get(target)) for r in rows]
    card = len(set(vals))
    return 2 <= card <= max_classes and card <= len(rows) * 0.5


def leak_candidates(rows: list[dict], target: str, *, skip=(),
                    nmi_min: float = 0.5, max_card_frac: float = 0.5) -> list[dict]:
    """Columns whose single-feature predictivity of the target is suspiciously
    high: candidate label leaks for a human to adjudicate, not verdicts.

    Two shapes, two guards:
      value leak   the column's VALUE gives the target (a refund flag == churn)
      null leak    whether the column is MISSING gives the target (a
                   days-until-cancellation that is null unless the row churned)
      id guard     a near-unique column has NMI 1.0 for a useless reason, so
                   value-grouping is skipped above a cardinality ceiling
      base guard   NMI, not accuracy, so an imbalanced label does not make every
                   column look predictive
    """
    n = len(rows)
    targets = [str(r.get(target)) for r in rows]
    out = []
    for col in (rows[0].keys() if rows else []):
        if col == target or col in skip:
            continue
        vals = [str(r.get(col)) for r in rows]
        card = len(set(vals))
        value_nmi = None
        if 2 <= card <= max(2, int(n * max_card_frac)):
            value_nmi = _normalized_mi(vals, targets)
        nulls = [str(r.get(col)).strip().lower() in _LEAK_NULLS for r in rows]
        null_nmi = _normalized_mi(nulls, targets) if 0 < sum(nulls) < n else None
        scored = [(x, k) for x, k in ((value_nmi, "value"), (null_nmi, "missingness")) if x is not None]
        if not scored:
            continue
        best, kind = max(scored)
        if best >= nmi_min:
            out.append({"column": col, "nmi": round(best, 3), "kind": kind, "cardinality": card})
    return sorted(out, key=lambda d: -d["nmi"])


def unrepairable_findings(report: dict) -> list[str]:
    """Findings a mechanical repair must not touch, with the reason.

    Printed beside the fixes so nobody reads a repaired file as a clean one.
    """
    out = []
    for f in report["findings"]:
        if f["level"] in ("fail", "warn") and f["id"] in UNREPAIRABLE:
            out.append(f"{f['id']} ({f['check']}): {UNREPAIRABLE[f['id']]}")
    return out
