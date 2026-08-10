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
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOC = ROOT / "FINDINGS.md"
FEED = ROOT / "findings.json"

BEGIN_INDEX, END_INDEX = "<!-- INDEX:BEGIN -->", "<!-- INDEX:END -->"
BEGIN_XREF, END_XREF = "<!-- XREF:BEGIN -->", "<!-- XREF:END -->"

# `### F-001` / **title** / `check` (CID) · date · status
ENTRY = re.compile(r"^### ([FDN]-\d+)\n\*\*(.+?)\*\*\n(.+?)\n", re.M)
SERIES_NAME = {"F": "other people's evals", "D": "dinostomp itself", "N": "negative results"}


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


def main() -> int:
    check_only = "--check" in sys.argv
    entries = parse()
    rows = existing_index_rows()

    text = DOC.read_text(encoding="utf-8")
    updated = splice(text, BEGIN_INDEX, END_INDEX, render_index(entries, rows))
    updated = splice(updated, BEGIN_XREF, END_XREF, render_xref(entries, rows))

    feed = {
        "generated_from": "FINDINGS.md",
        "counts": {s: sum(1 for e in entries if e["series"] == s) for s in "FDN"},
        "series": SERIES_NAME,
        "findings": [
            {**e, "subject": rows.get(e["id"], ("", ""))[0],
             "summary": rows.get(e["id"], ("", e["title"]))[1]}
            for e in entries],
    }
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
