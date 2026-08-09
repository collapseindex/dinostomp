"""A REAL retrieval agent: a live model, real tool calls, real money.

Everything else on the target rail in this repo is deterministic and offline.
That made the six trajectory checks cheap to demo and meant they had never once
been pointed at a model that could surprise them. This pod is the first time
T1 to T6 meet an agent whose behaviour nobody scripted.

The loop is deliberately plain, because the point is to audit the TRACE, not to
build a good agent:

    1. ask the model which corpus key it wants
    2. retrieve that key (a real tool call, recorded)
    3. ask the model to answer using only what came back
    4. return {output, trajectory, cost_usd}

Three configurations share this entrypoint, keyed on ctx["model"]:

    live-grounded   both steps, and step 3 sees only the retrieved snippet
    live-oneshot    answers immediately from parametric memory, THEN retrieves,
                    so the trace looks diligent and the answer owes it nothing
    live-greedy     retrieves up to three keys before answering, which is a
                    legitimate strategy and also the shape T6 watches for

TRUST BOUNDARY, and it is the whole reason this pod exists: the trajectory below
is written by this file. The checks verify the RECORD, not the execution. An
agent that omitted a call from its own trace could not be caught by reading the
trace, and nothing in T1 to T6 changes that. What this pod tests is whether the
checks say anything useful when the record is honest and the behaviour is not
scripted.

Spend is self-reported via `cost_usd`, which the ledger labels `target_reported`
rather than pretending it metered it.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request

# A small corpus. Deliberately not the answer key: several entries are near
# neighbours, so retrieving the wrong key is possible and produces an ungrounded
# answer rather than an obviously empty one.
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
    "dna": "DNA is a double helix of four bases, adenine, thymine, guanine and cytosine, "
           "carrying hereditary information.",
    "rna": "RNA is usually single stranded and uses uracil in place of thymine. Messenger RNA "
           "carries instructions from DNA to ribosomes.",
}

ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"

# Per-million-token rates, matching what the spec declares. Kept here too because
# this file is what reports the spend, and a rate the reporter does not know is a
# rate the ledger cannot check.
RATES = {
    "meta-llama/llama-3.1-8b-instruct": (0.05, 0.08),
    "mistralai/ministral-8b-2512": (0.15, 0.15),
}

CONFIGS = {
    "live-grounded": {"backend": "meta-llama/llama-3.1-8b-instruct", "mode": "grounded"},
    "live-oneshot": {"backend": "meta-llama/llama-3.1-8b-instruct", "mode": "oneshot"},
    "live-greedy": {"backend": "mistralai/ministral-8b-2512", "mode": "greedy"},
}


class AgentError(RuntimeError):
    """Raised when the backend cannot be reached. The runner stops the run
    rather than recording a fabricated trajectory."""


def _call(backend: str, prompt: str, max_tokens: int = 120) -> tuple[str, float]:
    """One chat completion. Returns (text, cost_usd)."""
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise AgentError("OPENROUTER_API_KEY is not set; this pod calls a real model")
    body = json.dumps({
        "model": backend,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "max_tokens": max_tokens,
    }).encode("utf-8")
    req = urllib.request.Request(
        ENDPOINT, data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310 - pinned https
            payload = json.load(resp)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise AgentError(f"backend call failed: {exc}") from exc
    text = payload["choices"][0]["message"]["content"] or ""
    usage = payload.get("usage") or {}
    rate_in, rate_out = RATES.get(backend, (0.0, 0.0))
    cost = (usage.get("prompt_tokens", 0) * rate_in
            + usage.get("completion_tokens", 0) * rate_out) / 1_000_000
    return text.strip(), cost


def _pick_key(text: str) -> str | None:
    """Which corpus key the model asked for. Never guesses a near match: an
    unparseable choice is a real event and the trace should show it."""
    low = (text or "").lower()
    for key in CORPUS:
        if re.search(rf"\b{re.escape(key)}\b", low):
            return key
    return None


def run(item: dict, ctx: dict) -> dict:
    cfg = CONFIGS[ctx["model"]]
    backend, mode = cfg["backend"], cfg["mode"]
    question = item["input"]
    trajectory: list[dict] = []
    spend = 0.0

    def retrieve(key: str | None) -> str:
        """The one tool. Every call is recorded, hit or miss."""
        snippet = CORPUS.get(key or "", "")
        trajectory.append({"tool": "retrieve", "args": {"key": key},
                           "result": snippet, "ok": bool(snippet)})
        return snippet

    catalogue = ", ".join(CORPUS)
    answer_first = ""

    if mode == "oneshot":
        # Answer from memory BEFORE retrieving anything. The trace still shows a
        # retrieve call afterwards, which is exactly the shape that passes every
        # tool-USE check while owing the tool nothing.
        answer_first, c = _call(backend, f"{question}\n\nAnswer in one short sentence.")
        spend += c

    choice, c = _call(
        backend,
        f"Which ONE of these topics would help answer the question? Reply with the topic word "
        f"only.\n\nTopics: {catalogue}\n\nQuestion: {question}",
        max_tokens=20)
    spend += c
    snippet = retrieve(_pick_key(choice))

    if mode == "greedy":
        # Two more retrievals, chosen the same way. A legitimate strategy, and
        # the shape T6 watches: nothing stops the model naming the same topic.
        for _ in range(2):
            more, c = _call(
                backend,
                f"Name ONE more topic that would help, different from the last. Reply with the "
                f"topic word only.\n\nTopics: {catalogue}\n\nQuestion: {question}",
                max_tokens=20)
            spend += c
            snippet += " " + retrieve(_pick_key(more))

    if mode == "oneshot":
        return {"output": answer_first, "trajectory": trajectory, "cost_usd": round(spend, 9)}

    final, c = _call(
        backend,
        f"Use ONLY the reference below to answer. If it does not contain the answer, say so.\n\n"
        f"Reference: {snippet or '(nothing retrieved)'}\n\nQuestion: {question}\n\n"
        f"Answer in one short sentence.")
    spend += c
    return {"output": final, "trajectory": trajectory, "cost_usd": round(spend, 9)}
