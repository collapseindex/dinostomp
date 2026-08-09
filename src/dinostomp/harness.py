"""The mediated rail: a trace the HARNESS observed, not one the agent testified to.

Every other target in this repository writes its own trajectory. That is a
self-report, and the trust boundary in `targets.py` says so plainly: an agent
that omits a call from its trace cannot be caught by reading the trace. Six
checks (T1 to T6) read that trace, and all six are therefore reading testimony.

Here the harness owns the tools. The agent never touches a tool function; it is
handed a `Tools` object and every call goes through it, so the recorded
trajectory is a log of what happened rather than a claim about it:

    # agent.py, inside the pod
    def answer(item, tools, ctx):
        hit = tools.retrieve(key="photosynthesis")   # recorded by the harness
        return f"The answer is {hit}"

The three-argument signature is the tell. `run(item, ctx)` is the self-reported
rail; `answer(item, tools, ctx)` is this one, and a pod cannot be on both by
accident.

WHAT THIS IS NOT, stated first because the name people reach for is "sandbox":

    This is NOT a security boundary. The agent is ordinary Python running
    in-process, and nothing here stops it importing `os`, opening a socket,
    reading your environment, or monkeypatching this module.

Calling it a sandbox would be the exact flattering-instrument failure this
project exists to catch, so it is called `mediated` instead, and the report
labels traces `harness_observed` rather than `sandboxed`. What mediation buys is
narrower and real:

  - **the trace is observed.** T1, T2, T3 and T6 stop reading testimony. T5,
    which exists only as a fleet-relative proxy for under-reporting, becomes
    unnecessary for a mediated run and says so.
  - **policy is enforced at call time.** A forbidden tool is DENIED when the
    agent reaches for it, not noticed afterwards in an audit. The attempt is
    recorded either way, so a denial is evidence rather than a silent block.
  - **evidence can be withheld.** `--probe ablate` re-runs each item with every
    tool result replaced by a marker. An answer that does not change when its
    evidence is taken away did not causally depend on that evidence, which is
    the question T4 could never ask (D-020) and T7 now can.

Real isolation needs a subprocess with a sanitised environment and a denied
network, and tools crossing an IPC boundary. That is a bigger change and it is
not pretended here.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any, Callable

from dinostomp.providers import Completion, ProviderError
from dinostomp.targets import MAX_RESULT_CHARS, MAX_STEPS_RECORDED, load_target, split_entrypoint

# What an ablated tool returns in place of its real result. Deliberately inert
# and obviously not an answer: if an agent echoes this string, the echo shows up
# in the output and is visible rather than being mistaken for evidence.
WITHHELD = "(evidence withheld by the ablation probe)"

DEFAULT_SYMBOL = "answer"


class ToolDenied(RuntimeError):
    """Raised into the agent when policy refuses a call.

    Raised rather than returned, so an agent cannot mistake a denial for an
    empty result and quietly carry on. The attempt is recorded before this is
    raised: a denied call is evidence about the agent, and dropping it would
    hide the very behaviour the policy exists to catch.
    """


class Tools:
    """The only way an agent reaches a tool. Every call lands in `steps`.

    Attribute access is sugar for `call`: `tools.retrieve(key=...)` and
    `tools.call("retrieve", key=...)` record identically, so a pod cannot get a
    different trace by preferring one spelling.
    """

    def __init__(self, registry: dict[str, Callable], *, forbidden: set[str] | None = None,
                 max_steps: int | None = None, ablate: bool = False):
        self._registry = dict(registry)
        self._forbidden = set(forbidden or ())
        self._max_steps = max_steps
        self._ablate = bool(ablate)
        self.steps: list[dict] = []

    @property
    def ablated(self) -> bool:
        """True when results are being withheld. Exposed so an agent CAN know,
        and so a pod that changes behaviour on it is doing something visible
        rather than something clever."""
        return self._ablate

    def available(self) -> list[str]:
        return sorted(n for n in self._registry if n not in self._forbidden)

    def _record(self, name: str, args: dict, result: Any, ok: bool, **extra) -> dict:
        text = result if isinstance(result, str) else str(result)
        step: dict[str, Any] = {"tool": name, "args": args, "ok": bool(ok)}
        if len(text) > MAX_RESULT_CHARS:
            step["result"] = text[:MAX_RESULT_CHARS]
            step["result_truncated"] = True
        else:
            step["result"] = text
        step.update(extra)
        if len(self.steps) < MAX_STEPS_RECORDED:
            self.steps.append(step)
        return step

    def call(self, name: str, **args) -> Any:
        name = str(name)
        # Order matters and is deliberate: an attempt is recorded BEFORE it is
        # refused. A policy that hides what it blocked leaves an auditor unable
        # to tell a well-behaved agent from a thwarted one.
        if name in self._forbidden:
            self._record(name, args, "denied: forbidden by policy", False, denied="forbidden")
            raise ToolDenied(f"tool {name!r} is forbidden by this pod's policy")
        if name not in self._registry:
            self._record(name, args, "denied: no such tool", False, denied="unknown")
            raise ToolDenied(f"no tool named {name!r}; available: {', '.join(self.available())}")
        if self._max_steps is not None and len(self.steps) >= self._max_steps:
            self._record(name, args, "denied: step budget exhausted", False, denied="max_steps")
            raise ToolDenied(f"this pod allows at most {self._max_steps} tool call(s)")
        if self._ablate:
            # The counterfactual. The call is real, the policy is real, the
            # RESULT is withheld, so the only thing that changed between the two
            # arms is whether the agent could see what came back.
            self._record(name, args, WITHHELD, True, ablated=True)
            return WITHHELD
        try:
            result = self._registry[name](**args)
        except Exception as exc:  # noqa: BLE001 - pod tool code, recorded not swallowed
            self._record(name, args, f"tool raised {type(exc).__name__}: {exc}", False)
            raise ProviderError(f"tool {name!r} raised {type(exc).__name__}: {exc}") from exc
        self._record(name, args, result, True)
        return result

    def __getattr__(self, name: str):
        if name.startswith("_"):
            raise AttributeError(name)

        def bound(**args):
            return self.call(name, **args)

        return bound


def load_tools(entrypoints: dict, base_dir: Path) -> dict[str, Callable]:
    """`{"retrieve": "tools.py:retrieve"}` -> `{"retrieve": <callable>}`.

    Each tool is a pod-local callable hashed into the manifest like any other
    pod code, so swapping a tool between runs is drift and the battery says so.
    """
    out: dict[str, Callable] = {}
    for name, entrypoint in (entrypoints or {}).items():
        rel, symbol = split_entrypoint(str(entrypoint))
        path = Path(base_dir) / rel
        spec = importlib.util.spec_from_file_location(f"dinostomp_tool_{name}", path)
        if spec is None or spec.loader is None:
            raise ProviderError(f"cannot load tool module: {path}")
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except Exception as exc:  # noqa: BLE001 - user code, reported not swallowed
            raise ProviderError(
                f"tool module {rel} failed to import: {type(exc).__name__}: {exc}") from exc
        fn = getattr(module, symbol, None)
        if not callable(fn):
            raise ProviderError(f"{rel} must define {symbol}(...) for tool {name!r}")
        out[str(name)] = fn
    return out


class MediatedTarget:
    """An agent mounted on the provider rail, with the harness holding the tools."""

    provider_name = "mediated"

    def __init__(self, model: str, entrypoint: str, base_dir: Path, *,
                 tools: dict | None = None, forbidden: set[str] | None = None,
                 max_steps: int | None = None, ablate: bool = False):
        self.model = model
        self.entrypoint = entrypoint
        self.fn = load_target(entrypoint, base_dir, default_symbol=DEFAULT_SYMBOL)
        self.registry = load_tools(tools or {}, base_dir)
        self.forbidden = set(forbidden or ())
        self.max_steps = max_steps
        self.ablate = bool(ablate)

    def complete(self, item: dict, seed: int, params: dict) -> Completion:
        tools = Tools(self.registry, forbidden=self.forbidden,
                      max_steps=self.max_steps, ablate=self.ablate)
        ctx = {"model": self.model, "seed": seed, "params": dict(params or {}),
               "ablated": self.ablate}
        try:
            raw = self.fn(item, tools, ctx)
        except ToolDenied as exc:
            # A denial is a RESULT, not a crash. The agent reached for something
            # the pod forbids and did not recover; that is an answer of "none"
            # with the attempt on the record, and T1 reads it from the trace.
            return Completion(
                text="", finish_reason="tool_denied", model_reported=self.model,
                raw_usage={"target": True, "denied": str(exc)},
                trajectory=list(tools.steps))
        except Exception as exc:  # noqa: BLE001 - user code; stop the run cleanly
            raise ProviderError(
                f"agent {self.entrypoint!r} raised {type(exc).__name__}: {exc}") from exc

        if isinstance(raw, str):
            text, extra = raw, {}
        elif isinstance(raw, dict):
            if "output" not in raw:
                raise ProviderError("agent returned a dict with no 'output' key")
            text, extra = raw["output"], raw
            if not isinstance(text, str):
                raise ProviderError(f"agent 'output' must be a string, got {type(text).__name__}")
        else:
            raise ProviderError(
                f"agent returned {type(raw).__name__}; expected a string or a dict with 'output'")

        if "trajectory" in extra:
            # REFUSED, not ignored. An agent on this rail returning a trajectory
            # is offering steps the harness never saw, which is the exact thing
            # mediation exists to remove; silently dropping it would leave a pod
            # author believing their trace was recorded. Stopping the run is the
            # same treatment every other attempt to invent evidence gets here.
            raise ProviderError(
                f"agent {self.entrypoint!r} returned a 'trajectory'. On the mediated rail the "
                "harness records the calls it observed, so a self-reported trace would be "
                "unverifiable evidence sitting in a record that claims to be a log. Drop the key, "
                "or use provider `python` if you want to write your own trace")

        usage: dict[str, Any] = {"target": True}

        cost = extra.get("cost_usd")
        if cost is not None:
            try:
                cost = float(cost)
            except (TypeError, ValueError):
                raise ProviderError(f"agent 'cost_usd' must be a number, got {cost!r}") from None
            if cost < 0:
                raise ProviderError("agent reported a negative cost_usd")

        return Completion(
            text=text,
            finish_reason=str(extra.get("finish_reason") or "stop"),
            input_tokens=max(0, int(extra.get("input_tokens") or 0)),
            output_tokens=max(0, int(extra.get("output_tokens") or 0)),
            raw_usage={**usage, **(extra.get("usage") or {})},
            model_reported=str(extra.get("model_reported") or self.model),
            trajectory=list(tools.steps),
            cost_usd=cost,
        )
