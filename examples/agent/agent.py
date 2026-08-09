"""A deterministic offline retrieval agent, mounted on the target rail.

Four configurations share this entrypoint, keyed on `ctx["model"]`. Each has a
different slice of the same corpus, so the fleet spreads the way a real fleet
does and the psychometric checks have something to measure:

  agent-grounded  the whole index; answers only from what it retrieved
  agent-partial   two thirds of the index
  agent-narrow    a third of the index
  agent-lazy      answers from its own memory FIRST, then retrieves anyway, so
                  its trace looks diligent while its answer owes it nothing

That last one is the pod's teaching case: agent-lazy scores 100% and every
trajectory check about tool USE passes it, because it really does call the
required tool. Only T4 (grounding) notices that two of its correct answers
appear in no retrieved evidence at all.

No network, no key, no spend: the agent rail demos end to end for free, exactly
like the dry provider.
"""

from __future__ import annotations

# The index. Order is load-bearing: a configuration's coverage is a prefix of
# this dict, so early cities are easy for everyone and late ones separate the
# fleet (item difficulty, without hand-tuning anything).
CORPUS = {
    "paris": ("France", "Paris is the capital of France, on the Seine."),
    "tokyo": ("Japan", "Tokyo is the capital of Japan and its largest city."),
    "ottawa": ("Canada", "Ottawa is the capital of Canada, in Ontario."),
    "canberra": ("Australia", "Canberra is the capital of Australia."),
    "lisbon": ("Portugal", "Lisbon is the capital of Portugal, on the Tagus."),
    "nairobi": ("Kenya", "Nairobi is the capital of Kenya."),
    "hanoi": ("Vietnam", "Hanoi is the capital of Vietnam."),
    "oslo": ("Norway", "Oslo is the capital of Norway."),
    "quito": ("Ecuador", "Quito is the capital of Ecuador, high in the Andes."),
    "amman": ("Jordan", "Amman is the capital of Jordan."),
    "dublin": ("Ireland", "Dublin is the capital of Ireland, on the Liffey."),
    "helsinki": ("Finland", "Helsinki is the capital of Finland."),
    "warsaw": ("Poland", "Warsaw is the capital of Poland, on the Vistula."),
    "stockholm": ("Sweden", "Stockholm is the capital of Sweden."),
    "copenhagen": ("Denmark", "Copenhagen is the capital of Denmark."),
    "vienna": ("Austria", "Vienna is the capital of Austria, on the Danube."),
    "budapest": ("Hungary", "Budapest is the capital of Hungary."),
    "athens": ("Greece", "Athens is the capital of Greece."),
    "lima": ("Peru", "Lima is the capital of Peru, on the Pacific coast."),
    "rabat": ("Morocco", "Rabat is the capital of Morocco."),
    "reykjavik": ("Iceland", "Reykjavik is the capital of Iceland."),
    "kathmandu": ("Nepal", "Kathmandu is the capital of Nepal."),
    "havana": ("Cuba", "Havana is the capital of Cuba."),
    "cairo": ("Egypt", "Cairo is the capital of Egypt, on the Nile."),
}

# Two items the index does NOT cover. A grounded agent must come back empty
# here; only the lazy one can answer, and only from memory.
MEMORY = {"santiago": "Chile", "tunis": "Tunisia"}

# How much of the index each configuration can see.
COVERAGE = {
    "agent-grounded": 24,
    "agent-partial": 16,
    "agent-narrow": 9,
    "agent-lazy": 24,
}

CITIES = list(CORPUS)


def _city(question: str) -> str:
    """Pull the city out of 'Which country is <City> the capital of?'.

    Parsing the question is not knowledge: a configuration with a narrow index
    still reads the question fine, it just cannot look the answer up.
    """
    words = question.rstrip("?").strip().split()
    return words[words.index("is") + 1].lower() if "is" in words else words[-1].lower()


def _retrieve(city: str, coverage: int) -> tuple[str, bool]:
    """The index lookup, limited to this configuration's slice."""
    if city in CITIES[:coverage]:
        return CORPUS[city][1], True
    return f"no passage found for {city!r}", False


def _country_from(passage: str) -> str:
    """Read the country straight out of the retrieved sentence. Nothing
    retrieved means nothing to say."""
    marker = "the capital of "
    if marker not in passage:
        return ""
    tail = passage.split(marker, 1)[1]
    for stop in (",", ".", " and"):
        if stop in tail:
            tail = tail.split(stop, 1)[0]
    return tail.strip()


def run(item: dict, ctx: dict) -> dict:
    model = ctx["model"]
    coverage = COVERAGE.get(model, len(CITIES))
    city = _city(str(item["input"]))

    if model == "agent-lazy":
        # Answer first, retrieve second. The required tool is called on every
        # item, so T2 is satisfied; the answer still did not come from it.
        answer = MEMORY.get(city) or CORPUS.get(city, ("", ""))[0]
        passage, ok = _retrieve(city, coverage)
        return {
            "output": answer or "unknown",
            "trajectory": [{"tool": "retrieve", "args": {"city": city}, "result": passage, "ok": ok}],
        }

    passage, ok = _retrieve(city, coverage)
    trajectory = [{"tool": "retrieve", "args": {"city": city}, "result": passage, "ok": ok}]
    answer = _country_from(passage)
    if not answer:
        trajectory.append({"tool": "give_up", "args": {"city": city}, "result": "no evidence", "ok": True})
        answer = "unknown"
    return {"output": answer, "trajectory": trajectory}
