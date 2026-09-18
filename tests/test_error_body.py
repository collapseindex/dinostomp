"""D-099: an error object inside a 200 is a failed call, never an empty answer.

OpenRouter answers HTTP 200 with `{"error": {"code": 429, ...}}` and no
`choices` when an upstream model is rate-limited. Parsed as a completion, that
is what a wrong answer looks like: empty text, `finish_reason: stop`, zero
tokens, zero cost, and a fail on the record.
"""

import json
import urllib.error
import urllib.request
from io import BytesIO

import pytest

from dinostomp.providers import OpenRouterProvider, ProviderError, raise_for_error_body

RATE_LIMITED = {"id": "gen-1", "error": {"message": "temporarily rate-limited upstream", "code": 429,
                                          "metadata": {"error_type": "rate_limit_exceeded"}}}
BAD_REQUEST = {"error": {"message": "no endpoints found for this model", "code": 404}}
GOOD = {"choices": [{"message": {"content": "A"}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 5, "completion_tokens": 1}, "model": "m"}
ITEM = {"id": "i", "input": "Q?", "target": "A"}


def _responses(bodies, monkeypatch):
    """Serve each body in turn from urlopen, and count the calls."""
    served = []

    class FakeResponse(BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    def fake_urlopen(req, timeout=None):
        body = bodies[min(len(served), len(bodies) - 1)]
        served.append(body)
        return FakeResponse(json.dumps(body).encode())

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr("time.sleep", lambda s: None)
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    return served


def test_error_body_is_not_an_empty_answer(monkeypatch):
    _responses([RATE_LIMITED], monkeypatch)
    with pytest.raises(ProviderError) as exc:
        OpenRouterProvider("m").complete(ITEM, 1, {})
    assert "429" in str(exc.value) and "rate-limited" in str(exc.value)


def test_a_rate_limited_body_is_retried_then_succeeds(monkeypatch):
    served = _responses([RATE_LIMITED, GOOD], monkeypatch)
    completion = OpenRouterProvider("m").complete(ITEM, 1, {})
    assert completion.text == "A" and completion.input_tokens == 5
    assert len(served) == 2, "the first body was an error and must have been retried"


def test_a_permanent_error_body_does_not_burn_retries(monkeypatch):
    served = _responses([BAD_REQUEST], monkeypatch)
    with pytest.raises(ProviderError):
        OpenRouterProvider("m").complete(ITEM, 1, {})
    assert len(served) == 1, "404 in a body is not worth a second attempt"


@pytest.mark.parametrize("code,retryable", [(429, True), (529, True), (503, True), (404, False), (400, False)])
def test_retryable_classification(code, retryable):
    with pytest.raises(ProviderError) as exc:
        raise_for_error_body({"error": {"code": code, "message": "x"}}, "openrouter")
    assert exc.value.retryable is retryable


def test_a_normal_body_passes_through():
    assert raise_for_error_body(GOOD, "openrouter") is None
    assert raise_for_error_body({"error": None}, "openrouter") is None
