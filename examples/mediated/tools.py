"""The tools the HARNESS holds. The agent never imports this file.

That is the whole difference between this pod and `examples/agent`. There, the
agent owns its tools and writes its own account of using them. Here it can only
reach them through the `tools` object dinostomp hands it, so the trajectory in
the records is a log of calls that happened rather than a claim that they did.

Deliberately not the answer key: several entries are near neighbours, so
retrieving the wrong topic is possible and produces a wrong-but-plausible
answer instead of an obviously empty one.
"""

CORPUS = {
    "photosynthesis": "Photosynthesis converts light energy into chemical energy stored as "
                      "glucose, releasing oxygen. It happens in chloroplasts.",
    "respiration": "Cellular respiration breaks down glucose to release ATP, consuming oxygen "
                   "and producing carbon dioxide. It happens largely in mitochondria.",
    "transpiration": "Transpiration is the loss of water vapour from plant leaves through "
                     "stomata, which pulls water up from the roots.",
    "mitosis": "Mitosis divides one nucleus into two genetically identical nuclei, used for "
               "growth and repair.",
    "meiosis": "Meiosis produces four genetically distinct haploid cells from one diploid "
               "cell, and is used to make gametes.",
    "osmosis": "Osmosis is the movement of water across a semipermeable membrane from lower "
               "to higher solute concentration.",
    "diffusion": "Diffusion is the net movement of particles from higher to lower "
                 "concentration, requiring no energy input.",
    "enzymes": "Enzymes are protein catalysts that lower activation energy. They are not "
               "consumed by the reaction they speed up.",
}

# What a correct answer looks like for each topic. The corpus sentence above is
# prose; this is the one word the scorer grades, so a grounded agent has to get
# it OUT of the snippet rather than merely near it.
ANSWER = {
    "photosynthesis": "chloroplasts",
    "respiration": "mitochondria",
    "transpiration": "stomata",
    "mitosis": "two",
    "meiosis": "four",
    "osmosis": "higher",
    "diffusion": "lower",
    "enzymes": "activation",
}


def retrieve(key: str = "") -> str:
    """Look up one corpus entry. A miss returns empty rather than raising: a
    wrong key is a thing an agent DID, and the trace should show it doing it."""
    return CORPUS.get(str(key).strip().lower(), "")


def shell(cmd: str = "") -> str:
    """Offered and forbidden, so the denial path has something real to deny.

    A policy about a tool the harness does not hold enforces nothing, which the
    spec cross-checks now refuse. This tool exists to make `forbidden_tools`
    mean something on this pod: reaching for it is denied at call time and the
    attempt lands in the trace.
    """
    return f"(would have run: {cmd})"
