"""Generate the findings index, the cross-references, and a machine-readable feed.

FINDINGS.md stays the SOURCE OF TRUTH. The prose entries are written by hand;
everything derivable from them is generated here, because the two hand-kept
copies drifted twice already: once when an index row and its entry disagreed on
ordering, and once when a new entry was added to one and not the other. Both
were caught by a test, which is the argument for generating rather than
asserting.

    python scripts/index_findings.py           # rewrite the generated regions
    python scripts/index_findings.py --check    # fail if they are out of date

What is generated, all between explicit markers so nothing else is touched:

  * the id/subject/finding/status index table
  * BY CHECK: every finding a given check has produced, which is the view you
    want before changing that check
  * BY SUBJECT: every finding against a given dataset, tool or harness
  * findings.json: one record per entry, for anyone who would rather query than
    read 2,000 lines of markdown

An entry that cannot be parsed is an ERROR, not a skip. A findings index that
silently omits a finding is worse than no index.

findings.json is a PUBLISHED CONTRACT, not a convenience dump (see D-040 for
what it cost to learn the difference). It carries a `schema_version`, it is
validated against `docs/findings.schema.json` BEFORE it is written, and the
validation is the only thing standing between a consumer and a field that
quietly changed meaning. Compatibility rule, stated once and kept:

    within a major version, fields are only ADDED.
    removing a field, renaming one, or changing its type is a MAJOR bump.

Deliberately NOT in the feed: a generation timestamp. It would make every run
differ from the last, which turns `--check` from a drift detector into noise.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOC = ROOT / "FINDINGS.md"
FEED = ROOT / "findings.json"
SCHEMA = ROOT / "docs" / "findings.schema.json"

SCHEMA_VERSION = "1.0.0"
REPO_URL = "https://github.com/collapseindex/dinostomp"

BEGIN_INDEX, END_INDEX = "<!-- INDEX:BEGIN -->", "<!-- INDEX:END -->"
BEGIN_XREF, END_XREF = "<!-- XREF:BEGIN -->", "<!-- XREF:END -->"

# `### F-001` / **title** / `check` (CID) · date · status
ENTRY = re.compile(r"^### ([FDN]-\d+)\n\*\*(.+?)\*\*\n(.+?)\n", re.M)
SERIES_NAME = {"F": "other people's evals", "D": "dinostomp itself", "N": "negative results"}

# The leading word of a status line, mapped to a closed vocabulary. Everything
# after it -- "confirmed, underpowered", "fixed in v0.50.0" -- is a QUALIFIER
# that this bucket throws away, which is why `status` is published verbatim
# alongside it.
STATUS_CLASS = {
    "confirmed": "confirmed",
    "fixed": "fixed",
    "corrected": "fixed",
    "negative": "negative",
    "measured": "measured",
    "scoped": "open",
    "later": "superseded",
    "withdrawn": "withdrawn",
}
STATUS_MEANING = {
    "confirmed": "a real defect in somebody else's eval, verified against the source",
    "fixed": "a defect in dinostomp, repaired in a named release",
    "negative": "looked, found nothing; recorded rather than dropped",
    "measured": "quantified without a verdict either way",
    "open": "known, scoped, deliberately not fixed",
    "superseded": "closed by a later entry, which is named in the status",
    "withdrawn": "retracted; the id is kept and the entry says what killed it",
}


def status_class(status: str) -> str:
    """Bucket a free-text status, or FAIL.

    An unrecognised status is an error and not an "other" bucket. A silent
    catch-all is how a mis-typed status becomes a finding nobody can filter for,
    and every default-shaped bug in this repo's own ledger has been the
    flattering one.
    """
    head = re.sub(r"[^a-z]", "", status.split(",")[0].split()[0].lower())
    if head not in STATUS_CLASS:
        raise SystemExit(
            f"unrecognised status {status!r} (leading word {head!r}). Add it to "
            f"STATUS_CLASS with a deliberate meaning, or reword the entry. This "
            f"is not defaulted on purpose.")
    return STATUS_CLASS[head]


def parse_date(raw: str) -> tuple[str | None, str]:
    """(date_iso, precision) from a ledger date, which is not always a date.

    One entry is dated "first live fleet". Rather than invent a day for it, the
    feed reports null at precision "none" and keeps the verbatim string in
    `date`. A null here is the ledger declining to claim a precision it has not
    got, which a consumer can act on; a fabricated 2026-01-01 is not.
    """
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
        return raw, "day"
    if re.fullmatch(r"\d{4}-\d{2}", raw):
        return None, "month"
    return None, "none"


def parse() -> list[dict]:
    text = DOC.read_text(encoding="utf-8")
    ids_in_doc = re.findall(r"^### ([FDN]-\d+)", text, re.M)
    entries = []
    for match in ENTRY.finditer(text):
        fid, title, meta = match.group(1), match.group(2).strip(), match.group(3).strip()
        parts = [p.strip() for p in meta.split("·")]
        if len(parts) < 3:
            raise SystemExit(f"{fid}: metadata line is not `check · date · status`: {meta!r}")
        checks = re.findall(r"\(([A-Z]\d+)\)", parts[0])
        entries.append({
            "id": fid,
            "series": fid[0],
            "title": title,
            "check_label": parts[0],
            "checks": checks,
            "date": parts[1],
            "status": " ".join(parts[2:]).strip(),
            "anchor": "#" + fid.lower(),
        })
    if len(entries) != len(ids_in_doc):
        missing = sorted(set(ids_in_doc) - {e["id"] for e in entries})
        raise SystemExit(f"{len(ids_in_doc) - len(entries)} entry/entries could not be parsed: "
                         f"{missing}. A findings index that silently omits a finding is worse "
                         f"than no index.")
    return entries


def existing_index_rows() -> dict[str, tuple[str, str]]:
    """{id: (subject, finding)} from the current table.

    The subject and the one-line summary are EDITORIAL: they are not derivable
    from the entry body, so they are preserved from the table rather than
    invented here. A generator that rewrote them would quietly reword findings.
    """
    rows = {}
    for line in DOC.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\| \[([FDN]-\d+)\]\([^)]+\) \| ([^|]*)\| ([^|]*)\|", line)
        if m:
            rows[m.group(1)] = (m.group(2).strip(), m.group(3).strip())
    return rows


def render_index(entries, rows) -> str:
    out = ["| id | subject | finding | status |", "|---|---|---|---|"]
    for e in entries:
        subject, summary = rows.get(e["id"], ("", e["title"]))
        out.append(f"| [{e['id']}]({e['anchor']}) | {subject} | {summary} | {e['status']} |")
    return "\n".join(out)


def render_xref(entries, rows) -> str:
    by_check: dict[str, list[dict]] = {}
    for e in entries:
        for cid in e["checks"] or ["(no check id)"]:
            by_check.setdefault(cid, []).append(e)
    by_subject: dict[str, list[dict]] = {}
    for e in entries:
        subject = rows.get(e["id"], ("", ""))[0] or "(unattributed)"
        by_subject.setdefault(subject, []).append(e)

    def key(cid: str):
        m = re.match(r"([A-Z])(\d+)", cid)
        return (m.group(1), int(m.group(2))) if m else ("Z", 999)

    lines = ["### By check", "",
             "Every finding a given check has produced. This is the view to read BEFORE changing",
             "a check: it is that check's own track record, including the times it was the thing",
             "at fault.", "",
             "| check | findings |", "|---|---|"]
    for cid in sorted(by_check, key=key):
        got = by_check[cid]
        links = ", ".join(f"[{e['id']}]({e['anchor']})" for e in got)
        lines.append(f"| `{cid}` | {links} |")

    lines += ["", "### By subject", "",
              "| subject | findings |", "|---|---|"]
    for subject in sorted(by_subject, key=lambda s: (-len(by_subject[s]), s.lower())):
        got = by_subject[subject]
        links = ", ".join(f"[{e['id']}]({e['anchor']})" for e in got)
        lines.append(f"| {subject} | {links} |")
    return "\n".join(lines)


def splice(text: str, begin: str, end: str, body: str) -> str:
    if begin not in text or end not in text:
        raise SystemExit(f"markers {begin} / {end} are missing from FINDINGS.md")
    head, rest = text.split(begin, 1)
    _, tail = rest.split(end, 1)
    return f"{head}{begin}\n\n{body}\n\n{end}{tail}"


def build_feed(entries, rows) -> dict:
    """Assemble the published feed. Field order here is the field order on disk."""
    from dinostomp import __version__
    from dinostomp.fingerprint import engine_fingerprint

    findings = []
    for e in entries:
        subject, summary = rows.get(e["id"], ("", e["title"]))
        date_iso, precision = parse_date(e["date"])
        findings.append({
            "id": e["id"],
            "series": e["series"],
            "series_name": SERIES_NAME[e["series"]],
            "title": e["title"],
            "summary": summary,
            "subject": subject,
            "check_label": e["check_label"],
            "checks": e["checks"],
            "date": e["date"],
            "date_iso": date_iso,
            "date_precision": precision,
            "status": e["status"],
            "status_class": status_class(e["status"]),
            "anchor": e["anchor"],
            "url": f"{REPO_URL}/blob/main/FINDINGS.md{e['anchor']}",
        })
    counts = {s: sum(1 for e in entries if e["series"] == s) for s in "FDN"}
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_from": "FINDINGS.md",
        "generator": "scripts/index_findings.py",
        "schema": "docs/findings.schema.json",
        "tool": {"name": "dinostomp", "version": __version__,
                 "engine": engine_fingerprint()},
        "counts": {**counts, "total": len(entries)},
        "series": SERIES_NAME,
        "status_classes": STATUS_MEANING,
        "findings": findings,
    }


def validate(feed: dict) -> None:
    """Hold the feed to its own published schema before writing it.

    A contract nobody validates is documentation. This runs on every generation
    rather than in a test, so a feed that violates it never reaches the disk to
    be committed by accident, and the FIRST run of it rejected a real entry:
    D-039 had reached the index with a blank subject, and the blank rendered it
    "(unattributed)" in the cross-reference without a word to anyone.
    """
    import jsonschema

    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    try:
        jsonschema.validate(feed, schema)
    except jsonschema.ValidationError as exc:
        where = "/".join(str(p) for p in exc.absolute_path) or "(root)"
        culprit = ""
        path = list(exc.absolute_path)
        if len(path) >= 2 and path[0] == "findings":
            culprit = f" [{feed['findings'][path[1]]['id']}]"
        raise SystemExit(
            f"findings.json violates docs/findings.schema.json at {where}{culprit}:\n"
            f"  {exc.message}") from None


def main() -> int:
    check_only = "--check" in sys.argv
    entries = parse()
    rows = existing_index_rows()

    text = DOC.read_text(encoding="utf-8")
    updated = splice(text, BEGIN_INDEX, END_INDEX, render_index(entries, rows))
    updated = splice(updated, BEGIN_XREF, END_XREF, render_xref(entries, rows))

    feed = build_feed(entries, rows)
    validate(feed)
    feed_text = json.dumps(feed, indent=2, ensure_ascii=False) + "\n"

    stale = (updated != text) or (not FEED.is_file()) or \
            (FEED.read_text(encoding="utf-8") != feed_text)
    if check_only:
        if stale:
            print("findings index is OUT OF DATE; run `python scripts/index_findings.py`",
                  file=sys.stderr)
            return 1
        print(f"index current: {len(entries)} entries")
        return 0

    DOC.write_text(updated, encoding="utf-8", newline="\n")
    FEED.write_text(feed_text, encoding="utf-8", newline="\n")
    counts = feed["counts"]
    print(f"{len(entries)} entries indexed "
          f"(F {counts['F']}, D {counts['D']}, N {counts['N']}) -> FINDINGS.md, findings.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
