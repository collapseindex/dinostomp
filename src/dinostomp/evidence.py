"""What each check needs, stated in terms of the schemas rather than the runner.

Until now the coupling was implicit: the checks read whatever `dinostomp run`
happened to write, and a check that could not run said "no runs on disk yet".
That sentence is wrong in two directions. It is wrong when there ARE runs and
the check needs a field they lack, and it is wrong about the architecture,
because it assumes the only way evidence can exist is that this runner made it.

The record and manifest schemas are the contract. A check declares which fields
of that contract it consumes. Two things follow:

  1. A skip says exactly what is missing. "no `finish_reason` on 240 of 240
     records" is a sentence someone can act on; "no runs on disk yet" is not,
     especially when there are runs on disk.

  2. Anything that can WRITE conforming records and manifests can be audited,
     whether or not dinostomp produced them. An importer for another harness's
     logs becomes a transform into this contract rather than a change to the
     battery. `dinostomp import` is the reference implementation of exactly
     that, and it deliberately gets no privileges the battery does not give
     any other producer.

The requirements below are the honest statement of what the battery reads. If a
check is listed as needing a field and does not read it, that is a bug in this
table, and `tests/test_evidence.py` is where it gets caught.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Fields the schemas mark optional but individual checks depend on. A field in
# the schema's `required` list is not listed here: a record missing one of those
# is schema-invalid, which R4 gates on, and there is no point telling a check to
# skip over something the report already calls broken.
RECORD = "record"
MANIFEST = "manifest"


@dataclass(frozen=True)
class Need:
    """One evidence field a check consumes, and what it does with it."""

    where: str          # RECORD or MANIFEST
    field: str
    why: str

    def describe(self) -> str:
        return f"`{self.field}` on every {self.where} ({self.why})"


# What each check reads BEYOND the schema-required core. Checks absent from this
# table need only the required fields, and their applicability is decided by the
# shape of the eval (choice items, a fleet, a probe) rather than by evidence
# fields. That distinction is the point: "not applicable" and "not enough
# evidence" are different answers and the report should not blur them.
NEEDS: dict[str, list[Need]] = {
    "R3": [Need(RECORD, "usage", "per-record cost is summed and compared to the manifest total"),
           Need(MANIFEST, "spend_usd", "the ledger total the sum is checked against")],
    "R5": [Need(RECORD, "finish_reason", "a truncated response is identified by it")],
    "R8": [Need(RECORD, "output", "verdicts are re-scored from the recorded text"),
           Need(RECORD, "score", "the recorded verdict is what gets re-derived")],
    "R14": [Need(RECORD, "output", "a collapsed model is identified by repeated output text")],
    "R16": [Need(RECORD, "output", "an unparsed-but-correct answer is looked for in the text")],
    "R18": [Need(RECORD, "usage", "billed output tokens are compared against the recorded text")],
    "R19": [Need(MANIFEST, "tool_sha256", "the engine that produced the run is compared to this one")],
    "T1": [Need(RECORD, "trajectory", "a forbidden tool call is read from the trace")],
    "T2": [Need(RECORD, "trajectory", "a missing required call is read from the trace")],
    "T3": [Need(RECORD, "trajectory", "well-formedness is a property of the trace")],
    "T4": [Need(RECORD, "trajectory", "grounding compares answers to the trace's own tool results")],
    "T5": [Need(RECORD, "trajectory", "under-reporting is measured against fleet trace length")],
    "T6": [Need(RECORD, "trajectory", "repeated calls are read from the trace")],
    "J1": [Need(RECORD, "judge_response", "the judge's verbatim reply is re-parsed offline")],
    "J2": [Need(RECORD, "perturbation", "each regrade is attributed to the perturbation applied")],
    "J3": [Need(RECORD, "judge_response", "self-consistency compares two replies to identical input")],
    "J4": [Need(RECORD, "graded_model", "a family gap needs to know whose answer was graded")],
    "S10": [Need(RECORD, "canary_kind", "a control and a real canary are told apart by it")],
    "P10": [Need(MANIFEST, "seed", "spread is measured across seeds")],
    "P11": [Need(MANIFEST, "framing", "a swing is attributed to the instruction framing")],
    "P12": [Need(MANIFEST, "framing", "a ranking is compared framing by framing")],
}


@dataclass
class Survey:
    """What evidence is actually present across a pod's runs."""

    n_records: int = 0
    n_manifests: int = 0
    record_fields: dict[str, int] = field(default_factory=dict)
    manifest_fields: dict[str, int] = field(default_factory=dict)

    def present(self, need: Need) -> int:
        table = self.record_fields if need.where == RECORD else self.manifest_fields
        return table.get(need.field, 0)

    def total(self, where: str) -> int:
        return self.n_records if where == RECORD else self.n_manifests


def survey(entries: list[dict]) -> Survey:
    """Count which optional fields the evidence on disk actually carries.

    `entries` is the discovered-run shape the linter already builds:
    {"manifest": dict | None, "records": [dict, ...]}.
    """
    out = Survey()
    for e in entries:
        m = e.get("manifest")
        if m is not None:
            out.n_manifests += 1
            for k, v in m.items():
                if v is not None:
                    out.manifest_fields[k] = out.manifest_fields.get(k, 0) + 1
        for r in e.get("records") or ():
            out.n_records += 1
            for k, v in r.items():
                if v is not None and v != []:
                    out.record_fields[k] = out.record_fields.get(k, 0) + 1
    return out


def missing_for(check_id: str, survey_: Survey) -> list[Need]:
    """Which declared needs this evidence does not satisfy."""
    return [n for n in NEEDS.get(check_id, []) if survey_.present(n) == 0]


def skip_reason(check_id: str, survey_: Survey) -> str | None:
    """A skip message naming the missing FIELDS, or None if evidence suffices.

    Returns None when nothing is missing, so a caller can fall through to its
    own applicability logic rather than being overridden by this module.
    """
    if survey_.n_records == 0 and survey_.n_manifests == 0:
        return ("no evidence on disk. This check reads run records; produce them with "
                "`dinostomp run <spec>`, or import another harness's logs with "
                "`dinostomp import`")
    gaps = missing_for(check_id, survey_)
    if not gaps:
        return None
    parts = []
    for need in gaps:
        total = survey_.total(need.where)
        parts.append(f"no {need.describe()}; 0 of {total} {need.where}(s) carry it")
    return "; ".join(parts)


def contract_summary() -> list[dict[str, Any]]:
    """The contract, as data, for `dinostomp evidence` and for tests."""
    return [
        {"check": cid,
         "needs": [{"where": n.where, "field": n.field, "why": n.why} for n in needs]}
        for cid, needs in sorted(NEEDS.items())
    ]
