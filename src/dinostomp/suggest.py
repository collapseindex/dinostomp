"""Propose witness cases, without letting the proposal grade its own homework.

The witness gate is this tool's best idea and its biggest onboarding tax. A
scorer may not score real data until its author has written concrete outputs it
must REJECT, and writing those from a blank page is the step where people bounce.

The obvious automation is dangerous in a specific way. If the tool generates
candidate witnesses and accepts the set that kills all eight mutants, then the
witnesses have been FITTED to the mutants, and W1 stops being an independent
measure of witness adequacy: it becomes the thing they were optimised against.
That is Goodhart applied to your own safety net, one level up from the failure
the gate exists to prevent.

So this module obeys three rules:

  1. It PROPOSES. Every case comes back for a human to accept, edit, or reject,
     and nothing is written into a spec by this module.
  2. Proposals are derived from the DATA and from named bug classes, never from
     running the mutants and keeping whatever happens to pass. The mutants stay
     the exam; these are not the answer key.
  3. `dinostomp suggest-witnesses` reports gauntlet coverage for suggested and
     authored witnesses SEPARATELY, so a suite that only survives because the
     tool wrote it is visible as exactly that.

A suite made entirely of accepted suggestions is a suite nobody thought about.
The command says so, every time.
"""

from __future__ import annotations

import re

# One proposal per known scoring-bug class, mirroring the mutation gauntlet's
# vocabulary. These are TRANSFORMS of a real target from the dataset, so the
# author is reading their own data rather than a generic placeholder.
_NUMBER = re.compile(r"-?\d+(?:\.\d+)?")


def _first_target(items: list[dict]) -> str | None:
    for item in items:
        t = item.get("target")
        if isinstance(t, list):
            t = t[0] if t else None
        if isinstance(t, str) and t.strip():
            return t.strip()
        if isinstance(t, (int, float)):
            return str(t)
    return None


def _truncate(text: str) -> str | None:
    """A strict prefix that is still non-empty, and still a plausible answer."""
    if len(text) < 2:
        return None
    cut = max(1, len(text) - max(1, len(text) // 3))
    return text[:cut]


def propose(items: list[dict], kind: str) -> list[dict]:
    """Candidate witnesses for this dataset and scorer kind. Never authoritative.

    Returns dicts in spec form, each carrying a `why` that names the bug class
    it is aimed at, so an author accepting one knows what they are buying.
    """
    target = _first_target(items)
    if target is None:
        return []
    numeric = bool(_NUMBER.fullmatch(target))
    out: list[dict] = [
        {"output": target, "target": target, "expect": "pass",
         "why": "the scorer must accept the reference answer itself"},
    ]

    # A scorer that cannot fail is not a scorer, so the rejections are the
    # point. One per bug class the gauntlet knows about.
    prefix = _truncate(target)
    if prefix and prefix != target:
        out.append({"output": prefix, "target": target, "expect": "fail",
                    "why": "no credit for a truncated answer"})
    if kind != "includes":
        out.append({"output": f"The answer is {target}", "target": target, "expect": "fail",
                    "why": "no credit for wrappers around the answer"})
    out.append({"output": f"not {target}", "target": target, "expect": "fail",
                "why": "a denied mention is not a mention"})

    if numeric:
        out.append({"output": "", "target": target, "expect": "uncheckable",
                    "why": "a numeric scorer handed no number has not judged the answer wrong; "
                           "it has not judged it"})
    else:
        swapped = target.upper() if target.lower() == target else target.lower()
        if swapped != target:
            out.append({"output": swapped, "target": target, "expect": "fail",
                        "why": "decide out loud whether case is part of the contract; flip this "
                               "to `pass` if it is not"})
        if " " in target:
            out.append({"output": target.replace(" ", "  ", 1), "target": target, "expect": "fail",
                        "why": "a doubled space is part of the match, or say that it is not"})
        out.append({"output": "", "target": target, "expect": "fail",
                    "why": "an empty answer is never correct"})

    other = None
    for item in items:
        t = item.get("target")
        t = t[0] if isinstance(t, list) and t else t
        if isinstance(t, str) and t.strip() and t.strip() != target:
            other = t.strip()
            break
    if other:
        out.append({"output": other, "target": target, "expect": "fail",
                    "why": "a different item's reference answer must not pass this one"})
    return out


def coverage_split(gauntlet_all, gauntlet_authored) -> dict:
    """What the AUTHORED witnesses catch on their own.

    The number that matters is not "do all mutants die", it is "do any die
    because a human thought about this scorer". A suite that only holds up with
    the suggestions in it is a suite nobody thought about, and the split makes
    that visible instead of averaging it away.
    """
    return {
        "killed_together": len(getattr(gauntlet_all, "killed", []) or []),
        "killed_by_authored": len(getattr(gauntlet_authored, "killed", []) or []),
        "survivors_together": [m.name for m in (getattr(gauntlet_all, "survived", []) or [])],
        "survivors_authored_only": [m.name for m in
                                    (getattr(gauntlet_authored, "survived", []) or [])],
    }
