"""Exact match on the label, tolerant of one copied menu letter.

The menu is three words. A generating model asked for the word often copies
the letter too ("B. refusal"); that is presentation, so one leading
`<letter>. ` is stripped. Case is not forgiven (kills the case-blind
mutant), a prefix is not the word, a sentence around the word is not the
word, and a bare letter is uncheckable because the scorer never sees the
menu. The witnesses in eval.yaml pin each of those.
"""

import re

from dinostomp.scorers import ScoreResult

LABEL = re.compile(r"^[A-Z]{1,2}\.\s+")
BARE_LABEL = re.compile(r"^[A-Z]{1,2}\.?$")


def score(output: str, target):
    got = output.strip()
    targets = [str(t).strip() for t in (target if isinstance(target, list) else [target])]
    if got in targets:
        return True
    if BARE_LABEL.match(got):
        return ScoreResult("uncheckable", evidence=f"bare menu label {got!r}; the menu is not visible to the scorer")
    stripped = LABEL.sub("", got, count=1)
    return stripped != got and stripped in targets
