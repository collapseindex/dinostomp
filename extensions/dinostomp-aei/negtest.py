"""The evidence tax, collected.

    python extensions/dinostomp-aei/negtest.py

Two assertions per check, and the second is the one that matters:

  CLEAN   the conforming release produces no fail and no warn
  MUTANT  each planted defect produces a fail FROM ITS OWN CHECK

A rule that fires on the mutant and also on the clean file has proved nothing
except that it fires. A rule that fires on somebody else's mutant has proved
that the finding it reports is not the finding it names. Both are failures here.
"""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from dinostomp_aei import rules  # noqa: E402

FIX = HERE / "dinostomp_aei" / "fixtures"
MUTANTS = ("A1", "A2", "A3", "A4", "A5", "A6", "A7", "A8", "A9", "A10")


class Collect:
    def __init__(self) -> None:
        self.by_level: dict = defaultdict(list)

    def finding(self, cid, level, detail, **kw) -> None:
        self.by_level[level].append((cid, detail))


def audit(path: Path) -> Collect:
    c = Collect()
    rules.audit(path, c)
    return c


def main() -> int:
    problems: list[str] = []

    clean = audit(FIX / "clean.csv")
    loud = clean.by_level["fail"] + clean.by_level["warn"]
    print(f"CLEAN  {'ok' if not loud else 'NOISY'}  "
          f"{len(clean.by_level['pass'])} pass, {len(clean.by_level['skip'])} skip, "
          f"{len(loud)} fail/warn")
    for cid, detail in loud:
        print(f"         {cid}: {detail[:110]}")
        problems.append(f"clean fixture triggered {cid}")

    for check in MUTANTS:
        path = FIX / f"mutant_{check}.csv"
        if not path.is_file():
            problems.append(f"{check}: no mutant fixture")
            print(f"MUTANT {check}: MISSING")
            continue
        got = audit(path)
        loud = got.by_level["fail"] + got.by_level["warn"]
        mine = [d for cid, d in loud if cid == check]
        others = sorted({cid for cid, _ in loud if cid != check})
        # A10's planted collision also changes a partition group's membership,
        # so A6 legitimately has something to say about that file. Collateral is
        # only a problem when the check under test stays silent.
        status = "FIRES" if mine else "MISS "
        if not mine:
            problems.append(f"{check}: planted defect did not fire its own check")
        print(f"MUTANT {check}: {status}"
              + (f"  {mine[0][:96]}" if mine else "")
              + (f"   [also: {', '.join(others)}]" if others else ""))

    print(f"\n{len(problems)} problem(s)")
    for p in problems:
        print(f"  - {p}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
