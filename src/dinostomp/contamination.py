"""Canary regurgitation: asking a model whether it has already read your data.

S8 only ever checked that a canary string TRAVELS with the dataset. It could not
tell you whether a model had swallowed it, and the README said so. This closes
that, with one design constraint that matters more than the feature:

**An instrument that cannot fire tells you nothing.** A fresh canary is a random
string no model has ever seen, so a probe against it comes back clean whether
the model is contaminated or not, and whether the probe works or not. A green
result there is unfalsifiable, which is exactly the flattering shape this
project exists to refuse.

So every probe carries a POSITIVE CONTROL: a passage that is certainly in any
model's training data. If a model cannot complete the control, the probe has no
demonstrated sensitivity on that model and the check SKIPS with that reason
rather than reporting a clean bill of health. Only a model that proves it can
regurgitate something is allowed to testify that it cannot regurgitate your
canary.

The result is one honest sentence in three flavours:

  control reproduced, canary not  -> pass, and the pass means something
  control reproduced, canary too  -> WARN: this model has seen your data
  control not reproduced          -> skip: the probe is blind on this model
"""

from __future__ import annotations

import json
import re
from pathlib import Path

# Passages that are in every general-purpose model's training data many times
# over. The tail is what the model must supply; short and unambiguous, so a
# failure to produce it means the probe is blind rather than the model is coy.
CONTROLS = [
    ("To be, or not to be, that is the", "question"),
    ("We hold these truths to be self-evident, that all men are created", "equal"),
    ("The quick brown fox jumps over the lazy", "dog"),
]

PROMPT = (
    "Continue this text exactly as it appears in your training data. "
    "Reply with the continuation only, no commentary.\n\n{head}"
)

# How much of the canary is handed over as the prompt. Enough to be
# unambiguous, little enough that completing it requires memorisation.
HEAD_FRACTION = 0.5
MIN_TAIL_CHARS = 6

# A canary short enough to be guessed is not evidence of anything. Below this
# the probe refuses to run rather than producing a finding nobody should trust.
MIN_CANARY_CHARS = 16


def read_canary(data_path: Path) -> str | None:
    """The `_canary` string travelling with a jsonl dataset, if any."""
    try:
        for line in data_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict) and obj.get("_canary"):
                return str(obj["_canary"])
    except OSError:
        return None
    return None


def split_canary(canary: str) -> tuple[str, str]:
    """(head, tail). The head is the prompt; the tail is what memorisation
    would have to supply."""
    cut = max(len(canary) - MIN_TAIL_CHARS, int(len(canary) * HEAD_FRACTION))
    cut = min(cut, len(canary) - MIN_TAIL_CHARS) if len(canary) > MIN_TAIL_CHARS else len(canary) // 2
    return canary[:cut], canary[cut:]


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip().lower()


def reproduced(output: str, tail: str) -> bool:
    """Did the response contain the continuation? Whitespace and case are
    ignored; nothing else is, because a near-miss is not a memory."""
    tail_n = _norm(tail)
    return bool(tail_n) and tail_n in _norm(output)


def build_cases(canary: str) -> list[dict]:
    """The canary case plus its controls. Order is fixed so a run file reads
    the same way every time."""
    head, tail = split_canary(canary)
    cases = [{"case_id": "canary", "kind": "canary", "head": head, "tail": tail}]
    for idx, (chead, ctail) in enumerate(CONTROLS):
        cases.append({"case_id": f"control{idx}", "kind": "control", "head": chead, "tail": ctail})
    return cases


def prompt_for(case: dict) -> str:
    return PROMPT.format(head=case["head"])
