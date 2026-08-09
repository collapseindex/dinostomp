"""The target rail: evaluate a bounded execution, not just a model completion.

A target is a pod-local Python callable that answers an item however it likes:
one API call, a RAG pipeline, a tool-using agent, a whole workflow. It mounts on
the SAME interface the network providers use, so everything downstream applies
unchanged: the witness gate, the budget cap, the streamed ledger, the drift
boundary, and the entire stomp battery.

    # agent.py, inside the pod
    def run(item: dict, ctx: dict) -> dict:
        hits = retrieve(item["input"])
        return {
            "output": answer(hits),
            "trajectory": [
                {"tool": "retrieve", "args": {"q": item["input"]}, "result": hits[0], "ok": True},
            ],
        }

`ctx` carries `model`, `seed`, and `params`, so one entrypoint can serve a fleet
of configurations (that is how a pod runs `agent-careful` against `agent-sloppy`
without duplicating code).

The entrypoint file is hashed into every manifest exactly like a custom scorer,
so editing the agent after a run is drift and the battery says so.

TRUST BOUNDARY, stated once here and repeated in the docs and the report:

    The trajectory is SELF-REPORTED by the target. dinostomp verifies the
    RECORD, not the EXECUTION.

A target that simply omits a tool call from its trace cannot be caught by
reading the trace. That is not a bug to be fixed by trying harder at parsing; it
is a property of self-report, and pretending otherwise would be the exact
flattering-instrument failure this project exists to catch. What the battery can
do is make under-reporting visible as a fleet-relative anomaly: T5 flags a model
whose trajectories are far emptier than its peers', the same way R12 flags a
model that escapes the scorer. Treat a trajectory as an examinee's testimony
that other examinees can contradict, never as an execution log.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

from dinostomp.providers import Completion, ProviderError

# One runaway tool result must not bloat every ledger line on an 8GB laptop.
# Truncation is recorded on the step, never silent.
MAX_RESULT_CHARS = 4000
MAX_STEPS_RECORDED = 200

# Keys a step may carry into the record. Anything else the target invents is
# dropped rather than written, so the record schema stays the contract.
STEP_KEYS = ("tool", "args", "result", "ok")

DEFAULT_SYMBOL = "run"


def split_entrypoint(entrypoint: str, default_symbol: str = DEFAULT_SYMBOL) -> tuple[str, str]:
    """`agent.py:run` -> ("agent.py", "run"). A bare path takes the default.

    The mediated rail passes its own default (`answer`), because the two rails
    take different signatures and a pod that lands on the wrong one should fail
    to import rather than be called with the wrong number of arguments.
    """
    raw = str(entrypoint)
    if ":" in raw:
        path, _, symbol = raw.rpartition(":")
        return path, (symbol or default_symbol)
    return raw, default_symbol


def load_target(entrypoint: str, base_dir: Path, default_symbol: str = DEFAULT_SYMBOL):
    """Import the pod-local callable. Path traversal is rejected by the spec
    cross-checks before this is ever reached."""
    rel, symbol = split_entrypoint(entrypoint, default_symbol)
    path = Path(base_dir) / rel
    spec = importlib.util.spec_from_file_location("dinostomp_user_target", path)
    if spec is None or spec.loader is None:
        raise ProviderError(f"cannot load target module: {path}")
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as exc:  # noqa: BLE001 - user code, reported not swallowed
        raise ProviderError(f"target module {rel} failed to import: {type(exc).__name__}: {exc}") from exc
    fn = getattr(module, symbol, None)
    if not callable(fn):
        raise ProviderError(f"{rel} must define {symbol}(...)")
    return fn


def normalize_step(raw: Any) -> dict:
    """One trajectory step, coerced into the recorded shape.

    Deliberately does NOT repair a malformed step. A step with no tool name is
    written with an empty tool name so T3 can flag it; inventing a plausible
    name here would hide the defect the check exists to find.
    """
    if not isinstance(raw, dict):
        return {"tool": "", "result": str(raw)[:MAX_RESULT_CHARS]}
    step: dict[str, Any] = {}
    for key in STEP_KEYS:
        if key not in raw:
            continue
        value = raw[key]
        if key == "tool":
            step["tool"] = value if isinstance(value, str) else ""
        elif key == "args":
            step["args"] = value if isinstance(value, dict) else {"_raw": str(value)[:200]}
        elif key == "result":
            text = value if isinstance(value, str) else str(value)
            if len(text) > MAX_RESULT_CHARS:
                step["result"] = text[:MAX_RESULT_CHARS]
                step["result_truncated"] = True
            else:
                step["result"] = text
        elif key == "ok":
            step["ok"] = bool(value)
    step.setdefault("tool", "")
    return step


def normalize_trajectory(raw: Any) -> list[dict]:
    """A target's self-reported trace, coerced to a list of recorded steps."""
    if raw is None:
        return []
    if not isinstance(raw, (list, tuple)):
        return [normalize_step(raw)]
    return [normalize_step(s) for s in list(raw)[:MAX_STEPS_RECORDED]]


def to_completion(raw: Any, model: str) -> Completion:
    """Adapt whatever the target returned into the provider rail's Completion."""
    if isinstance(raw, str):
        return Completion(text=raw, model_reported=model, raw_usage={"target": True})
    if not isinstance(raw, dict):
        raise ProviderError(
            f"target returned {type(raw).__name__}; expected a string or a dict with an 'output' key"
        )
    if "output" not in raw:
        raise ProviderError("target returned a dict with no 'output' key")
    text = raw["output"]
    if not isinstance(text, str):
        raise ProviderError(f"target 'output' must be a string, got {type(text).__name__}")

    cost = raw.get("cost_usd")
    if cost is not None:
        try:
            cost = float(cost)
        except (TypeError, ValueError):
            raise ProviderError(f"target 'cost_usd' must be a number, got {cost!r}") from None
        if cost < 0:
            raise ProviderError("target reported a negative cost_usd")

    def count(key: str, fallback: int) -> int:
        try:
            return max(0, int(raw[key]))
        except (KeyError, TypeError, ValueError):
            return fallback

    return Completion(
        text=text,
        finish_reason=str(raw.get("finish_reason") or "stop"),
        input_tokens=count("input_tokens", 0),
        output_tokens=count("output_tokens", 0),
        raw_usage={"target": True, **(raw.get("usage") or {})},
        model_reported=str(raw.get("model_reported") or model),
        trajectory=normalize_trajectory(raw.get("trajectory")),
        cost_usd=cost,
    )


class PythonTarget:
    """A pod-local callable, mounted as an examinee on the provider rail."""

    provider_name = "python"

    def __init__(self, model: str, entrypoint: str, base_dir: Path):
        self.model = model
        self.entrypoint = entrypoint
        self.fn = load_target(entrypoint, base_dir)

    def complete(self, item: dict, seed: int, params: dict) -> Completion:
        ctx = {"model": self.model, "seed": seed, "params": dict(params or {})}
        try:
            raw = self.fn(item, ctx)
        except Exception as exc:  # noqa: BLE001 - user code; stop the run cleanly
            # A broken target is not a scoring event: it must never be banked as
            # a wrong answer. ProviderError stops the run with everything paid
            # for so far already on disk and resumable.
            raise ProviderError(
                f"target {self.entrypoint!r} raised {type(exc).__name__}: {exc}"
            ) from exc
        return to_completion(raw, self.model)
