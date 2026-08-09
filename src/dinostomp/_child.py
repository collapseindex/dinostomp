"""The child half of `isolation: subprocess`. Runs one item, then exits.

Started as `python -I <this file>` with a sanitised environment. Reads one JSON
config line on stdin, speaks the tool protocol on stdout, and exits.

Invoked BY PATH rather than as `-m dinostomp._child`, and it imports nothing but
the standard library, because `-I` ignores PYTHONPATH: a module invocation could
not find dinostomp in a child this isolated.

Order matters here and is the whole design:

    1. capture stdout FIRST, before any pod code exists in this process
    2. deny the network
    3. only then import the agent

An agent imported before step 1 could print during import and corrupt the
protocol. An agent imported before step 2 could open a socket at module scope,
which is where a phone-home would naturally live.

`-I` runs isolated: no user site-packages, no PYTHON* variables, and the CWD is
not on `sys.path`. The pod directory is added explicitly below, so an agent
imports its own neighbours and nothing else by accident.
"""

from __future__ import annotations

import json
import sys


class _Denied(OSError):
    """Raised in place of opening a socket."""


def _deny_network() -> None:
    """Replace the socket constructor before the agent exists.

    BEST EFFORT, and the docstring in `sandbox.py` says so in the same words.
    This stops `requests`, `urllib`, and every SDK built on them, which is what
    an agent quietly phoning home actually uses. It does not stop `ctypes`, a
    re-exec, or `os.system`, and nothing written in Python could.
    """
    import socket

    def blocked(*a, **kw):
        raise _Denied(
            "network access is denied inside dinostomp's sandboxed agent rail "
            "(isolation: subprocess). An eval that needs the network should declare the call "
            "as a TOOL, so the harness records it")

    socket.socket = blocked            # type: ignore[assignment]
    socket.create_connection = blocked  # type: ignore[assignment]
    for name in ("socketpair", "create_server"):
        if hasattr(socket, name):
            setattr(socket, name, blocked)


class _Tools:
    """The child-side stub. Holds no tool code: it asks the parent."""

    def __init__(self, names, out, inp, ablated: bool):
        self._names = list(names)
        self._out, self._in = out, inp
        self._ablated = bool(ablated)

    @property
    def ablated(self) -> bool:
        return self._ablated

    def available(self):
        return list(self._names)

    def call(self, name: str, **args):
        self._out.write(json.dumps({"op": "call", "tool": str(name), "args": args}) + "\n")
        self._out.flush()
        line = self._in.readline()
        if not line:
            raise RuntimeError("the harness closed the tool channel")
        reply = json.loads(line)
        if not reply.get("ok"):
            # Raised, not returned, so an agent cannot mistake a refusal for an
            # empty result. Same contract as the in-process rail.
            raise ToolDenied(reply.get("error") or "tool call refused")
        return reply.get("result")

    def __getattr__(self, name: str):
        if name.startswith("_"):
            raise AttributeError(name)

        def bound(**args):
            return self.call(name, **args)

        return bound


class ToolDenied(RuntimeError):
    """Mirror of `harness.ToolDenied`, importable without the parent's module."""


def main() -> int:
    # 1. The protocol owns the real stdout. Anything the agent prints goes to
    #    stderr, where it is diagnostic instead of corrupting.
    protocol_out = sys.stdout
    protocol_in = sys.stdin
    sys.stdout = sys.stderr

    raw = protocol_in.readline()
    if not raw:
        return 2
    config = json.loads(raw)

    # 2. Deny the network before any pod code can run.
    _deny_network()

    # 3. Now the agent may exist.
    try:
        # The pod directory is deliberately NOT put on sys.path. It was, in the
        # first version, and that made the child WEAKER than in-process: `import
        # tools` reached the corpus and the forbidden shell function directly,
        # whatever the policy said. The agent module is loaded by file path
        # below, so it needs no path entry of its own, and a pod-local helper
        # import now fails loudly instead of quietly becoming a side channel.
        import importlib.util
        from pathlib import Path

        entry = str(config["entrypoint"])
        rel, _, symbol = entry.rpartition(":")
        if not rel:
            rel, symbol = entry, "answer"
        path = Path(config["base_dir"]) / rel
        spec = importlib.util.spec_from_file_location("dinostomp_sandboxed_agent", path)
        if spec is None or spec.loader is None:
            raise ImportError(f"cannot load agent module: {path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        fn = getattr(module, symbol or "answer", None)
        if not callable(fn):
            raise ImportError(f"{rel} must define {symbol or 'answer'}(item, tools, ctx)")
    except BaseException as exc:  # noqa: BLE001 - reported across the boundary
        protocol_out.write(json.dumps(
            {"op": "error", "type": type(exc).__name__, "message": str(exc)}) + "\n")
        protocol_out.flush()
        return 1

    tools = _Tools(config.get("tools") or [], protocol_out, protocol_in,
                   bool((config.get("ctx") or {}).get("ablated")))
    try:
        raw_result = fn(config["item"], tools, config["ctx"])
    except ToolDenied as exc:
        # A denial the agent did not recover from is an ANSWER of none, with the
        # attempt already on the parent's record. Same as the in-process rail.
        protocol_out.write(json.dumps(
            {"op": "done", "output": "", "finish_reason": "tool_denied",
             "extra": {"denied": str(exc)}}) + "\n")
        protocol_out.flush()
        return 0
    except BaseException as exc:  # noqa: BLE001 - reported across the boundary
        protocol_out.write(json.dumps(
            {"op": "error", "type": type(exc).__name__, "message": str(exc)}) + "\n")
        protocol_out.flush()
        return 1

    if isinstance(raw_result, str):
        payload = {"op": "done", "output": raw_result, "extra": {}}
    elif isinstance(raw_result, dict):
        if "output" not in raw_result:
            payload = {"op": "error", "type": "ValueError",
                       "message": "agent returned a dict with no 'output' key"}
        else:
            extra = {k: v for k, v in raw_result.items() if k != "output"}
            payload = {"op": "done", "output": raw_result["output"], "extra": extra}
    else:
        payload = {"op": "error", "type": "TypeError",
                   "message": f"agent returned {type(raw_result).__name__}; expected a string "
                              "or a dict with an 'output' key"}
    protocol_out.write(json.dumps(payload, default=str) + "\n")
    protocol_out.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
