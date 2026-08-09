"""Run a mediated agent in a separate process, with its tools left behind.

`harness.py` moved the tools out of the AGENT and into the harness, which made
the trajectory a log instead of testimony. Everything still shared one Python
process, so the agent could reach around the harness whenever it liked: import
`os`, read the parent's API keys, open a socket, monkeypatch `Tools` itself.
That was stated plainly and asserted in the tests rather than papered over.

This module puts an operating-system process boundary in the way. The agent runs
in a child; the tools stay in the parent and are reached over a pipe. The child
never imports the tool module and never holds the corpus, the API client, or the
retrieval index. Denying a call is now a decision made in a different process
from the one asking.

    parent                              child
    ------                              -----
    spawn, sanitised env         --->   import the agent module
    wait                                answer(item, tools, ctx)
    {"op":"call","tool":...}     <---     tools.retrieve(key=...)
    run the REAL tool
    record the step
    {"ok":true,"result":...}     --->     returns
    {"op":"done","output":...}   <---   return

WHAT THIS BUYS, precisely, because the word "sandbox" promises more than any of
it delivers:

  - **Credential isolation. Real.** The child's environment is stripped of every
    variable matching *KEY*, *TOKEN*, *SECRET*, *PASSWORD* and friends, so an
    agent cannot read the keys the parent uses to pay for a run. Verifiable, and
    verified in `tests/test_sandbox.py`.
  - **Tool isolation. Real, and narrower than it first sounds.** The tool code
    is loaded only in the parent, and the pod directory is NOT on the child's
    `sys.path`, so `import tools` fails and a denied tool cannot be reached by
    importing it. The first version of this module DID add the pod directory to
    the path, which made the child weaker than running in-process; the test that
    catches it is in `tests/test_sandbox.py`. What remains: the tool FILE is
    still on disk and readable, because the filesystem is not confined, so an
    agent that goes looking with `open()` can read the corpus. It cannot CALL a
    denied tool, and the parent still records every call it does make.
  - **Fault and hang containment. Real.** A segfault, an infinite loop or a
    memory bomb takes the child down, not the run. `timeout_s` is enforced by
    killing the process, and the run stops cleanly with its ledger intact.
  - **Network denial. BEST EFFORT, and defeatable.** `socket.socket` is
    replaced in the child before the agent is imported, which stops the ordinary
    ways of reaching the network: `requests`, `urllib`, an SDK. It does NOT stop
    `ctypes`, a re-exec, or `os.system`, and `tests/test_sandbox.py` proves one
    of those escapes rather than claiming otherwise.
  - **Filesystem confinement. NOT PROVIDED.** The child runs as the same user
    with the same rights. It can read and write anything you can. Doing this
    properly needs a container, a jail, or a Windows job object with a
    restricted token, none of which this module attempts.

So: `isolation: subprocess` is CONTAINMENT, not confinement. It defends a run
against an agent that is careless, buggy, or quietly overreaching. It does not
defend a machine against an agent that is hostile, and no amount of Python in
this file would change that. Run untrusted agent code in a VM.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from dinostomp.providers import Completion, ProviderError
from dinostomp.harness import WITHHELD, Tools, load_tools

# Environment variables the child never sees. Substring match, case-insensitive,
# per the project's own security rules: strip anything that looks like a
# credential rather than maintaining a list of the ones we happen to know.
SECRET_PATTERNS = ("key", "token", "secret", "password", "passwd", "credential",
                   "auth", "session", "cookie", "api")

# Kept regardless, because a Python child will not start without them on
# Windows and a failure to launch is not isolation, it is a broken pod.
ALWAYS_KEEP = ("PATH", "SYSTEMROOT", "SYSTEMDRIVE", "WINDIR", "COMSPEC", "TEMP", "TMP",
               "TMPDIR", "HOME", "USERPROFILE", "LANG", "LC_ALL", "PYTHONHASHSEED",
               "PYTHONIOENCODING", "PROCESSOR_ARCHITECTURE", "NUMBER_OF_PROCESSORS")

DEFAULT_TIMEOUT_S = 60


def sanitised_env(base: dict | None = None) -> dict:
    """A child environment with every credential-looking variable removed.

    Removal, not an allow-list: an allow-list would keep breaking pods that need
    an ordinary variable, and a pod that breaks gets its isolation turned off.
    """
    src = dict(base if base is not None else os.environ)
    out = {}
    for k, v in src.items():
        if k.upper() in ALWAYS_KEEP:
            out[k] = v
            continue
        if any(p in k.lower() for p in SECRET_PATTERNS):
            continue
        out[k] = v
    # No PYTHONPATH is set on purpose: the child runs under `-I`, which ignores
    # it, and needs nothing but the standard library to start. The pod directory
    # is put on `sys.path` inside the child, after the network is denied.
    return out


def _redact(text: str) -> str:
    """Keep a child's error text from carrying a secret back into a record."""
    return re.sub(r"(sk-|ghp_|xox[baprs]-)[A-Za-z0-9_\-]{8,}", r"\1***", text or "")


class SandboxedTarget:
    """A mediated agent, run in a child process with the tools left behind."""

    provider_name = "mediated"

    def __init__(self, model: str, entrypoint: str, base_dir: Path, *,
                 tools: dict | None = None, forbidden: set[str] | None = None,
                 max_steps: int | None = None, ablate: bool = False,
                 timeout_s: int | None = None):
        self.model = model
        self.entrypoint = str(entrypoint)
        self.base_dir = Path(base_dir)
        self.tool_spec = dict(tools or {})
        # Loaded HERE, in the parent, and never handed across the boundary. The
        # child gets tool NAMES; the parent keeps the code and the data.
        self.registry = load_tools(self.tool_spec, self.base_dir)
        self.forbidden = set(forbidden or ())
        self.max_steps = max_steps
        self.ablate = bool(ablate)
        self.timeout_s = int(timeout_s or DEFAULT_TIMEOUT_S)

    def complete(self, item: dict, seed: int, params: dict) -> Completion:
        tools = Tools(self.registry, forbidden=self.forbidden,
                      max_steps=self.max_steps, ablate=self.ablate)
        config = {
            "entrypoint": self.entrypoint,
            "base_dir": str(self.base_dir),
            "item": item,
            "ctx": {"model": self.model, "seed": seed, "params": dict(params or {}),
                    "ablated": self.ablate},
            "tools": sorted(set(self.tool_spec) - self.forbidden),
        }
        # Run the child BY PATH, not as `-m dinostomp._child`. `-I` is what makes
        # this isolated (no user site-packages, no inherited PYTHON* variables,
        # the CWD off sys.path) and `-I` also ignores PYTHONPATH, so a module
        # invocation could not find dinostomp at all. `_child.py` imports nothing
        # but the standard library precisely so this works.
        child = Path(__file__).resolve().with_name("_child.py")
        proc = subprocess.Popen(
            [sys.executable, "-I", str(child)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            env=sanitised_env(), cwd=str(self.base_dir), text=True, encoding="utf-8",
            bufsize=1,
        )
        try:
            return self._converse(proc, config, tools)
        finally:
            if proc.poll() is None:
                proc.kill()
            proc.wait()

    def _converse(self, proc, config: dict, tools: Tools) -> Completion:
        """Drive the child until it finishes, serving its tool calls."""
        import threading

        result: dict[str, Any] = {}

        def pump():
            try:
                proc.stdin.write(json.dumps(config) + "\n")
                proc.stdin.flush()
                for line in proc.stdout:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        msg = json.loads(line)
                    except json.JSONDecodeError:
                        # The agent printed something. Not fatal, and not
                        # allowed to corrupt the protocol either.
                        continue
                    op = msg.get("op")
                    if op == "call":
                        reply = self._serve(msg, tools)
                        proc.stdin.write(json.dumps(reply) + "\n")
                        proc.stdin.flush()
                    elif op in ("done", "error"):
                        result.update(msg)
                        return
            except (BrokenPipeError, OSError, ValueError) as exc:
                result.setdefault("op", "error")
                result.setdefault("type", type(exc).__name__)
                result.setdefault("message", str(exc))

        thread = threading.Thread(target=pump, daemon=True)
        thread.start()
        thread.join(self.timeout_s)
        if thread.is_alive():
            proc.kill()
            thread.join(5)
            raise ProviderError(
                f"agent {self.entrypoint!r} did not finish within {self.timeout_s}s and was "
                f"killed. A hang is contained here rather than stopping the machine; raise "
                f"`isolation.timeout_s` if the agent is legitimately slow")

        if not result:
            stderr = _redact((proc.stderr.read() or "").strip())
            raise ProviderError(
                f"agent {self.entrypoint!r} produced no result in its child process"
                + (f": {stderr[-400:]}" if stderr else ""))
        if result.get("op") == "error":
            raise ProviderError(
                f"agent {self.entrypoint!r} raised {result.get('type')}: "
                f"{_redact(str(result.get('message')))}")

        text = result.get("output")
        if not isinstance(text, str):
            raise ProviderError(
                f"agent 'output' must be a string, got {type(text).__name__}")
        extra = result.get("extra") or {}
        if "trajectory" in extra:
            raise ProviderError(
                f"agent {self.entrypoint!r} returned a 'trajectory'. On the mediated rail the "
                "harness records the calls it observed, so a self-reported trace would be "
                "unverifiable evidence in a record that claims to be a log")

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
            finish_reason=str(extra.get("finish_reason") or result.get("finish_reason") or "stop"),
            input_tokens=max(0, int(extra.get("input_tokens") or 0)),
            output_tokens=max(0, int(extra.get("output_tokens") or 0)),
            raw_usage={"target": True, "isolation": "subprocess", **(extra.get("usage") or {})},
            model_reported=str(extra.get("model_reported") or self.model),
            trajectory=list(tools.steps),
            cost_usd=cost,
        )

    def _serve(self, msg: dict, tools: Tools) -> dict:
        """One tool call, executed in the PARENT. Policy is decided here."""
        from dinostomp.harness import ToolDenied

        name = str(msg.get("tool") or "")
        args = msg.get("args") if isinstance(msg.get("args"), dict) else {}
        try:
            return {"ok": True, "result": tools.call(name, **args)}
        except ToolDenied as exc:
            return {"ok": False, "denied": True, "error": str(exc)}
        except ProviderError as exc:
            return {"ok": False, "denied": False, "error": str(exc)}
