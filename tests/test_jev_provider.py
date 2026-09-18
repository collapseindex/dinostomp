"""The `jev` provider: choices in, a choice out, probabilities on the record, no prompt.

A decisions model takes the menu as the request. The runner must not render
an option block into its prompt, the shuffle probe must permute the menu
rather than the text, and the blind probe must still blank the state.
"""

import json

import pytest

from dinostomp.providers import DecisionsProvider, ProviderError, make_provider
from dinostomp.runner import shuffled_choices

ITEM = {"id": "i1", "input": "Which ocean borders Portugal?", "target": "Atlantic Ocean",
        "choices": ["Atlantic Ocean", "Indian Ocean", "NONE"],
        "metadata": {"options": {"Atlantic Ocean": "The Atlantic", "Indian Ocean": "The Indian", "NONE": "none fits"}}}
REPLY = {"model": "typesafe/jev-1.13-20260917",
         "answers": {"decision": {"type": "choice", "choice": "Atlantic Ocean",
                                  "probabilities": {"Atlantic Ocean": 0.9, "Indian Ocean": 0.08, "NONE": 0.02},
                                  "confidence": 0.88}},
         "usage": {"input_tokens": 120, "output_tokens": 30, "cost": 0.00000504}}


def _provider(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    seen = {}

    def fake_request(self, url, headers, payload):
        seen["url"], seen["payload"] = url, payload
        return REPLY

    monkeypatch.setattr(DecisionsProvider, "_request", fake_request)
    return make_provider("jev", "typesafe/jev-1.13"), seen


def test_payload_is_a_choice_question_over_the_menu(monkeypatch):
    provider, seen = _provider(monkeypatch)
    completion = provider.complete(ITEM, 42, {"instructions": "Pick the ocean."})
    q = seen["payload"]["questions"]["decision"]
    assert seen["payload"]["state"] == ITEM["input"]
    assert q["type"] == "choice" and q["instructions"] == "Pick the ocean."
    assert q["criteria"] == ITEM["metadata"]["options"]
    assert completion.text == "Atlantic Ocean"
    assert completion.cost_usd == pytest.approx(0.00000504)
    assert completion.input_tokens == 120 and completion.model_reported.startswith("typesafe/jev")
    evidence = json.loads(completion.trajectory[0]["result"])
    assert evidence["distribution"]["Atlantic Ocean"] == 0.9 and evidence["confidence"] == 0.88
    assert evidence["p_target"] == 0.9


def test_criteria_fall_back_to_the_choice_text(monkeypatch):
    provider, seen = _provider(monkeypatch)
    bare = {k: v for k, v in ITEM.items() if k != "metadata"}
    provider.complete(bare, 42, {})
    assert seen["payload"]["questions"]["decision"]["criteria"] == {c: c for c in ITEM["choices"]}


def test_needs_choices(monkeypatch):
    provider, _ = _provider(monkeypatch)
    with pytest.raises(ProviderError):
        provider.complete({"id": "x", "input": "q", "target": "a"}, 42, {})


def test_takes_choices_and_shuffle_permutes_the_menu():
    assert DecisionsProvider.takes_choices is True
    order = shuffled_choices(ITEM, 7)
    assert sorted(order) == sorted(ITEM["choices"]) and order != ITEM["choices"]
    assert shuffled_choices(ITEM, 7) == order, "deterministic per (item, seed)"


def test_typesafe_is_the_same_call_on_the_direct_endpoint(monkeypatch):
    """One class, two doors: the record's provider says which was used, and a
    reply without `cost` leaves pricing to the spec's rates."""
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    seen = {}

    def fake_request(self, url, headers, payload):
        seen["url"], seen["auth"], seen["payload"] = url, headers["authorization"], payload
        direct = {**REPLY, "model": "jev-latest", "usage": {"input_tokens": 120, "output_tokens": 30}}
        return direct

    monkeypatch.setattr(DecisionsProvider, "_request", fake_request)
    provider = make_provider("typesafe", "jev-latest")
    assert provider.provider_name == "typesafe"
    completion = provider.complete(ITEM, 42, {})
    assert seen["url"] == "https://api.typesafe.ai/v1/systemone"
    assert seen["auth"] == "Bearer test-key"
    assert seen["payload"]["model"] == "jev-latest"
    assert seen["payload"]["questions"]["decision"]["type"] == "choice"
    assert completion.text == "Atlantic Ocean" and completion.cost_usd is None
    assert completion.input_tokens == 120
    assert json.loads(completion.trajectory[0]["result"])["distribution"]["Atlantic Ocean"] == 0.9


def test_typesafe_refuses_to_run_without_its_own_key(monkeypatch):
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    monkeypatch.setenv("OPENROUTER_API_KEY", "not-the-right-door")
    with pytest.raises(ProviderError, match="TYPESAFE_API_KEY"):
        make_provider("typesafe", "jev-latest")
