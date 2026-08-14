"""Cross-artifact consistency: does this repository agree with itself?

    python scripts/check_consistency.py          # report
    python scripts/check_consistency.py --strict # exit nonzero on any disagreement

Individual tests already pin individual numbers. This asks the question none of
them ask: do the SAME facts, stated in different files by different passes,
still say the same thing. Every stale-number defect in this repo's own ledger
had that shape (a caption that drifted from the registry, a footer claiming
thirty findings against forty-one, a scorecard from a previous version), and
each was found by a person noticing rather than by a check.

WHAT IT DOES NOT DO. It does not fix anything, and it does not gate the build
by default. It prints disagreements and names both sides, because a consistency
checker that silently repairs is a consistency checker that hides the fact that
two files disagreed.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))


def read(name: str) -> str:
    path = ROOT / name
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def check_version() -> list[str]:
    """One version, five places."""
    from dinostomp import __version__

    bad = []
    sources = {
        "pyproject.toml": re.search(r'^version = "([^"]+)"', read("pyproject.toml"), re.M),
        "CITATION.cff": re.search(r"^version: (.+)$", read("CITATION.cff"), re.M),
        "README badge": re.search(r"<sub>v([0-9.]+) ", read("README.md")),
        "README action ref": re.search(r"uses: collapseindex/dinostomp@v([0-9.]+)", read("README.md")),
    }
    for where, match in sources.items():
        if not match:
            bad.append(f"version: {where} does not state one at all")
        elif match.group(1).strip() != __version__:
            bad.append(f"version: {where} says {match.group(1).strip()}, package says {__version__}")
    latest = re.search(r"^### v([0-9.]+) ", read("CHANGELOG.md"), re.M)
    if latest and latest.group(1) != __version__:
        bad.append(f"version: CHANGELOG's newest entry is v{latest.group(1)}, package is {__version__}")
    return bad


def check_fingerprint() -> list[str]:
    from dinostomp.fingerprint import engine_fingerprint

    actual = engine_fingerprint()
    readme = read("README.md")
    bad = []
    if actual not in readme:
        bad.append(f"fingerprint: README does not publish {actual[:16]}...")
    short = re.search(r"engine `([0-9a-f]{16})`", readme)
    if short and not actual.startswith(short.group(1)):
        bad.append(f"fingerprint: README badge says {short.group(1)}, engine is {actual[:16]}")
    return bad


def check_check_counts() -> list[str]:
    """The battery size, everywhere it is written out."""
    from dinostomp.lint import CHECKS, SCOPE_CHECKS, SLUGS

    bad = []
    n, data_n = len(CHECKS), len(SCOPE_CHECKS["data"])
    docs = read("README.md") + read("METHODOLOGY.md") + read("FINDINGS.md")
    flat = " ".join(docs.split())
    for number, word in ((n, num_word(n)), (data_n, num_word(data_n))):
        if word is None:
            bad.append(f"checks: no english word known for {number}; extend num_word()")
    if str(n) not in flat and (num_word(n) or "").lower() not in flat.lower():
        bad.append(f"checks: the registry has {n} checks and no doc states it")
    if set(SLUGS) != {cid for cid, *_ in CHECKS}:
        bad.append("checks: SLUGS and CHECKS disagree about which checks exist")
    # Every check in the registry must appear in METHODOLOGY's published table.
    method = read("METHODOLOGY.md")
    missing = [cid for cid, *_ in CHECKS if f"| {cid} |" not in method]
    if missing:
        bad.append(f"checks: METHODOLOGY's table is missing {missing}")
    return bad


def num_word(n: int) -> str | None:
    words = {6: "six", 10: "Ten", 14: "Fourteen", 15: "Fifteen", 16: "sixteen", 17: "seventeen", 20: "twenty", 21: "twenty-one",
             25: "twenty-five", 47: "forty-seven", 57: "fifty-seven", 61: "sixty-one", 62: "sixty-two", 64: "sixty-four", 65: "sixty-five", 66: "sixty-six", 67: "sixty-seven", 68: "sixty-eight",
             92: "ninety-two"}
    return words.get(n)


_ONES = ["zero", "one", "two", "three", "four", "five", "six", "seven",
         "eight", "nine", "ten", "eleven", "twelve", "thirteen", "fourteen",
         "fifteen", "sixteen", "seventeen", "eighteen", "nineteen"]
_TENS = {20: "twenty", 30: "thirty", 40: "forty", 50: "fifty", 60: "sixty",
         70: "seventy", 80: "eighty", 90: "ninety"}


def spell(n: int) -> str | None:
    """English for a count, so prose can be checked as strictly as a table.

    The previous version of this was a dict covering 23 to 27, written when
    that was the range of interest. Everything outside it returned None, and
    every check guarded with `if spelled` then silently did nothing. A lookup
    that stops answering as the project grows is worse than no lookup: it turns
    a check into a no-op exactly when the number it guards has moved.
    """
    if n < 0 or n > 99:
        return None
    if n < 20:
        return _ONES[n]
    tens, ones = divmod(n, 10)
    base = _TENS[tens * 10]
    return base if not ones else f"{base}-{_ONES[ones]}"


def check_prose_counts() -> list[str]:
    """Counts written out in sentences, which no table-shaped check can see.

    The README advertised "the forty-seven findings against itself" while the
    ledger held sixty-three. This is the SECOND time that sentence went stale:
    CHANGELOG v0.42.0 records it sitting at forty-one for six releases. It was
    fixed both times by correcting the number, which is the fix that already
    failed once, so it is now checked instead.
    """
    counts = json.loads(read("findings.json") or "{}").get("counts", {})
    d = counts.get("D")
    if d is None:
        return ["prose: findings.json has no D count to check against"]

    # CHANGELOG is deliberately excluded: its past entries quote the numbers
    # that were true when written, and rewriting history to match the present
    # is the opposite of what a changelog is for.
    total = counts.get("total")

    def ok(token: str, want: int) -> bool:
        t = token.lower().replace(",", "")
        return t in {str(want), spell(want)}

    # Every phrasing below was found stale in the README at least once. The
    # first version of this check knew only "findings against itself" and
    # therefore missed four stale numbers in the page's credibility paragraph,
    # including "forty-seven of the eighty-nine" sitting directly under a table
    # that read 66 and 116. A checker aimed at one sentence guards one sentence.
    PATTERNS = (
        (r"([\w-]+) findings against itself", "D", "findings against itself"),
        (r"([\w-]+) self-found defects", "D", "self-found defects"),
        (r"([\w-]+) of the ([\w,-]+) are against this tool", "D+total",
         "are against this tool"),
    )
    bad = []
    for name in ("README.md", "METHODOLOGY.md", "FINDINGS.md", "CONTRIBUTING.md"):
        text = " ".join(read(name).split())
        for pattern, kind, label in PATTERNS:
            for m in re.finditer(pattern, text):
                first = m.group(1).lower()
                if first in {"the", "its", "our", "these", "those", "all"}:
                    continue
                if kind == "D" and not ok(first, d):
                    bad.append(f"prose: {name} says {first!r} {label}, "
                               f"the ledger holds {d} ({spell(d)})")
                elif kind == "D+total":
                    if not ok(first, d):
                        bad.append(f"prose: {name} says {first!r} {label}, "
                                   f"the ledger holds {d} ({spell(d)})")
                    if total and not ok(m.group(2), total):
                        bad.append(f"prose: {name} says {m.group(2)!r} entries in "
                                   f"{label!r}, the ledger holds {total}")
    return bad


def check_referenced_tags() -> list[str]:
    """Every `@vX.Y.Z` a doc tells someone to install must be a tag that exists.

    The README carried `dinostomp@v0.51.0` in a copy-pasteable install block.
    That tag was never cut, so the one instruction a new user follows first
    failed, three lines above a sentence calling exactly that "a credibility
    wound in a document whose whole thesis is receipts".

    Checked rather than corrected, because correcting it is the fix that already
    failed: a version reference goes stale silently every time one is skipped.
    """
    import subprocess
    try:
        out = subprocess.run(["git", "tag"], cwd=ROOT, capture_output=True,
                             text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return []                      # no git available: not this check's business
    tags = {t.strip() for t in out.stdout.splitlines() if t.strip()}
    if not tags:
        return []
    bad = []
    for name in ("README.md", "AUTHORING.md", "CONTRIBUTING.md", "METHODOLOGY.md"):
        text = read(name)
        for ref in sorted(set(re.findall(r"dinostomp@(v[0-9]+\.[0-9]+\.[0-9]+)", text))):
            if ref not in tags:
                bad.append(f"tags: {name} tells the reader to install {ref}, "
                           f"which is not a tag in this repository")
    return bad


def check_findings() -> list[str]:
    """The ledger, its feed, the README's summary, and the scorecard in FINDINGS."""
    feed = json.loads(read("findings.json") or "{}")
    counts = feed.get("counts", {})
    readme, findings = read("README.md"), read("FINDINGS.md")
    bad = []
    total = counts.get("total")
    if total and f"{total} entries, all permanent" not in readme:
        bad.append(f"findings: README does not state {total} entries")
    for series in "FDN":
        n = counts.get(series)
        if n is None:
            continue
        if f"| **{series}** | {n} |" not in readme:
            bad.append(f"findings: README's {series} row is not {n}")
        if f"**{n}**" not in findings:
            bad.append(f"findings: FINDINGS.md scorecard does not state {n} for {series}")
    return bad


def check_trials() -> list[str]:
    from trials.run_trials import CLEAN_TRIALS, TRIALS

    # CONTRIBUTING sat at "86 of 86" for six releases, in the one section whose
    # job is to recruit outside attackers.
    #
    # The first attempt to cover it just added the file to this concatenation,
    # which does nothing: the old test asked whether the CURRENT number appears
    # ANYWHERE across all docs, and the README satisfies that on its own. A
    # stale count in a second file is invisible to an existence check. Each
    # file that quotes a trial count is now checked on its own.
    FILES = ("README.md", "METHODOLOGY.md", "CONTRIBUTING.md")

    def without_history(md: str) -> str:
        """Drop release-history sections before checking counts.

        METHODOLOGY's `## Status` section is a changelog, and its v0.12.0 entry
        correctly reads "30 defects at that release, 30 of 30 caught; the suite
        has grown since". A past number stated as past is not stale, and
        rewriting history to match the present is the opposite of what a
        release log is for. This is the same exemption CHANGELOG.md gets in
        check_prose_counts.
        """
        out, skipping = [], False
        for line in md.split("\n"):
            if line.startswith("## "):
                skipping = line.strip().lower() in ("## status", "## roadmap")
            if not skipping:
                out.append(line)
        return "\n".join(out)

    bad = []
    for name in FILES:
        text = " ".join(without_history(read(name)).split())
        # The docs phrase it three ways: "N of N planted defects", "N of N
        # caught", "N of N defects caught". Matching only the first let a stale
        # README through the version of this check that was supposed to fix it.
        for m in re.finditer(r"(\d+) of (\d+)(?= planted defects| caught| defects caught)",
                             text):
            if (int(m.group(1)), int(m.group(2))) != (len(TRIALS), len(TRIALS)):
                bad.append(f"trials: {name} says {m.group(1)} of {m.group(2)} defects "
                           f"caught, run_trials.py has {len(TRIALS)}")
        for m in re.finditer(r"(\d+) of (\d+) clean pods", text):
            if (int(m.group(1)), int(m.group(2))) != (len(CLEAN_TRIALS), len(CLEAN_TRIALS)):
                bad.append(f"trials: {name} says {m.group(1)} of {m.group(2)} clean pods, "
                           f"run_trials.py has {len(CLEAN_TRIALS)}")

    docs = "".join(read(n) for n in FILES)
    if f"{len(TRIALS)} of {len(TRIALS)}" not in docs:
        bad.append(f"trials: docs do not state {len(TRIALS)} of {len(TRIALS)} caught")
    if f"{len(CLEAN_TRIALS)} of {len(CLEAN_TRIALS)}" not in docs:
        bad.append(f"trials: docs do not state {len(CLEAN_TRIALS)} clean pods")
    return bad


def check_benchmarks() -> list[str]:
    """The audited-benchmark count the README claims, against the pods on disk."""
    pods = sorted(p.name for p in (ROOT / "benchmarks").iterdir()
                  if p.is_dir() and (p / "eval.yaml").is_file())
    readme = " ".join(read("README.md").split())
    bad = []
    claimed = re.search(r"Across \*\*(\w+[\w-]*) benchmark", readme)
    if not claimed:
        bad.append("benchmarks: the README no longer states how many were audited")
    else:
        word = claimed.group(1).lower()
        spelled = spell(len(pods))
        if word not in {str(len(pods)), spelled}:
            bad.append(f"benchmarks: README says {word!r}, {len(pods)} pods on disk")
        findings = read("FINDINGS.md")
        # No `if spelled` guard: spell() answers for every count this project
        # will ever have, and guarding on it is what made this check vanish.
        if spelled.capitalize() not in findings and str(len(pods)) not in findings:
            bad.append(f"benchmarks: FINDINGS.md does not state {len(pods)} either")
    return bad


def check_corpus() -> list[str]:
    """taxonomy -> manifest -> scorecard -> leaderboard -> the prose quoting them."""
    sys.path.insert(0, str(ROOT / "corpus"))
    import taxonomy

    bad = []
    summary = taxonomy.summary()
    corpus_readme = read("corpus/README.md")
    if f"| `literature` | {summary['by_source'].get('literature', 0)} |" not in corpus_readme:
        bad.append("corpus: README's source table disagrees with taxonomy.py")
    if f"{summary['n_blind_spots']} of the twenty-one defect classes" not in corpus_readme and \
            f"Nine of the twenty-one" not in corpus_readme:
        bad.append(f"corpus: README does not state {summary['n_blind_spots']} blind-spot classes")

    for folder in sorted((ROOT / "corpus" / "instances").iterdir()):
        if not folder.is_dir():
            continue
        manifest = json.loads((folder / "MANIFEST.json").read_text(encoding="utf-8"))
        registry = read("corpus/SPLITS.md")
        if folder.name not in registry and folder.name.split("-")[0] not in registry:
            bad.append(f"corpus: split {folder.name} is not in SPLITS.md")
        commitment = manifest.get("labels_sha256", "")
        if commitment and commitment[:16] not in registry:
            bad.append(f"corpus: SPLITS.md does not carry {folder.name}'s commitment")

    cards = sorted((ROOT / "corpus" / "scorecards").glob("*.json"))
    from dinostomp import __version__

    for path in cards:
        card = json.loads(path.read_text(encoding="utf-8"))
        if card["detector"].startswith("dinostomp") and card["detector"] != f"dinostomp {__version__}":
            bad.append(f"corpus: {path.name} is from {card['detector']}, package is {__version__}")
    board = read("corpus/LEADERBOARD.md")
    for path in cards:
        card = json.loads(path.read_text(encoding="utf-8"))
        if card["detector"] not in board:
            bad.append(f"corpus: {card['detector']} has a scorecard but no leaderboard row")
    return bad


def check_quoted_numbers() -> list[str]:
    """Numbers the corpus README quotes in a fenced block, against the scorecard."""
    card_path = ROOT / "corpus" / "scorecards" / "dinostomp.json"
    if not card_path.is_file():
        return ["corpus: no dinostomp scorecard to check the quoted block against"]
    card = json.loads(card_path.read_text(encoding="utf-8"))
    text = read("corpus/README.md")
    bad = []
    for label, key in (("recall, classes it has a check for", "recall_covered"),
                       ("false alarms on clean instances", "false_alarm_rate_on_clean")):
        value = card.get(key)
        if value is None:
            continue
        if f"{value:.1%}" not in text:
            bad.append(f"corpus README quotes a stale {label}: scorecard says {value:.1%}")
    return bad


def check_dead_references() -> list[str]:
    """Files named in docs that do not exist."""
    bad = []
    for name in ("README.md", "corpus/README.md", "METHODOLOGY.md", "CONTRIBUTING.md"):
        text = read(name)
        for target in set(re.findall(r"\]\(([A-Za-z0-9_./-]+\.(?:md|json|py|yml|yaml))\)", text)):
            base = (ROOT / name).parent
            if not (base / target).exists() and not (ROOT / target).exists():
                bad.append(f"links: {name} points at {target}, which does not exist")
    return bad


def check_no_secrets_tracked() -> list[str]:
    """The rule that costs the most if it ever fails."""
    proc = subprocess.run(["git", "ls-files"], capture_output=True, text=True, cwd=str(ROOT))
    bad = []
    for line in proc.stdout.splitlines():
        low = line.lower()
        if "withheld" in low or low.endswith(".env") or "holdback" in low or "nonce" in low:
            bad.append(f"SECRETS: {line} is tracked by git")
    return bad


CHECKS = [
    ("version", check_version),
    ("engine fingerprint", check_fingerprint),
    ("check registry", check_check_counts),
    ("findings ledger", check_findings),
    ("prose counts", check_prose_counts),
    ("referenced tags", check_referenced_tags),
    ("trials", check_trials),
    ("benchmarks", check_benchmarks),
    ("corpus", check_corpus),
    ("quoted numbers", check_quoted_numbers),
    ("links", check_dead_references),
    ("secrets", check_no_secrets_tracked),
]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--strict", action="store_true", help="exit nonzero on any disagreement")
    args = ap.parse_args()

    total = 0
    for name, fn in CHECKS:
        try:
            problems = fn()
        except Exception as exc:  # noqa: BLE001 - a checker that crashes is a failed check
            problems = [f"{name}: checker crashed: {type(exc).__name__}: {exc}"]
        total += len(problems)
        mark = "ok  " if not problems else "DIFF"
        print(f"  [{mark}] {name}")
        for p in problems:
            print(f"           {p}")
    print(f"\n  {total} disagreement(s) across {len(CHECKS)} area(s)")
    return 1 if (args.strict and total) else 0


if __name__ == "__main__":
    sys.exit(main())
