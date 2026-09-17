"""`params.reasoning_effort` reaches the wire in each provider's own shape.

D-098: a reasoning model asked for a one-word answer spent all 256 output
tokens on hidden reasoning, returned an empty string with
finish_reason=length, and was billed for every token. The spec had no way to
say "do not think"; now it does.
"""

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

import dinostomp
from dinostomp.providers import OpenAICompatProvider, OpenRouterProvider

SCHEMA_DIR = Path(dinostomp.__file__).parent / "schemas"

ITEM = {"id": "i", "input": "Q?", "target": "A"}
REPLY = {"choices": [{"message": {"content": "A"}, "finish_reason": "stop"}],
         "usage": {"prompt_tokens": 3, "completion_tokens": 1}, "model": "m"}


def _capture(monkeypatch, cls, key_env):
    monkeypatch.setenv(key_env, "test-key")
    seen = {}

    def fake_request(self, url, headers, payload):
        seen["payload"] = payload
        return REPLY

    monkeypatch.setattr(cls, "_request", fake_request)
    return seen


def test_openai_sends_top_level_reasoning_effort(monkeypatch):
    seen = _capture(monkeypatch, OpenAICompatProvider, "OPENAI_API_KEY")
    OpenAICompatProvider("m").complete(ITEM, 1, {"reasoning_effort": "none", "max_tokens": 8})
    assert seen["payload"]["reasoning_effort"] == "none"
    assert "reasoning" not in seen["payload"]


def test_openrouter_nests_reasoning_effort(monkeypatch):
    seen = _capture(monkeypatch, OpenRouterProvider, "OPENROUTER_API_KEY")
    OpenRouterProvider("m").complete(ITEM, 1, {"reasoning_effort": "minimal"})
    assert seen["payload"]["reasoning"] == {"effort": "minimal"}
    assert "reasoning_effort" not in seen["payload"]


def test_absent_param_sends_nothing(monkeypatch):
    seen = _capture(monkeypatch, OpenRouterProvider, "OPENROUTER_API_KEY")
    OpenRouterProvider("m").complete(ITEM, 1, {"temperature": 0})
    assert "reasoning" not in seen["payload"]
    assert "reasoning_effort" not in seen["payload"]


def _param_schemas(node):
    """Every `properties` block that declares reasoning_effort, wherever it sits."""
    if isinstance(node, dict):
        props = node.get("properties")
        if isinstance(props, dict) and "reasoning_effort" in props:
            yield props["reasoning_effort"]
        for v in node.values():
            yield from _param_schemas(v)
    elif isinstance(node, list):
        for v in node:
            yield from _param_schemas(v)


@pytest.mark.parametrize("effort,ok", [("none", True), ("high", True), ("lots", False)])
def test_schema_pins_the_enum(effort, ok):
    schema = json.loads((SCHEMA_DIR / "eval.schema.json").read_text(encoding="utf-8"))
    found = list(_param_schemas(schema))
    assert len(found) == 1, "declared once, on the model params"
    errors = list(Draft202012Validator(found[0]).iter_errors(effort))
    assert (not errors) is ok
