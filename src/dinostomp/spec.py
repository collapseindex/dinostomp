"""Load and validate dinostomp eval specs.

The validator returns machine-readable issues instead of raising, so an
LLM (or a human) authoring a spec can self-correct in a loop:

    spec, issues = load_spec("eval.yaml")
    if issues:
        ...fix and retry...
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from importlib import resources
from pathlib import Path
from typing import Any, Optional

import jsonschema
import yaml


SCHEMA_NAMES = ("eval", "items", "record", "manifest", "report")


@dataclass(frozen=True)
class Issue:
    """One validation problem, addressed to the author of the spec."""

    loc: str
    message: str
    check: str = "schema"

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


def load_schema(name: str) -> dict[str, Any]:
    """Load a bundled JSON Schema by short name (e.g. "eval")."""
    if name not in SCHEMA_NAMES:
        raise ValueError(f"unknown schema {name!r}, expected one of {SCHEMA_NAMES}")
    ref = resources.files("dinostomp.schemas").joinpath(f"{name}.schema.json")
    return json.loads(ref.read_text(encoding="utf-8"))


def _json_path(parts: Any) -> str:
    out = "$"
    for p in parts:
        out += f"[{p}]" if isinstance(p, int) else f".{p}"
    return out


def validate_obj(obj: Any, schema_name: str) -> list[Issue]:
    """Validate a parsed object against a bundled schema. Returns all issues."""
    schema = load_schema(schema_name)
    validator_cls = jsonschema.validators.validator_for(schema)
    validator = validator_cls(schema)
    issues = []
    for err in sorted(validator.iter_errors(obj), key=lambda e: list(e.absolute_path)):
        issues.append(Issue(loc=_json_path(err.absolute_path), message=err.message))
    return issues


def load_spec(path: str | Path) -> tuple[Optional[dict[str, Any]], list[Issue]]:
    """Parse and validate an eval spec file (YAML or JSON).

    Returns (spec, issues). spec is None only when the file could not be
    parsed at all; a parsed-but-invalid spec is returned alongside its issues
    so the caller can see both.
    """
    p = Path(path)
    if not p.is_file():
        return None, [Issue(loc="$", message=f"spec file not found: {p}", check="io")]
    try:
        raw = p.read_text(encoding="utf-8")
    except OSError as exc:
        return None, [Issue(loc="$", message=f"cannot read spec: {exc}", check="io")]
    try:
        obj = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        return None, [Issue(loc="$", message=f"not valid YAML: {exc}", check="parse")]
    if not isinstance(obj, dict):
        return None, [Issue(loc="$", message="spec must be a mapping at the top level", check="parse")]

    issues = validate_obj(obj, "eval")
    issues.extend(_cross_checks(obj, p.parent))
    return obj, issues


def _cross_checks(spec: dict[str, Any], base: Path) -> list[Issue]:
    """Checks the schema language cannot express. Same Issue shape."""
    issues: list[Issue] = []

    declared_mounts = {str(m) for m in (spec.get("mounts") or []) if isinstance(m, str)}
    mounted = {(base / Path(m)).resolve() for m in declared_mounts}

    def check_pod_path(loc: str, raw: str, what: str) -> None:
        rel = Path(raw)
        if rel.is_absolute():
            issues.append(Issue(loc=loc, message=f"{what} path must be relative to the spec file", check="path"))
            return
        resolved = (base / rel).resolve()
        if not resolved.is_relative_to(base.resolve()) and resolved not in mounted:
            # Leaving the pod is allowed only for something DECLARED as a mount,
            # because declaring it is what gets it hashed into every manifest.
            # Undeclared, it would be an input nobody can detect changing.
            issues.append(Issue(
                loc=loc, check="path",
                message=f"{what} path escapes the eval directory; declare it under `mounts` if "
                        "that is deliberate, which is what puts it inside the drift boundary"))
        elif not resolved.is_file():
            issues.append(Issue(loc=loc, message=f"{what} file not found: {raw}", check="path"))

    for idx, raw in enumerate(spec.get("mounts") or []):
        if not isinstance(raw, str):
            continue
        loc = f"$.mounts[{idx}]"
        if Path(raw).is_absolute():
            issues.append(Issue(loc=loc, message="mount paths must be relative to the spec file",
                                check="path"))
        elif not (base / raw).resolve().is_file():
            issues.append(Issue(loc=loc, message=f"mount not found: {raw}", check="path"))

    data = spec.get("data")
    if isinstance(data, dict) and isinstance(data.get("path"), str):
        check_pod_path("$.data.path", data["path"], "data")

    scorer = spec.get("scorer")
    if isinstance(scorer, dict) and scorer.get("kind") == "python" and isinstance(scorer.get("code"), str):
        check_pod_path("$.scorer.code", scorer["code"], "scorer code")

    # A pod-local judge is code that decides verdicts, so it gets the strictest
    # treatment of all: traversal rejected, hashed into every manifest.
    if isinstance(scorer, dict) and scorer.get("kind") == "judge":
        judge = scorer.get("judge")
        if isinstance(judge, dict) and judge.get("provider") == "python":
            entry = judge.get("entrypoint")
            if isinstance(entry, str):
                rel = entry.rpartition(":")[0] if ":" in entry else entry
                check_pod_path("$.scorer.judge.entrypoint", rel, "judge entrypoint")

    # Target entrypoints are pod-local code hashed into every manifest, so they
    # get the same traversal treatment as a custom scorer.
    for idx, mc in enumerate(spec.get("models") or []):
        if not isinstance(mc, dict) or mc.get("provider") not in ("python", "mediated"):
            continue
        entry = mc.get("entrypoint")
        if isinstance(entry, str):
            rel = entry.rpartition(":")[0] if ":" in entry else entry
            check_pod_path(f"$.models[{idx}].entrypoint", rel, "target entrypoint")

    # A tool is pod-local code the agent executes, so it gets the same traversal
    # treatment as a scorer or a target: an unhashed input is outside the drift
    # boundary, and a tool outside the pod is an unhashed input.
    tools = spec.get("tools")
    if isinstance(tools, dict):
        for name, entry in tools.items():
            if isinstance(entry, str):
                rel = entry.rpartition(":")[0] if ":" in entry else entry
                check_pod_path(f"$.tools.{name}", rel, f"tool {name!r}")

    mediated = [mc for mc in spec.get("models") or []
                if isinstance(mc, dict) and mc.get("provider") == "mediated"]
    if mediated and not tools:
        issues.append(Issue(
            loc="$.tools", check="tools",
            message="a mediated agent is declared but this spec offers no tools. The mediated rail "
                    "exists so the HARNESS holds the tools; an agent with none can only answer from "
                    "memory, and `python` is the rail for that"))
    if tools and not mediated:
        issues.append(Issue(
            loc="$.tools", check="tools",
            message="a `tools` block is declared but no model uses provider `mediated`; nothing in "
                    "this spec can reach these tools. A `python` target calls its own functions and "
                    "self-reports the trace"))

    # A forbidden tool the harness never offers is a policy about nothing. Worth
    # saying, because a typo here reads as an enforced ban and enforces nothing.
    if isinstance(tools, dict) and mediated:
        traj_block = spec.get("trajectory")
        if isinstance(traj_block, dict):
            for key in ("required_tools", "forbidden_tools"):
                unknown = sorted({t for t in (traj_block.get(key) or [])
                                  if isinstance(t, str)} - set(tools))
                if unknown:
                    issues.append(Issue(
                        loc=f"$.trajectory.{key}", check="trajectory",
                        message=f"{', '.join(unknown)} named in {key} but not offered in $.tools. On "
                                "the mediated rail the harness can only enforce policy about tools "
                                "it holds, so this line does nothing"))

    # A tool cannot be both mandatory and banned; the policy would be
    # unsatisfiable and T1/T2 would contradict each other on every item.
    traj = spec.get("trajectory")
    if isinstance(traj, dict):
        required = {t for t in (traj.get("required_tools") or []) if isinstance(t, str)}
        forbidden = {t for t in (traj.get("forbidden_tools") or []) if isinstance(t, str)}
        both = sorted(required & forbidden)
        if both:
            issues.append(Issue(loc="$.trajectory", check="trajectory",
                                message=f"tool(s) {', '.join(both)} are both required and forbidden; "
                                        "no trajectory could satisfy this policy"))
        if (required or forbidden or traj.get("max_steps")) and not any(
            isinstance(mc, dict) and mc.get("provider") in ("python", "mediated", "imported")
            for mc in spec.get("models") or []
        ):
            issues.append(Issue(loc="$.trajectory", check="trajectory",
                                message="a trajectory policy is declared but no model uses a "
                                        "python, mediated or imported target; nothing in this "
                                        "spec can produce or carry a trajectory"))

    # Typed claims must reference models this spec actually runs: a claim
    # about a phantom model is an authoring error, caught before any money.
    models = {mc.get("model") for mc in spec.get("models", []) if isinstance(mc, dict)}
    for idx, claim in enumerate(spec.get("claims") or []):
        if not isinstance(claim, dict):
            continue
        loc = f"$.claims[{idx}]"
        if claim.get("type") == "accuracy":
            if claim.get("model") not in models and claim.get("model") != "each":
                issues.append(Issue(loc=loc, message=f"claim names model {claim.get('model')!r}, "
                                                     "which this spec does not run", check="claims"))
        elif claim.get("type") == "superiority":
            for side in ("better", "worse"):
                if claim.get(side) not in models:
                    issues.append(Issue(loc=loc, message=f"claim names model {claim.get(side)!r}, "
                                                         "which this spec does not run", check="claims"))
            if claim.get("better") == claim.get("worse"):
                issues.append(Issue(loc=loc, message="a model cannot beat itself", check="claims"))

    return issues


def spec_sha256(path: str | Path) -> str:
    """SHA-256 of a file's exact bytes (spec, data, scorer code alike).

    Everything that influences a run gets hashed into its manifest; this is
    the drift boundary the stomp battery checks against.
    """
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def jsonl_lines(text: str) -> list[str]:
    """Split JSONL on NEWLINES, and on nothing else.

    `str.splitlines()` also splits on \x0b, \x0c, \x1c, \x1d, \x1e, \x85,
    U+2028 and U+2029. `json.dumps(..., ensure_ascii=False)` does not escape
    any of those and they are legal inside a JSON string, so a valid JSONL file
    containing one gets torn in half by the reader and then reported as the
    DATA being malformed.

    Not hypothetical: MMLU contains \x85 (NEL) twice, so auditing a
    Redux-derived copy of it produced `invalid JSON: Unterminated string` for a
    file whose 5,702 lines all parse (D-032). The error blamed the dataset for
    a defect in the reader, which is the direction this project cares about.

    A trailing \r is stripped so a CRLF file still reads, which is the one bit
    of line-ending tolerance a JSONL reader owes its caller.
    """
    return [line[:-1] if line.endswith("\r") else line for line in text.split("\n")]
