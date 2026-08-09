"""Model providers.

`dry` is the load-bearing one: a deterministic offline examinee that needs no
network and no key, so every eval runs end to end at zero cost. Its skill is
derived from the model name hash, so a fleet of dry models gives the lint
battery strong and weak examinees to correlate against (the same trick the
benchmark-checker witness generator uses).

Network providers read keys from environment variables only. Keys are never
stored, never logged, and never appear in error messages.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


TIMEOUT_S = 60
DEFAULT_MAX_TOKENS = 1024
RETRIES = 3
RETRY_STATUSES = {429, 500, 502, 503, 529}

ENV_KEYS = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
}


class ProviderError(RuntimeError):
    """A call that failed after retries. Message never contains credentials."""


@dataclass
class Completion:
    text: str
    finish_reason: str = "stop"
    input_tokens: int = 0
    output_tokens: int = 0
    raw_usage: dict = field(default_factory=dict)
    # What the provider SAYS answered, verbatim. Hosted aliases move; the
    # manifest records the identifier actually returned, not just the one asked for.
    model_reported: str = ""
    # Self-reported execution trace, for targets that do more than one call
    # (agents, RAG pipelines, workflows). Empty for plain completion providers.
    # See the TRUST BOUNDARY note in targets.py: this is testimony, not a log.
    trajectory: list[dict] = field(default_factory=list)
    # Set only by targets that spend money the ledger cannot price from tokens.
    # None means "price me from tokens and the rate table" (the normal path).
    cost_usd: float | None = None


def _as_messages(item_input: Any) -> tuple[str | None, list[dict]]:
    """Normalize an item's input into (system, messages).

    Multiple system messages are joined in order; dropping any of them would
    silently change the experiment.
    """
    if isinstance(item_input, str):
        return None, [{"role": "user", "content": item_input}]
    system_parts = []
    messages = []
    for m in item_input:
        if m["role"] == "system":
            system_parts.append(m["content"])
        else:
            messages.append({"role": m["role"], "content": m["content"]})
    return ("\n\n".join(system_parts) or None), messages


def _unit(key: str) -> float:
    """Deterministic hash in [0, 1)."""
    return int(hashlib.sha256(key.encode()).hexdigest()[:8], 16) / 0xFFFFFFFF


class DryProvider:
    """Deterministic offline examinee. Zero network, zero spend.

    Correctness is skill (from the model-name hash) vs item difficulty (from
    the item-id hash) plus a small per-pair jitter: strong models beat weak
    ones consistently and easy items are easy for everyone. A fleet of dry
    models therefore has real psychometric structure (reliability, positive
    discrimination) for the stomp battery to measure. Wrong answers are
    deterministic per (model, item), so unanimity checks see realistic
    disagreement instead of identical mistakes.
    """

    SKILL_LO, SKILL_SPAN = 0.35, 0.60
    DIFF_LO, DIFF_SPAN = 0.05, 0.85
    JITTER = 0.16

    def __init__(self, model: str):
        self.model = model
        self.skill = self.SKILL_LO + self.SKILL_SPAN * _unit(f"skill|{model}")

    def complete(self, item: dict, seed: int, params: dict) -> Completion:
        iid = str(item["id"])
        difficulty = self.DIFF_LO + self.DIFF_SPAN * _unit(f"difficulty|{iid}")
        jitter = (_unit(f"jitter|{self.model}|{seed}|{iid}") - 0.5) * self.JITTER
        target = item["target"]
        first = str(target[0] if isinstance(target, list) else target)
        if self.skill + jitter > difficulty:
            text = first
        else:
            k = int(_unit(f"wrong|{self.model}|{iid}") * 1_000_000)
            try:
                text = str(int(float(first)) + 1 + k % 7)
            except ValueError:
                text = ("not", "hardly", "unlikely")[k % 3] + " " + first
        prompt = item["input"] if isinstance(item["input"], str) else json.dumps(item["input"])
        return Completion(
            text=text,
            finish_reason="stop",
            input_tokens=max(1, len(prompt) // 4),
            output_tokens=max(1, len(text) // 4),
            raw_usage={"dry": True},
            model_reported=self.model,
        )


class HttpProvider:
    """Shared plumbing for the JSON-over-HTTPS providers."""

    provider_name: str = ""

    def __init__(self, model: str):
        self.model = model
        env = ENV_KEYS[self.provider_name]
        self.key = os.environ.get(env, "")
        if not self.key:
            raise ProviderError(f"{env} is not set; refusing to run {self.provider_name}")

    def _request(self, url: str, headers: dict, payload: dict) -> dict:
        body = json.dumps(payload).encode("utf-8")
        last = "no attempt made"
        for attempt in range(1, RETRIES + 1):
            req = urllib.request.Request(url, data=body, headers=headers, method="POST")
            try:
                with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
                    text = resp.read().decode("utf-8", "replace")
                try:
                    return json.loads(text)
                except json.JSONDecodeError:
                    # A proxy/CDN returning HTML with status 200 must be a clean
                    # ProviderError, not a traceback after spend.
                    raise ProviderError(
                        f"{self.provider_name} returned a non-JSON body (starts {text[:80]!r})"
                    ) from None
            except urllib.error.HTTPError as exc:
                detail = ""
                try:
                    detail = exc.read().decode("utf-8", "replace")[:300]
                except OSError:
                    pass
                last = f"HTTP {exc.code}: {detail}"
                if exc.code not in RETRY_STATUSES:
                    break
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                last = f"network error: {exc}"
            if attempt < RETRIES:
                time.sleep(2 * attempt)
        raise ProviderError(f"{self.provider_name} call failed after {RETRIES} attempt(s): {last}")


class AnthropicProvider(HttpProvider):
    provider_name = "anthropic"
    URL = "https://api.anthropic.com/v1/messages"

    def complete(self, item: dict, seed: int, params: dict) -> Completion:
        system, messages = _as_messages(item["input"])
        payload: dict[str, Any] = {
            "model": self.model,
            "max_tokens": int(params.get("max_tokens", DEFAULT_MAX_TOKENS)),
            "messages": messages,
        }
        if system:
            payload["system"] = system
        if "temperature" in params:
            payload["temperature"] = params["temperature"]
        headers = {
            "content-type": "application/json",
            "x-api-key": self.key,
            "anthropic-version": "2023-06-01",
        }
        data = self._request(self.URL, headers, payload)
        try:
            text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
            usage = data.get("usage", {}) or {}
            return Completion(
                text=text,
                finish_reason=data.get("stop_reason") or "stop",
                input_tokens=int(usage.get("input_tokens") or 0),
                output_tokens=int(usage.get("output_tokens") or 0),
                raw_usage=usage,
                model_reported=str(data.get("model") or ""),
            )
        except (TypeError, AttributeError, ValueError) as exc:
            raise ProviderError(f"anthropic response had an unexpected shape: {exc}") from exc


class OpenAICompatProvider(HttpProvider):
    provider_name = "openai"
    URL = "https://api.openai.com/v1/chat/completions"

    def complete(self, item: dict, seed: int, params: dict) -> Completion:
        system, messages = _as_messages(item["input"])
        if system:
            messages = [{"role": "system", "content": system}, *messages]
        payload: dict[str, Any] = {
            "model": self.model,
            "max_tokens": int(params.get("max_tokens", DEFAULT_MAX_TOKENS)),
            "messages": messages,
        }
        if "temperature" in params:
            payload["temperature"] = params["temperature"]
        headers = {"content-type": "application/json", "authorization": f"Bearer {self.key}"}
        data = self._request(self.URL, headers, payload)
        try:
            choice = (data.get("choices") or [{}])[0]
            usage = data.get("usage", {}) or {}
            return Completion(
                text=(choice.get("message") or {}).get("content") or "",
                finish_reason=choice.get("finish_reason") or "stop",
                input_tokens=int(usage.get("prompt_tokens") or 0),
                output_tokens=int(usage.get("completion_tokens") or 0),
                raw_usage=usage,
                model_reported=str(data.get("model") or ""),
            )
        except (TypeError, AttributeError, ValueError, IndexError) as exc:
            raise ProviderError(f"{self.provider_name} response had an unexpected shape: {exc}") from exc


class OpenRouterProvider(OpenAICompatProvider):
    provider_name = "openrouter"
    URL = "https://openrouter.ai/api/v1/chat/completions"


PROVIDERS = {
    "dry": DryProvider,
    "anthropic": AnthropicProvider,
    "openai": OpenAICompatProvider,
    "openrouter": OpenRouterProvider,
}

# Providers whose calls cost nothing the ledger has to price. `python` targets
# may still report their OWN spend (an agent calling a paid API inside itself);
# that number is target-reported and the manifest labels it as such.
ZERO_RATE_PROVIDERS = frozenset({"dry", "python"})


def make_provider(provider: str, model: str, **kw):
    """Build an examinee. Extra kwargs are provider-specific (`python` targets
    need `entrypoint` and `base_dir`); the two-argument call still works, which
    is what keeps every existing provider_factory stub valid."""
    if provider == "python":
        from dinostomp.targets import PythonTarget  # local: targets imports Completion from here

        entrypoint = kw.get("entrypoint")
        if not entrypoint:
            raise ProviderError("a python target requires an entrypoint (e.g. agent.py:run)")
        return PythonTarget(model, entrypoint, kw.get("base_dir") or Path("."))
    if provider not in PROVIDERS:
        raise ProviderError(f"unknown provider: {provider!r}")
    return PROVIDERS[provider](model)
