"""Graded scorer: partial credit for being close, not just exactly right.

Returning a float in [0,1] is the whole partial-credit idiom. dinostomp keeps
the verdict categorical (pass only on a perfect 1.0, so every dichotomous check
still reads a clean pass rate) and carries the float alongside as graded credit,
which the report averages into `partial_score` beside accuracy.
"""
import re


def score(output, target):
    m = re.search(r"-?\d+", str(output))
    if m is None:
        return None  # no number to grade: uncheckable, excluded from denominators
    got = int(m.group())
    want = int(str(target))
    # full credit exactly right, linearly less to zero by an error of 10.
    return max(0.0, 1.0 - abs(got - want) / 10.0)
