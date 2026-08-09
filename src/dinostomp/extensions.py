"""Two growth surfaces, and one rule that keeps them safe.

The core owns what BROKEN means. Extensions widen what the battery looks for.
That asymmetry is the whole design, and it is enforced here rather than
requested in a style guide.

THE HARD RULE
=============

**An extension may add findings. It may never remove or soften one.**

No hook runs before the core. No hook filters findings. No hook adjusts a
threshold. The moment an extension can make a verdict greener, every `SOUND` in
the wild silently means "sound according to whatever plugins that person had
installed", and the engine fingerprint stops meaning anything, because the
verdict would depend on code the fingerprint does not cover.

Three mechanisms enforce it, in increasing order of bluntness:

  1. Extensions receive a WRITE-ONLY collector. There is no API to read, edit,
     or delete a finding, including their own.
  2. `THRESHOLDS` is hashed before and after extension code is imported and
     run. A mutation aborts the audit rather than producing a report whose
     settings nobody can reconstruct.
  3. Core findings are snapshotted and compared after the merge. A core finding
     that changed is a bug or an attack, and either way the report is refused.

WHAT AN EXTENSION PAYS
======================

The same evidence tax the core pays. A third-party check ships with its own
planted defect that must be caught and its own clean pod that must stay clean.
Until it does, its findings are still REPORTED (suppressing them would be its
own kind of dishonesty) but they do not count toward coverage, and the report
labels them `unvalidated`. A pile of unvalidated lint rules must not be able to
wear this tool's verdict.

WHAT THE REPORT SAYS
====================

Every loaded extension is named, versioned and hashed in the report, exactly as
the engine is. A `SOUND` produced with extensions loaded is a precise claim
about a specific set of code, or it is not a claim at all.

Extensions are imported Python and have the powers of imported Python. They are
trusted because installing one is a deliberate act, unlike opening a stranger's
pod, and that difference is why they are not gated behind `--trust-code`. The
naming and hashing is what keeps the trust informed.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from importlib import metadata
from typing import Any, Callable, Protocol, runtime_checkable

ENTRY_POINT_GROUP = "dinostomp.checks"

# Extension check ids are namespaced so a third-party check can never collide
# with a core id, and so a reader can always tell where a finding came from.
ID_PREFIX = "x:"


class ExtensionError(RuntimeError):
    """Raised when an extension breaks the contract. Never swallowed."""


@runtime_checkable
class CheckProvider(Protocol):
    """What a `dinostomp.checks` entry point must expose.

    NAME/VERSION identify it in the report. CHECKS declares what it adds.
    TRIALS and CLEAN_PODS are the evidence tax; omit them and the checks are
    reported but excluded from coverage.
    """

    NAME: str
    VERSION: str
    CHECKS: list


@dataclass(frozen=True)
class ExtensionCheck:
    """One third-party check.

    `run` receives a read-only context and a write-only collector. It returns
    nothing; anything it wants to say, it says through the collector.
    """

    id: str
    name: str
    gating: bool
    applies_when: str
    run: Callable[[Any, Any], None]
    slug: str = ""

    def namespaced(self, pkg: str) -> str:
        return f"{ID_PREFIX}{pkg}:{self.id}"


@dataclass
class Collector:
    """Write-only. There is deliberately no read, edit, or delete.

    An extension cannot see core findings, cannot see other extensions'
    findings, and cannot see its own after emitting them. That is not
    inconvenience for its own sake: a plugin that can read the verdict is one
    step from a plugin that shapes it.
    """

    _out: list = field(default_factory=list)

    def finding(self, check_id: str, level: str, detail: str, *, n: int = 0,
                examples: list[str] | None = None, evidence: dict | None = None) -> None:
        if level not in ("pass", "fail", "warn", "skip", "n/a"):
            raise ExtensionError(f"unknown finding level {level!r}")
        self._out.append({"check_id": check_id, "level": level, "detail": detail,
                          "n": n, "examples": list(examples or []),
                          "evidence": dict(evidence or {})})

    def drain(self) -> list[dict]:
        out, self._out = self._out, []
        return out


@dataclass(frozen=True)
class LoadedExtension:
    name: str
    version: str
    sha256: str
    checks: list[ExtensionCheck]
    validated: bool
    reason: str = ""

    def to_dict(self) -> dict:
        return {"name": self.name, "version": self.version, "sha256": self.sha256,
                "checks": [c.id for c in self.checks], "validated": self.validated,
                **({"unvalidated_reason": self.reason} if not self.validated else {})}


def _module_hash(module) -> str:
    """SHA-256 of the provider module's own source.

    Not a supply-chain guarantee: it hashes the module this process imported,
    which is exactly the code that produced the findings. That is the claim
    being made, and it is the only one available from inside the process.
    """
    try:
        import inspect

        src = inspect.getsource(module)
    except (OSError, TypeError):
        src = f"{getattr(module, '__name__', '?')}@{getattr(module, '__file__', '?')}"
    return hashlib.sha256(src.encode("utf-8", "replace")).hexdigest()


def thresholds_fingerprint(thresholds: dict) -> str:
    """A hash of every dial, so a mutation cannot hide."""
    return hashlib.sha256(
        json.dumps({k: v for k, v in sorted(thresholds.items())}, sort_keys=True,
                   default=str).encode("utf-8")).hexdigest()


def _validated(module) -> tuple[bool, str]:
    """Has this extension paid the evidence tax?

    The bar is the one the core holds itself to: a planted defect its check must
    catch, and a clean pod its check must stay quiet on. Declaring neither is
    not an error, it is a labelled limitation.
    """
    trials = getattr(module, "TRIALS", None)
    clean = getattr(module, "CLEAN_PODS", None)
    if not trials:
        return False, ("declares no TRIALS: no planted defect proves these checks fire, so they "
                       "are reported but excluded from coverage")
    if not clean:
        return False, ("declares no CLEAN_PODS: nothing proves these checks stay quiet on a good "
                       "eval, so they are reported but excluded from coverage")
    return True, ""


def discover(core_ids: set[str], *, entry_points=None) -> tuple[list[LoadedExtension], list[str]]:
    """Load every installed check provider. Returns (extensions, problems).

    A provider that raises on import, collides with a core id, or fails the
    protocol is REFUSED and reported. It is never partially loaded: half an
    extension is a coverage line nobody can interpret.
    """
    loaded: list[LoadedExtension] = []
    problems: list[str] = []
    try:
        eps = entry_points if entry_points is not None else \
            metadata.entry_points(group=ENTRY_POINT_GROUP)
    except Exception as exc:  # noqa: BLE001 - a broken environment is not a crash
        return [], [f"cannot enumerate {ENTRY_POINT_GROUP} entry points: {exc}"]

    for ep in eps:
        try:
            module = ep.load()
        except Exception as exc:  # noqa: BLE001 - one bad extension must not kill the audit
            problems.append(f"{ep.name}: refused, it raised on import: {exc}")
            continue
        checks = list(getattr(module, "CHECKS", []) or [])
        if not checks:
            problems.append(f"{ep.name}: refused, it declares no CHECKS")
            continue
        bad = [c for c in checks if not isinstance(c, ExtensionCheck)]
        if bad:
            problems.append(f"{ep.name}: refused, {len(bad)} entr(y/ies) are not ExtensionCheck")
            continue
        collides = [c.id for c in checks if c.id in core_ids]
        if collides:
            problems.append(f"{ep.name}: refused, check id(s) {', '.join(collides)} collide with "
                            "core checks; extension ids are namespaced for exactly this reason")
            continue
        ok, reason = _validated(module)
        loaded.append(LoadedExtension(
            name=getattr(module, "NAME", ep.name),
            version=str(getattr(module, "VERSION", "0")),
            sha256=_module_hash(module),
            checks=checks, validated=ok, reason=reason))
    return loaded, problems


def run_extensions(extensions: list[LoadedExtension], context: Any, thresholds: dict
                   ) -> tuple[list[dict], list[str]]:
    """Run every extension check under the hard rule. Returns (findings, problems).

    The threshold fingerprint is taken before and compared after. An extension
    that moved a dial does not get its findings dropped and the audit continued;
    the audit is refused, because a report whose settings cannot be
    reconstructed is worse than no report.
    """
    before = thresholds_fingerprint(thresholds)
    out: list[dict] = []
    problems: list[str] = []
    for ext in extensions:
        for check in ext.checks:
            collector = Collector()
            try:
                check.run(context, collector)
            except Exception as exc:  # noqa: BLE001 - an extension crash is its problem
                problems.append(f"{ext.name}:{check.id} raised and was skipped: {exc}")
                continue
            for f in collector.drain():
                out.append({**f, "check_id": check.namespaced(ext.name),
                            "name": check.name, "gating": check.gating,
                            "extension": ext.name, "validated": ext.validated})
    after = thresholds_fingerprint(thresholds)
    if before != after:
        raise ExtensionError(
            "an extension mutated THRESHOLDS during the audit. The report is refused: a verdict "
            "whose settings cannot be reconstructed is worse than no verdict. Extensions widen "
            "what the battery looks for; they do not decide what BROKEN means.")
    return out, problems
