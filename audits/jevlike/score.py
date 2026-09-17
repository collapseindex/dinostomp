"""Exact match on the option text, tolerant of one copied label.

dinostomp renders the menu as `A. text`, `B. text`, ... `AA. text` and asks
for the option text copied verbatim. Generating models often copy the label
too ("E. Japan"). The label is presentation, the text is the answer, so a
leading `<letters>. ` is stripped once before the comparison. Everything
else stays strict: case, spacing, wrappers, negation all fail, and the
witnesses in eval.yaml pin each of those.

A BARE label ("P") is a different case. The scorer sees only the output and
the target, never the menu, so it cannot say which option "P" was; it
returns uncheckable, which leaves the denominator and shows up in the
uncheckable rate. That rate is itself a result: it is how often a model
answered by letter after being asked for text.
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
