"""Four deterministic offline answerers with different HOUSE STYLES.

The point of this pod is that exact match cannot grade these. Every bot knows
the same facts and differs only in how it says them: bare, wrapped, hedged, or
chatty. A string comparison would rank them by punctuation. A judge is supposed
to see through the wrapper to the answer, and J1/J2/J3 are what establish that
this particular judge actually does.

Skill still varies (via the same hash trick the dry provider uses), so the fleet
has real psychometric structure on top of the stylistic variation.
"""

from __future__ import annotations

import hashlib

# capital -> country. Shared by every bot: they differ in style and skill only.
FACTS = {
    "paris": "France", "tokyo": "Japan", "ottawa": "Canada", "canberra": "Australia",
    "lisbon": "Portugal", "nairobi": "Kenya", "hanoi": "Vietnam", "oslo": "Norway",
    "quito": "Ecuador", "amman": "Jordan", "dublin": "Ireland", "helsinki": "Finland",
    "warsaw": "Poland", "stockholm": "Sweden", "copenhagen": "Denmark", "vienna": "Austria",
    "budapest": "Hungary", "athens": "Greece", "lima": "Peru", "rabat": "Morocco",
    "reykjavik": "Iceland", "kathmandu": "Nepal", "havana": "Cuba", "cairo": "Egypt",
    "santiago": "Chile", "tunis": "Tunisia",
}

SKILL = {"bot-bare": 0.92, "bot-wrapped": 0.74, "bot-hedged": 0.56, "bot-chatty": 0.38}

STYLE = {
    "bot-bare": "{a}",
    "bot-wrapped": "The answer is {a}.",
    "bot-hedged": "I believe it is {a}, though I would double-check.",
    "bot-chatty": "Great question! After thinking it through, I would say {a}. Hope that helps!",
}


def _unit(key: str) -> float:
    return int(hashlib.sha256(key.encode()).hexdigest()[:8], 16) / 0xFFFFFFFF


def _city(question: str) -> str:
    words = question.rstrip("?").strip().split()
    return words[words.index("is") + 1].lower() if "is" in words else words[-1].lower()


def run(item: dict, ctx: dict) -> dict:
    model = ctx["model"]
    city = _city(str(item["input"]))
    right = FACTS.get(city, "")
    if _unit(f"d|{city}") < SKILL.get(model, 0.9):
        answer = right
    else:
        # A wrong answer that is still a plausible, on-topic country: the only
        # kind of wrong answer a judge has to actually think about.
        others = [c for c in FACTS.values() if c != right]
        answer = others[int(_unit(f"w|{model}|{city}") * len(others))]
    return {"output": STYLE.get(model, "{a}").format(a=answer)}
