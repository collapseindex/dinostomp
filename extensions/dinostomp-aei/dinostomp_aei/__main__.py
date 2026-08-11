"""Audit an AEI release from the command line.

    python -m dinostomp_aei aei_claude_ai_2026-06-26.csv [--json out.json]

Exit codes follow the core's convention: 0 clean, 1 a check failed, 2 nothing
could be checked. A warn does not change the exit code, because a diagnostic
that can break a build is a gate wearing a diagnostic's label.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import NAME, VERSION, SPEC
from . import rules


class Collector:
    def __init__(self) -> None:
        self.findings: list[dict] = []

    def finding(self, check_id, level, detail, *, n=0, examples=None, evidence=None) -> None:
        self.findings.append({"check_id": check_id, "level": level, "detail": detail,
                              "n": n, "examples": list(examples or []),
                              "evidence": dict(evidence or {})})


MARK = {"pass": "ok  ", "fail": "FAIL", "warn": "warn", "skip": "skip", "n/a": "n/a "}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="dinostomp_aei", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path", help="an AEI release CSV")
    ap.add_argument("--json", help="also write the findings here")
    args = ap.parse_args(argv)

    path = Path(args.path)
    if not path.is_file():
        print(f"no such file: {path}", file=sys.stderr)
        return 2

    out = Collector()
    scan = rules.audit(path, out)

    print(f"{NAME} {VERSION}  {path.name}  {scan.n_rows:,} rows\n")
    for f in out.findings:
        print(f"  [{MARK[f['level']]}] {f['check_id']}  {f['detail']}")
        for ex in f["examples"]:
            print(f"           {ex}")
    counts = {lvl: sum(1 for f in out.findings if f["level"] == lvl)
              for lvl in ("pass", "fail", "warn", "skip", "n/a")}
    ran = sum(1 for cid in SPEC if any(f["check_id"] == cid and f["level"] in ("pass", "fail")
                                       for f in out.findings))
    print(f"\n  {ran}/{len(SPEC)} checks reached a verdict; "
          + ", ".join(f"{v} {k}" for k, v in counts.items() if v))

    if args.json:
        Path(args.json).write_text(json.dumps(
            {"tool": NAME, "version": VERSION, "file": path.name, "rows": scan.n_rows,
             "findings": out.findings}, indent=2), encoding="utf-8")
        print(f"  wrote {args.json}")

    if counts["fail"]:
        return 1
    return 0 if ran else 2


if __name__ == "__main__":
    raise SystemExit(main())
