"""Instruction framings: the same question, asked differently.

Every eval fixes one phrasing of "answer this" and reports the number it gets.
That phrasing is a free parameter nobody registered. It moves scores, and on a
leaderboard it can move the ORDER, which is the part that turns a measurement
into a decision someone acts on.

This is the same family as the blind and shuffle probes. Those vary what the
model is shown about the ITEM; this varies what it is told about the TASK, and
leaves the item's own text byte-identical.

The rules every framing here obeys, so that a swing is attributable:

  - it must not add information about the answer, or it becomes a hint
  - it must not change the requested output FORMAT, or the scorer moves too and
    the swing measures the scorer
  - it must be something a real harness would plausibly write, because a swing
    under an absurd framing is not evidence about anything

`{q}` is the item's rendered input, untouched.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Framing:
    name: str
    template: str
    note: str

    def render(self, question: str) -> str:
        return self.template.replace("{q}", question)


FRAMINGS = [
    Framing("bare", "{q}",
            "the item alone, which is what most harnesses send"),
    Framing("instructed", "Answer the following question.\n\n{q}",
            "an explicit task statement"),
    Framing("polite", "Could you please answer this question?\n\n{q}",
            "politeness, which changes nothing about the task"),
    Framing("expert", "You are an expert. Answer the following question.\n\n{q}",
            "a persona, the most common prompt-engineering move there is"),
    Framing("terse", "Answer concisely.\n\n{q}",
            "a brevity instruction that does not name a format"),
    Framing("stepwise", "Think it through, then answer.\n\n{q}",
            "an invitation to reason, which is the framing most likely to "
            "genuinely change capability rather than just presentation"),
]

FRAMINGS_BY_NAME = {f.name: f for f in FRAMINGS}
DEFAULT_FRAMINGS = [f.name for f in FRAMINGS]


def framed_input(item: dict, framing_name: str, rendered: str | None = None) -> str:
    """Apply a framing to an item's input, leaving the item's own text alone."""
    question = rendered if rendered is not None else item["input"]
    if not isinstance(question, str):
        # chat-message inputs are already a task statement; framing them would
        # mean rewriting someone's system prompt, which is not this probe's job
        raise ValueError("template probe needs a plain-string input")
    return FRAMINGS_BY_NAME[framing_name].render(question)
