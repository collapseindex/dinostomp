"""Turn another harness's output into evidence this battery can read.

This exists to prove a claim the architecture makes: the battery consumes the
record and manifest SCHEMAS, not "whatever `dinostomp run` wrote". If that is
true, anything that can produce conforming records is auditable, and this module
is the reference demonstration.

It is deliberately unprivileged. An imported run gets no shortcuts:

  - its records are validated against `record.schema.json` like any other
  - its manifest carries `imported: true` and the source path, so a reader is
    never misled about where a number came from
  - `spec_sha256` and `data_sha256` are computed from YOUR pod, so the drift
    boundary applies to imported evidence exactly as it does to native evidence
  - it cannot claim `tool_sha256`, because this engine did not produce it, and
    R19 says so rather than pretending otherwise
  - checks whose evidence fields the import lacks SKIP, naming the field

What it does not do, and will not: invent fields. If the source log has no
`finish_reason`, the import has no `finish_reason`, R5 skips, and the coverage
line is one check shorter. Fabricating a plausible value would make the report
say something nobody measured, which is the failure this whole tool is pointed
at.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from dinostomp.spec import Issue, validate_obj

# Column names an importer will meet in the wild, mapped onto the record schema.
# Same discipline as the dataset audit: guess, SHOW the guess, refuse when
# genuinely ambiguous.
RECORD_CANDIDATES = {
    "item_id": ["item_id", "id", "doc_id", "sample_id", "example_id", "index", "idx"],
    "output": ["output", "completion", "response", "prediction", "generated", "text", "answer"],
    "score": ["score", "verdict", "correct", "is_correct", "passed", "result", "acc"],
    "model": ["model", "model_name", "model_id"],
}

TRUTHY = {"1", "true", "yes", "pass", "passed", "correct", "y", "t"}
FALSY = {"0", "false", "no", "fail", "failed", "incorrect", "n", "f"}


def _norm(name: str) -> str:
    return str(name).strip().lower().replace("-", "_").replace(" ", "_")


def _as_verdict(value: Any) -> str | None:
    """Map a foreign score onto pass / fail / uncheckable.

    Returns None when the value is not interpretable, and the caller refuses the
    import rather than defaulting. Defaulting an uninterpretable score to `fail`
    would silently invent a number; defaulting to `pass` would invent a
    flattering one.
    """
    if isinstance(value, bool):
        return "pass" if value else "fail"
    if isinstance(value, (int, float)):
        if value in (0, 1):
            return "pass" if value == 1 else "fail"
        return None
    if isinstance(value, str):
        v = value.strip().lower()
        if v in ("pass", "fail", "uncheckable", "flag"):
            return v
        if v in TRUTHY:
            return "pass"
        if v in FALSY:
            return "fail"
    return None


def infer_record_mapping(rows: list[dict], overrides: dict | None = None
                         ) -> tuple[dict[str, str], list[str], list[Issue]]:
    """Which foreign columns are item_id / output / score / model."""
    overrides = {k: v for k, v in (overrides or {}).items() if v}
    columns = list(rows[0].keys()) if rows else []
    by_norm = {_norm(c): c for c in columns}
    mapping: dict[str, str] = {}
    notes: list[str] = []
    issues: list[Issue] = []

    for canon, options in RECORD_CANDIDATES.items():
        if canon in overrides:
            if overrides[canon] not in columns:
                issues.append(Issue(loc=f"--{canon.replace(chr(95), chr(45))}-field", check="import",
                                    message=f"column {overrides[canon]!r} is not in this log; "
                                            f"columns are {', '.join(columns)}"))
                continue
            mapping[canon] = overrides[canon]
            notes.append(f"{canon:8} <- {overrides[canon]}   (you said so)")
            continue
        hits = [by_norm[o] for o in options if o in by_norm]
        if not hits:
            continue
        if len(hits) > 1 and _norm(hits[0]) != options[0]:
            issues.append(Issue(loc=f"--{canon.replace(chr(95), chr(45))}-field", check="import",
                                message=f"cannot tell which column is the {canon}: "
                                        f"{', '.join(hits)}. Pass --{canon.replace(chr(95), chr(45))}-field."))
            continue
        mapping[canon] = hits[0]
        notes.append(f"{canon:8} <- {hits[0]}")

    # `output` is deliberately NOT here. A loglikelihood-ranking log has no generated
    # text to map, and demanding one would make the most common eval-log shape in the
    # field unimportable. Absent output means R8/R14/R16 skip naming the field.
    for required in ("item_id", "score"):
        if required not in mapping and not any(i.loc == f"--{required}-field" for i in issues):
            issues.append(Issue(
                loc=f"--{required.replace(chr(95), chr(45))}-field", check="import",
                message=f"no column looks like the {required}. Columns are: "
                        f"{', '.join(columns) or '(none)'}. Pass --{required.replace(chr(95), chr(45))}-field."))

    # A RIVAL SCORE COLUMN THAT DISAGREES.
    #
    # Real harnesses ship more than one verdict per row. An lm-evaluation-harness
    # details file carries both `acc` and `acc_norm`, and only `acc` is in the
    # candidate list above, so the mapping silently took it. On the ARC log this
    # repo audits they disagree on 221 of 1172 items, 17.6% against 19.7%, and the
    # Open LLM Leaderboard published the OTHER one. Picking quietly would have made
    # this tool import a headline number nobody reported, which is the failure it
    # exists to object to.
    #
    # The rule needs no list of known column names: any unmapped column whose every
    # value reads as a verdict is a rival, and it is only raised when it actually
    # DISAGREES, so a log carrying a duplicate of the same verdict imports clean.
    chosen = mapping.get("score")
    if chosen and "score" not in overrides:
        for col in columns:
            if col == chosen or col in mapping.values():
                continue
            verdicts = [_as_verdict(r.get(col)) for r in rows]
            if any(v is None for v in verdicts):
                continue
            # A CONSTANT column is not a rival verdict, it is a flag. The first
            # version of this rule fired on `truncated`, which is 0 on all 1172
            # rows and therefore "disagrees" with the score on exactly the rows
            # that passed. That is an artifact of comparing a verdict to a
            # constant, not evidence of two competing numbers.
            if len(set(verdicts)) < 2:
                continue
            differs = sum(1 for r, v in zip(rows, verdicts)
                          if v != _as_verdict(r.get(chosen)))
            if differs:
                issues.append(Issue(
                    loc="--score-field", check="import",
                    message=f"{chosen!r} and {col!r} both read as per-item verdicts and they "
                            f"disagree on {differs} of {len(rows)} row(s). This tool will not "
                            f"choose which number you meant: pass --score-field {chosen} or "
                            f"--score-field {col}"))
    return mapping, notes, issues


def to_records(rows: list[dict], mapping: dict[str, str], *, model: str, seed: int,
               provider: str = "imported") -> tuple[list[dict], list[Issue]]:
    """Foreign rows to schema-conforming records. Validated, never coerced.

    Every produced record is checked against `record.schema.json` here rather
    than at audit time, so an import either yields evidence the battery can read
    or fails loudly at the boundary. A half-imported run is a lie about
    coverage.
    """
    out: list[dict] = []
    issues: list[Issue] = []
    for n, row in enumerate(rows):
        verdict = _as_verdict(row.get(mapping["score"]))
        if verdict is None:
            issues.append(Issue(
                loc=f"row {n}", check="import",
                message=f"cannot read {row.get(mapping['score'])!r} as a verdict. Expected a "
                        "boolean, 0/1, or one of pass/fail/uncheckable. Nothing is assumed here: "
                        "guessing would invent a number nobody measured"))
            continue
        item_id = str(row.get(mapping["item_id"]))
        rec = {
            "key": f"{item_id}#r0",
            "item_id": item_id,
            "model": str(row.get(mapping["model"])) if mapping.get("model") else model,
            "provider": provider,
            "seed": seed,
            "score": {"verdict": verdict, "evidence": "imported verdict, not re-derived here"},
            "ts": "1970-01-01T00:00:00+00:00",
        }
        # OMITTED, not defaulted. A loglikelihood log has no generated text, and
        # writing "" would claim the model answered with nothing rather than that
        # it never emitted text at all. The first is a result, the second is an
        # absence, and R8/R14/R16 are entitled to tell them apart.
        if mapping.get("output"):
            rec["output"] = str(row.get(mapping["output"], ""))
        problems = validate_obj(rec, "record")
        if problems:
            issues.append(Issue(loc=f"row {n}", check="import",
                                message=f"produced a schema-invalid record: {problems[0].message}"))
            continue
        out.append(rec)
    return out, issues


def build_manifest(spec: dict, hashes: dict, *, model: str, seed: int, source: Path,
                   n_records: int, run_file: str, witness_report: dict,
                   provider: str = "imported") -> dict:
    """A manifest for imported evidence, honest about what it is.

    Note what is absent: `tool_sha256`. This engine did not produce these
    numbers and must not stamp them as though it had. R19 reads that absence
    and reports it, which is the correct outcome: you are auditing evidence
    whose producer you cannot verify from here.
    """
    return {
        "tool_version": "imported",
        "spec_name": spec["name"],
        "spec_version": spec["version"],
        **hashes,
        "provider": provider,
        "model": model,
        "seed": seed,
        "n_items": n_records,
        "dry_run": False,
        "budget_cap_usd": 0.0,
        "imported": True,
        "imported_from": str(source),
        # The witness gate RUNS at import time, against this pod's scorer,
        # because that scorer is what re-derives these verdicts offline. A
        # manifest declaring `absent` would make every import a gated finding,
        # and weakening the drift check to excuse imports would be worse: the
        # honest fix is to actually pass the gate rather than to be forgiven
        # for skipping it.
        "witness_report": witness_report,
        "started_at": "1970-01-01T00:00:00+00:00",
        "finished_at": "1970-01-01T00:00:00+00:00",
        "run_file": run_file,
        "status": "complete",
    }


def read_log(path: Path) -> tuple[list[dict], list[Issue]]:
    """Read a foreign log. Reuses the dataset reader: same formats, same caps."""
    from dinostomp.dataset import read_rows

    return read_rows(path)


def write_run(pod_dir: Path, records: list[dict], manifest: dict, stem: str
              ) -> tuple[Path, Path, Path]:
    """Write the ledger, the manifest, AND the summary.

    The summary is not optional. `summary-rederive` (R9) recomputes every
    summary from its records and gates when one is missing, so an importer that
    skips it produces evidence that is broken on arrival, which would teach
    people that imports are always broken.
    """
    from dinostomp.runner import summarize

    runs = pod_dir / "data" / "runs"
    runs.mkdir(parents=True, exist_ok=True)
    rf = runs / f"{stem}.jsonl"
    rf.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8", newline="\n")
    mf = runs / f"{stem}_manifest.json"
    mf.write_text(json.dumps(manifest, indent=2), encoding="utf-8", newline="\n")

    results = pod_dir / "data" / "results"
    results.mkdir(parents=True, exist_ok=True)
    sf = results / f"{stem}_summary.json"
    summary = {"spec_name": manifest["spec_name"], "model": manifest["model"],
               "seed": manifest["seed"], "status": manifest["status"],
               "imported": True, **summarize(records)}
    sf.write_text(json.dumps(summary, indent=2), encoding="utf-8", newline="\n")
    return rf, mf, sf
