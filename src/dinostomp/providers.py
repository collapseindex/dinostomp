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
# A rate limit is the upstream asking for time, not a fault to retry at once.
# It gets its own budget: more attempts, and a wait that doubles from
# RATE_LIMIT_WAIT_S up to RATE_LIMIT_WAIT_MAX_S. Sized from GPT-5.6 Luna on
# OpenRouter, 2026-09-18, which answered 429 for tens of seconds at a time and
# stopped a run every seven records under the 2s/4s server-error backoff.
RATE_LIMIT_STATUSES = {429, 529}
RATE_LIMIT_RETRIES = 8
RATE_LIMIT_WAIT_S = 5
RATE_LIMIT_WAIT_MAX_S = 120
MAX_ERROR_CHARS = 300
# Error codes worth another attempt when they arrive inside a 200 body.
RETRYABLE_BODY_CODES = {408, 409, 425, 429, 500, 502, 503, 504, 520, 521, 522, 523, 524, 529}
# 52x are Cloudflare-side failures in front of a provider; an OpenRouter
# decisions call returned 520 mid-fleet on 2026-09-18 and stopped the run.
RETRY_STATUSES = {408, 429, 500, 502, 503, 504, 520, 521, 522, 523, 524, 529}

ENV_KEYS = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "jev": "OPENROUTER_API_KEY",
    "typesafe": "TYPESAFE_API_KEY",
}


class ProviderError(RuntimeError):
    """A call that failed after retries. Message never contains credentials.

    `retryable` marks failures worth another attempt (a rate limit, an
    overloaded upstream). Set by the caller that knows, read by the retry
    loop in HttpProvider._request.
    """

    def __init__(self, message: str, *, retryable: bool = False, rate_limited: bool = False):
        super().__init__(message)
        self.retryable = retryable
        self.rate_limited = rate_limited


def raise_for_error_body(data: Any, provider_name: str) -> None:
    """Refuse a 200 that carries an error OBJECT instead of a completion.

    Providers behind a gateway answer 200 with `{"error": {"code": 429, ...}}`
    and no `choices` when an upstream model is rate-limited or overloaded.
    Parsed as a completion that is indistinguishable from an empty answer: the
    scorer records a wrong answer, the ledger records zero tokens and zero
    cost, and the model's reported accuracy becomes the provider's
    availability. The status-code retry never sees it, because the status is
    200 (D-099).
    """
    if not isinstance(data, dict):
        return
    err = data.get("error")
    if not err:
        return
    if isinstance(err, dict):
        code = err.get("code")
        message = str(err.get("message") or err)[:MAX_ERROR_CHARS]
    else:
        code, message = None, str(err)[:MAX_ERROR_CHARS]
    try:
        code = int(code)
    except (TypeError, ValueError):
        code = None
    raise ProviderError(
        f"{provider_name} returned an error body with HTTP 200: {code or 'no code'}: {message}",
        retryable=code in RETRYABLE_BODY_CODES, rate_limited=code in RATE_LIMIT_STATUSES)


def backoff_s(attempt: int, rate_limited: bool) -> float:
    """Seconds to wait before attempt+1. A server error waits 2s, 4s; a rate
    limit waits 5s, 10s, 20s ... capped, because the limit is on the clock."""
    if rate_limited:
        return min(RATE_LIMIT_WAIT_S * 2 ** (attempt - 1), RATE_LIMIT_WAIT_MAX_S)
    return 2.0 * attempt


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
    # True for providers that take the item's `choices` as the request itself:
    # the runner then renders no option block and permutes the menu, not the
    # prompt, under the shuffle probe.
    takes_choices: bool = False

    def __init__(self, model: str):
        self.model = model
        env = ENV_KEYS[self.provider_name]
        self.key = os.environ.get(env, "")
        if not self.key:
            raise ProviderError(f"{env} is not set; refusing to run {self.provider_name}")

    def _request(self, url: str, headers: dict, payload: dict) -> dict:
        body = json.dumps(payload).encode("utf-8")
        last = "no attempt made"
        attempt = 0
        budget = RETRIES
        while attempt < budget:
            attempt += 1
            rate_limited = False
            req = urllib.request.Request(url, data=body, headers=headers, method="POST")
            try:
                with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
                    text = resp.read().decode("utf-8", "replace")
                try:
                    data = json.loads(text)
                except json.JSONDecodeError:
                    # A proxy/CDN returning HTML with status 200 must be a clean
                    # ProviderError, not a traceback after spend.
                    raise ProviderError(
                        f"{self.provider_name} returned a non-JSON body (starts {text[:80]!r})"
                    ) from None
                try:
                    raise_for_error_body(data, self.provider_name)
                except ProviderError as exc:
                    if not exc.retryable:
                        raise
                    last = str(exc)
                    rate_limited = exc.rate_limited
                else:
                    return data
            except urllib.error.HTTPError as exc:
                detail = ""
                try:
                    detail = exc.read().decode("utf-8", "replace")[:300]
                except OSError:
                    pass
                last = f"HTTP {exc.code}: {detail}"
                if exc.code not in RETRY_STATUSES:
                    break
                rate_limited = exc.code in RATE_LIMIT_STATUSES
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                last = f"network error: {exc}"
            if rate_limited:
                budget = RATE_LIMIT_RETRIES
            if attempt < budget:
                time.sleep(backoff_s(attempt, rate_limited))
        raise ProviderError(f"{self.provider_name} call failed after {attempt} attempt(s): {last}")


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

    @staticmethod
    def _set_reasoning(payload: dict, effort: str) -> None:
        """How much hidden reasoning a reasoning model may spend before it
        answers. Without a cap a one-word answer can spend the whole
        max_tokens on reasoning and return an empty string with
        finish_reason=length, billed in full (D-098). OpenAI's field is
        top-level; OpenRouter nests it, see the subclass."""
        payload["reasoning_effort"] = effort

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
        if "reasoning_effort" in params:
            self._set_reasoning(payload, str(params["reasoning_effort"]))
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

    @staticmethod
    def _set_reasoning(payload: dict, effort: str) -> None:
        payload["reasoning"] = {"effort": effort}


class DecisionsProvider(HttpProvider):
    """TypeSafe's Jev through OpenRouter's decisions endpoint: a System One model.

    The item's `choices` ARE the request. No prompt is rendered, no text comes
    back, nothing is parsed: the answer is one of the choices by name, with a
    probability per choice and a confidence, which ride in the record's
    trajectory as evidence. Option texts come from `metadata.options` when the
    item carries one for every choice, otherwise the choice string itself is
    the criterion. The blind probe still blanks `input`, which is the state.

    Cost is what the endpoint reports, handed to the ledger as target-reported.
    """

    provider_name = "jev"
    URL = "https://openrouter.ai/api/alpha/decisions"
    takes_choices = True
    QUESTION_KEY = "decision"
    DEFAULT_INSTRUCTIONS = "Choose the one option that answers the state."
    # `params.question: noul` asks a yes/no question of the state instead of a
    # choice over the menu. The answer is a probability of yes; the record's
    # output is a label so any scorer can read it, and the probability rides in
    # the trajectory as a two-way distribution so R23/R24 read it unchanged.
    NOUL_LABELS = ("yes", "no")
    NOUL_THRESHOLD = 0.5

    def complete(self, item: dict, seed: int, params: dict) -> Completion:
        if str(params.get("question") or "choice") == "noul":
            return self._noul(item, params)
        choices = item.get("choices")
        if not isinstance(choices, list) or len(choices) < 2:
            raise ProviderError(f"{self.provider_name} needs an item with at least two choices: {item.get('id')!r}")
        options = (item.get("metadata") or {}).get("options")
        if isinstance(options, dict) and all(c in options for c in choices):
            criteria = {str(c): str(options[c]) for c in choices}
        else:
            criteria = {str(c): str(c) for c in choices}
        state = item["input"] if isinstance(item["input"], (str, dict, list)) else str(item["input"])
        payload: dict[str, Any] = {
            "model": self.model,
            "state": state,
            "questions": {self.QUESTION_KEY: {
                "type": "choice",
                "instructions": str(params.get("instructions") or self.DEFAULT_INSTRUCTIONS),
                "criteria": criteria,
            }},
        }
        data = self._request(self.URL, self._headers(), payload)
        try:
            answer = data["answers"][self.QUESTION_KEY]
            choice = str(answer["choice"])
            probabilities = {str(k): float(v) for k, v in (answer.get("probabilities") or {}).items()}
            confidence = float(answer.get("confidence") or 0.0)
            usage = data.get("usage") or {}
            cost = usage.get("cost")
        except (TypeError, AttributeError, ValueError, KeyError) as exc:
            raise ProviderError(f"{self.provider_name} response had an unexpected shape: {exc}") from exc
        evidence = {"top": choice, "p_top": round(probabilities.get(choice, 0.0), 6),
                    "p_target": round(probabilities.get(str(item.get("target")), 0.0), 6),
                    "confidence": round(confidence, 6),
                    "distribution": {k: round(v, 6) for k, v in probabilities.items()}}
        return Completion(
            text=choice,
            finish_reason="stop",
            input_tokens=int(usage.get("input_tokens") or 0),
            output_tokens=int(usage.get("output_tokens") or 0),
            raw_usage=usage,
            model_reported=str(data.get("model") or ""),
            cost_usd=float(cost) if cost is not None else None,
            trajectory=[{"tool": "decisions.choice",
                         "args": {"n_options": len(criteria), "question": self.QUESTION_KEY},
                         "result": json.dumps(evidence, ensure_ascii=False), "ok": True}],
        )

    def _headers(self) -> dict:
        return {"content-type": "application/json", "authorization": f"Bearer {self.key}"}

    def _noul(self, item: dict, params: dict) -> Completion:
        """A yes/no question over the state. `params.instructions` is the
        question, `params.criteria` optionally says what true and false mean,
        `params.labels` names the two outputs (default yes/no), first is true."""
        labels = params.get("labels") or list(self.NOUL_LABELS)
        if not isinstance(labels, list) or len(labels) != 2:
            raise ProviderError(f"{self.provider_name} noul labels must be two strings, got {labels!r}")
        yes, no = str(labels[0]), str(labels[1])
        question: dict[str, Any] = {"type": "noul",
                                    "instructions": str(params.get("instructions") or "Is this true?")}
        criteria = params.get("criteria")
        if isinstance(criteria, dict):
            question["criteria"] = {str(k): str(v) for k, v in criteria.items()}
        state = item["input"] if isinstance(item["input"], (str, dict, list)) else str(item["input"])
        payload = {"model": self.model, "state": state, "questions": {self.QUESTION_KEY: question}}
        data = self._request(self.URL, self._headers(), payload)
        try:
            p_true = float(data["answers"][self.QUESTION_KEY]["noul"])
            usage = data.get("usage") or {}
            cost = usage.get("cost")
        except (TypeError, AttributeError, ValueError, KeyError) as exc:
            raise ProviderError(f"{self.provider_name} response had an unexpected shape: {exc}") from exc
        if not 0.0 <= p_true <= 1.0:
            raise ProviderError(f"{self.provider_name} returned a noul outside [0, 1]: {p_true}")
        label = yes if p_true >= self.NOUL_THRESHOLD else no
        evidence = {"top": label, "p_true": round(p_true, 6), "p_top": round(max(p_true, 1 - p_true), 6),
                    "distribution": {yes: round(p_true, 6), no: round(1 - p_true, 6)}}
        return Completion(
            text=label,
            finish_reason="stop",
            input_tokens=int(usage.get("input_tokens") or 0),
            output_tokens=int(usage.get("output_tokens") or 0),
            raw_usage=usage,
            model_reported=str(data.get("model") or ""),
            cost_usd=float(cost) if cost is not None else None,
            trajectory=[{"tool": "decisions.noul", "args": {"question": self.QUESTION_KEY},
                         "result": json.dumps(evidence, ensure_ascii=False), "ok": True}],
        )


class TypeSafeProvider(DecisionsProvider):
    """The same decisions call on TypeSafe's own endpoint, `POST /v1/systemone`.

    Identical request and answer shape to the OpenRouter path (which is where
    OpenRouter's alpha endpoint got it), so one class does both and the record
    says which door was used: `provider: jev` is the middleman, `typesafe` is
    direct. The endpoint reports tokens but no cost, so the ledger prices the
    call from the spec's rates like any other provider. Model `jev-latest` is
    TypeSafe's own name for the current Jev; `model_reported` on the manifest
    records what actually answered.
    """

    provider_name = "typesafe"
    URL = "https://api.typesafe.ai/v1/systemone"


# The same model behind two doors. A spec that names one door runs on the
# other when only the other's key is set, so a pod with a Jev arm or a Jev
# judge is runnable by anyone holding either key. The door actually used is
# what the manifest and every record say (`provider`), the spec's model name
# stays as the arm's identity, and `model_reported` carries what answered.
# Neither key: refused, naming both.
DOORS = {"typesafe": "jev", "jev": "typesafe"}
DOOR_MODELS = {"jev-latest": "typesafe/jev-1.13", "typesafe/jev-1.13": "jev-latest"}


def resolve_door(provider: str, model: str) -> tuple[str, str, str | None]:
    """(provider, model, note): the door to use given the keys in the
    environment. The note is one line for the log when the door changed."""
    other = DOORS.get(provider)
    if other is None or os.environ.get(ENV_KEYS[provider]):
        return provider, model, None
    if not os.environ.get(ENV_KEYS[other]):
        raise ProviderError(f"{ENV_KEYS[provider]} is not set and neither is {ENV_KEYS[other]}; "
                            f"{provider} needs one door to Jev open. Refusing to run {provider}")
    swapped = DOOR_MODELS.get(model, model)
    return other, swapped, (f"{provider}: {ENV_KEYS[provider]} is not set; using the {other} door for "
                            f"the same model ({model} -> {swapped}). The record says {other}")


PROVIDERS = {
    "dry": DryProvider,
    "anthropic": AnthropicProvider,
    "openai": OpenAICompatProvider,
    "openrouter": OpenRouterProvider,
    "jev": DecisionsProvider,
    "typesafe": TypeSafeProvider,
}

# Providers whose calls cost nothing the ledger has to price. `python` targets
# may still report their OWN spend (an agent calling a paid API inside itself);
# that number is target-reported and the manifest labels it as such.
ZERO_RATE_PROVIDERS = frozenset({"dry", "python", "mediated"})


def make_provider(provider: str, model: str, **kw):
    """Build an examinee. Extra kwargs are provider-specific (`python` targets
    need `entrypoint` and `base_dir`); the two-argument call still works, which
    is what keeps every existing provider_factory stub valid.

    A Jev door with no key falls back to the other door (see `resolve_door`);
    the returned object's `provider_name` is the door in use and `door_note`
    is the line to log, or None."""
    provider, model, note = resolve_door(provider, model)
    if note:
        print(note)
    if provider == "python":
        from dinostomp.targets import PythonTarget  # local: targets imports Completion from here

        entrypoint = kw.get("entrypoint")
        if not entrypoint:
            raise ProviderError("a python target requires an entrypoint (e.g. agent.py:run)")
        return PythonTarget(model, entrypoint, kw.get("base_dir") or Path("."))
    if provider == "mediated":
        entrypoint = kw.get("entrypoint")
        if not entrypoint:
            raise ProviderError("a mediated agent requires an entrypoint (e.g. agent.py:answer)")
        shared = dict(tools=kw.get("tools"), forbidden=kw.get("forbidden"),
                      max_steps=kw.get("max_steps"), ablate=bool(kw.get("ablate")))
        base = kw.get("base_dir") or Path(".")
        if kw.get("timeout_fault") and (kw.get("isolation") or {}).get("mode") == "subprocess":
            raise ProviderError("the timeout probe runs in-process for now: a subprocess agent reaches "
                                "its tools across a message boundary that does not yet carry a timeout")
        if (kw.get("isolation") or {}).get("mode") == "subprocess":
            from dinostomp.sandbox import SandboxedTarget  # local: imports Completion from here

            return SandboxedTarget(model, entrypoint, base,
                                   timeout_s=(kw.get("isolation") or {}).get("timeout_s"),
                                   **shared)
        from dinostomp.harness import MediatedTarget  # local: imports Completion from here

        return MediatedTarget(model, entrypoint, base, timeout_fault=bool(kw.get("timeout_fault")), **shared)
    if provider not in PROVIDERS:
        raise ProviderError(f"unknown provider: {provider!r}")
    return PROVIDERS[provider](model)
