"""Inspect AI (`.eval` and `.json`) logs, adapted onto the record schema.

Inspect is the UK AI Security Institute's eval framework. Its logs are a nested
document rather than a table, which is the point of testing against it: the flat
importer maps columns, and a column mapper cannot read this at all.

    {"version": 2, "eval": {"model": "...", "task": "..."},
     "results": {"scores": [...]},
     "samples": [{"id": 1, "epoch": 1, "input": "...", "target": "...",
                  "output": {"choices": [{"message": {"content": "..."},
                                          "stop_reason": "stop"}]},
                  "scores": {"choice": {"value": "I", "answer": "C"}},
                  "events": [{"event": "tool", "function": "web_browser_go",
                              "arguments": {...}, "result": "..."}],
                  "model_usage": {"openai/gpt-4o-mini": {"input_tokens": 15235, ...}}}]}

A `.eval` file is a ZIP holding `header.json` and one JSON per sample under
`samples/`, so the same reader serves both formats.

WHAT THIS UNLOCKS that the lm-eval adapter could not. Inspect records generated
text, a finish reason, per-model token usage, and REAL TOOL EVENTS, so an
imported Inspect run can reach the trajectory checks (T1-T6), the truncation
check (R5), the ledger checks (R3, R18) and the re-scoring check (R8). An
imported loglikelihood log reaches almost none of those.

THREE THINGS IT REFUSES TO GUESS, each with a reason:

  - **The verdict vocabulary.** Inspect scores are `C` / `I` / `P` / `N`, not
    0/1. `C` and `I` map cleanly. `P` (partial) and a fractional score do NOT:
    this battery's verdict is binary, and calling a partial credit a pass or a
    fail would invent a number. They import as `uncheckable`, which is the
    honest answer and keeps them out of the accuracy denominator.
  - **Which scorer is THE score.** An Inspect task may run several. Two scorers
    that disagree are the acc/acc_norm problem again (D-023), so more than one
    is a refusal unless `--score-field` names which.
  - **Whose trace it is.** Inspect observed those tool calls; dinostomp did not.
    The manifest says `foreign_observed`, and T8 prints it as such.
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Any

from dinostomp.spec import Issue

# Inspect's score vocabulary. CORRECT and INCORRECT are the only two this
# battery's binary verdict can represent without inventing something.
VERDICTS = {"C": "pass", "I": "fail"}
UNREPRESENTABLE = {
    "P": "a PARTIAL credit, which a binary verdict cannot represent",
    "N": "NOANSWER, which Inspect distinguishes from an incorrect answer",
}


def detect(path: Path) -> bool:
    """Is this an Inspect log? Cheap, and never raises on a foreign file."""
    p = Path(path)
    if p.suffix == ".eval":
        try:
            with zipfile.ZipFile(p) as z:
                return "header.json" in z.namelist()
        except (zipfile.BadZipFile, OSError):
            return False
    if p.suffix != ".json":
        return False
    try:
        with p.open(encoding="utf-8") as fh:
            head = json.load(fh)
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        return False
    return isinstance(head, dict) and "eval" in head and "samples" in head


def read(path: Path) -> tuple[dict, list[dict]]:
    """(header, samples). Handles both the JSON log and the `.eval` archive."""
    p = Path(path)
    if p.suffix == ".eval":
        with zipfile.ZipFile(p) as z:
            header = json.loads(z.read("header.json"))
            names = sorted(n for n in z.namelist()
                           if n.startswith("samples/") and n.endswith(".json"))
            return header, [json.loads(z.read(n)) for n in names]
    doc = json.loads(p.read_text(encoding="utf-8"))
    return doc, list(doc.get("samples") or [])


def scorer_names(header: dict, samples: list[dict]) -> list[str]:
    """Every scorer that actually produced a value on some sample."""
    names: list[str] = []
    for s in samples:
        for name in (s.get("scores") or {}):
            if name not in names:
                names.append(name)
    return sorted(names)


def _text(sample: dict) -> str | None:
    """The generated answer. Absent rather than empty when there is none."""
    choices = ((sample.get("output") or {}).get("choices")) or []
    if not choices:
        return None
    content = (choices[0].get("message") or {}).get("content")
    if isinstance(content, str):
        return content
    # Multi-part content (text + images). Only the text parts are an answer.
    if isinstance(content, list):
        parts = [c.get("text", "") for c in content if isinstance(c, dict)]
        joined = "".join(parts)
        return joined if joined else None
    return None


def _finish_reason(sample: dict) -> str | None:
    choices = ((sample.get("output") or {}).get("choices")) or []
    return (choices[0].get("stop_reason") if choices else None) or None


def _usage(sample: dict) -> dict | None:
    """Token counts, summed across models the sample used.

    No cost: Inspect does not record spend, and computing one from a rate table
    this adapter does not have would be a number nobody measured. The absence
    makes R3 skip naming the field, which is the correct outcome.
    """
    usage = sample.get("model_usage") or {}
    if not usage:
        return None
    out = {"input_tokens": 0, "output_tokens": 0}
    for per_model in usage.values():
        if not isinstance(per_model, dict):
            continue
        out["input_tokens"] += int(per_model.get("input_tokens") or 0)
        out["output_tokens"] += int(per_model.get("output_tokens") or 0)
    return out


def _trajectory(sample: dict) -> list[dict]:
    """Tool events, in order, as recorded BY INSPECT.

    Only `event == "tool"`. Inspect logs model calls, sandbox operations, spans
    and store writes in the same stream; folding those in would inflate every
    step count and make T3 and T6 read a different thing than they do on a
    native run.
    """
    steps = []
    for e in sample.get("events") or []:
        if e.get("event") != "tool":
            continue
        result = e.get("result")
        steps.append({
            "tool": str(e.get("function") or ""),
            "args": e.get("arguments") if isinstance(e.get("arguments"), dict) else {},
            "result": result if isinstance(result, str) else json.dumps(result, default=str),
            # Inspect marks a failed call with an `error` field on the event.
            "ok": not e.get("error"),
        })
    return steps


def _verdict(raw: Any) -> tuple[str, str]:
    """(verdict, evidence). Never guesses; unrepresentable becomes uncheckable."""
    if isinstance(raw, bool):
        return ("pass" if raw else "fail"), "imported verdict, not re-derived here"
    if isinstance(raw, str):
        key = raw.strip().upper()
        if key in VERDICTS:
            return VERDICTS[key], f"imported Inspect verdict {raw!r}"
        if key in UNREPRESENTABLE:
            return "uncheckable", (f"Inspect scored this {raw!r}: {UNREPRESENTABLE[key]}. "
                                   "Imported as uncheckable rather than forced into a "
                                   "pass or a fail, so it stays out of the accuracy "
                                   "denominator instead of inventing a number")
        return "uncheckable", (f"Inspect scored this {raw!r}, which is not a verdict this "
                               "battery can represent; imported as uncheckable rather than "
                               "guessed")
    if isinstance(raw, (int, float)) and raw in (0, 1):
        return ("pass" if raw == 1 else "fail"), "imported verdict, not re-derived here"
    if isinstance(raw, (int, float)):
        return "uncheckable", (f"Inspect scored this {raw}, a fractional score. A binary "
                               "verdict cannot represent partial credit, so it is imported "
                               "as uncheckable rather than rounded")
    return "uncheckable", f"Inspect score {raw!r} is not interpretable as a verdict"


def to_records(header: dict, samples: list[dict], *, scorer: str, model: str,
               seed: int, provider: str = "imported") -> tuple[list[dict], list[Issue]]:
    """Inspect samples to schema-conforming records. Nothing is fabricated."""
    from dinostomp.spec import validate_obj

    out: list[dict] = []
    issues: list[Issue] = []
    for n, s in enumerate(samples):
        score = (s.get("scores") or {}).get(scorer)
        if score is None:
            issues.append(Issue(
                loc=f"sample {s.get('id', n)}", check="import",
                message=f"no score from {scorer!r} on this sample; a partially scored log "
                        "would import as a run with holes in it"))
            continue
        verdict, evidence = _verdict(score.get("value") if isinstance(score, dict) else score)
        item_id = str(s.get("id"))
        # `epoch` is Inspect's word for a repeat: the same item, run again.
        repeat = max(0, int(s.get("epoch") or 1) - 1)
        rec: dict[str, Any] = {
            "key": f"{item_id}#r{repeat}",
            "item_id": item_id,
            "model": model,
            "provider": provider,
            "seed": seed,
            "repeat": repeat,
            "score": {"verdict": verdict, "evidence": evidence},
            "ts": str(s.get("completed_at") or (header.get("eval") or {}).get("created")
                      or "1970-01-01T00:00:00+00:00"),
        }
        text = _text(s)
        if text is not None:
            rec["output"] = text
        finish = _finish_reason(s)
        if finish:
            rec["finish_reason"] = finish
        usage = _usage(s)
        if usage:
            rec["usage"] = usage
        traj = _trajectory(s)
        if traj:
            rec["trajectory"] = traj
        problems = validate_obj(rec, "record")
        if problems:
            issues.append(Issue(loc=f"sample {s.get('id', n)}", check="import",
                                message=f"produced a schema-invalid record: {problems[0].message}"))
            continue
        out.append(rec)
    return out, issues


def summarise(header: dict, samples: list[dict]) -> list[str]:
    """Human-readable notes about what was found, printed before importing."""
    ev = header.get("eval") or {}
    notes = [f"detected: Inspect AI log (version {header.get('version')})"]
    if ev.get("task"):
        notes.append(f"task     <- {ev['task']}")
    if ev.get("model"):
        notes.append(f"model    <- {ev['model']}")
    epochs = {int(s.get("epoch") or 1) for s in samples}
    if len(epochs) > 1:
        notes.append(f"epochs   <- {min(epochs)}..{max(epochs)} (imported as run.repeats)")
    with_tools = sum(1 for s in samples if _trajectory(s))
    if with_tools:
        notes.append(f"tools    <- {with_tools} sample(s) carry tool events "
                     "(recorded by Inspect, not by this engine)")
    return notes
