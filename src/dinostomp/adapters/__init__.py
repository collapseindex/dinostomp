"""Adapters: other harnesses' logs, turned into evidence this battery can read.

The architecture claims the battery consumes the record and manifest SCHEMAS,
not "whatever `dinostomp run` wrote". An adapter is what makes that claim
testable: it reads a foreign log and produces conforming records, and gets no
privileges for doing so.

`dinostomp import` handles FLAT logs (jsonl/csv/json rows) by mapping columns.
That is enough for a harness whose log is a table. It is not enough for one
whose log is a nested document with tool events and per-scorer verdicts, which
is what an adapter here is for.

Every adapter obeys the same rules as the flat importer:

  - records are validated against `record.schema.json` at the boundary
  - the manifest says `imported: true` and names its source
  - `spec_sha256` / `data_sha256` come from YOUR pod, so the drift boundary
    applies exactly as it does to native evidence
  - no `tool_sha256`, because this engine did not produce the numbers
  - **no invented fields.** A field the source log lacks stays absent, the
    checks that read it skip by name, and the coverage line gets shorter.

One rule is specific to adapters and worth stating loudly: a trajectory that
arrives from another harness is recorded as `foreign_observed`, never as
`harness_observed`. dinostomp did not watch those tool calls happen. It is
better evidence than an agent's self-report, because the exporting harness is a
third party to the agent, and it is still someone else's word.
"""

from dinostomp.adapters import inspect_ai

# name -> module. `dinostomp import` sniffs a log against each `detect`.
ADAPTERS = {"inspect": inspect_ai}

__all__ = ["ADAPTERS", "inspect_ai"]
