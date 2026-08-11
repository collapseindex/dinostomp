"""A read-only pilot: how often does a public dataset carry a gating defect?

    python benchmarks/hf-sweep/sweep.py

WHAT THIS IS FOR. Twenty-five benchmark pods were hand-picked, and nine of them
turned out to carry a repeated option. That is a striking rate and a biased
sample: they were chosen because they are well known, and a hand-picked
twenty-five cannot tell you the base rate across the ecosystem. This measures a
wider, less curated slice.

WHAT IT DOES NOT DO. It files nothing, opens nothing, and contacts no
maintainer. It fetches public rows through the HuggingFace datasets-server,
hands each file to `lint_dataset` exactly as a user would, and counts. Anything
beyond counting is a decision for a person.

THREE LIMITS THAT BOUND EVERY NUMBER IT PRINTS.

  * It reads the FIRST 100 ROWS of one split. A duplicate at row 5,000 is
    invisible, so the rate is a lower bound and not a small one.
  * The sample is SEARCH-BIASED. It queries for multiple-choice-shaped datasets,
    which over-samples derivatives of the same few benchmarks; several hits in
    any run will be variants of one upstream artifact and are not independent
    observations of anything.
  * A gating flag is a FACT, not a verdict. Two byte-identical options is a
    fact. Whether it matters to that dataset's maintainer is not something this
    or any script decides.

The corpus here is the live internet, so re-running gives different numbers.
RESULT.json records one dated run rather than pretending to a stable measurement.
"""

from __future__ import annotations

import json
import sys
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from dinostomp.lint import lint_dataset  # noqa: E402

HERE = Path(__file__).resolve().parent
RAW = HERE / "data" / "raw"

# Invariants only. A sweep is exactly the setting where a diagnostic's
# false-alarm rate stops being harmless, so diagnostics are not counted here.
GATES = {"S1", "S2", "S5", "S6", "S7"}
ROWS_PER_DATASET = 100
SEARCH_TERMS = ("multiple choice", "mmlu", "commonsense qa", "exam questions",
                "benchmark multiple-choice", "quiz")


def get(url: str, timeout: int = 60):
    with urllib.request.urlopen(url, timeout=timeout) as r:  # noqa: S310 - pinned https
        return json.load(r)


def candidates(limit: int = 60) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for term in SEARCH_TERMS:
        q = urllib.parse.urlencode({"search": term, "limit": 30})
        try:
            rows = get(f"https://huggingface.co/api/datasets?{q}")
        except Exception:      # noqa: BLE001 - one dead query must not end the sweep
            continue
        for d in rows:
            if d["id"] not in seen:
                seen.add(d["id"])
                out.append(d["id"])
    return out[:limit]


def first_rows(repo: str) -> tuple[list | None, str]:
    try:
        info = get("https://datasets-server.huggingface.co/splits?"
                   + urllib.parse.urlencode({"dataset": repo}), timeout=45)
    except Exception as exc:   # noqa: BLE001
        return None, f"splits unavailable ({type(exc).__name__})"
    splits = info.get("splits") or []
    if not splits:
        return None, "no splits"
    s = splits[0]
    try:
        d = get("https://datasets-server.huggingface.co/rows?" + urllib.parse.urlencode(
            {"dataset": repo, "config": s["config"], "split": s["split"],
             "offset": 0, "length": ROWS_PER_DATASET}), timeout=60)
    except Exception as exc:   # noqa: BLE001
        return None, f"rows unavailable ({type(exc).__name__})"
    return [r["row"] for r in d.get("rows", [])], f"{s['config']}/{s['split']}"


def main() -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    repos = candidates()
    print(f"  {len(repos)} candidate datasets, reading {ROWS_PER_DATASET} rows each\n")

    audited = refused = 0
    fired: Counter = Counter()
    hits = []
    for repo in repos:
        rows, note = first_rows(repo)
        if not rows:
            continue
        path = RAW / (repo.replace("/", "__") + ".jsonl")
        path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
                        encoding="utf-8", newline="\n")
        report, _issues, _ctx = lint_dataset(path, use_extensions=False)
        if report is None:
            # The audit declined to guess a column mapping. This is the number
            # that decides whether unattended breadth is survivable: a tool that
            # guesses here produces confident findings about the wrong columns.
            refused += 1
            continue
        audited += 1
        gates = sorted(f["id"] for f in report["findings"]
                       if f["level"] == "fail" and f["id"] in GATES)
        for g in gates:
            fired[g] += 1
        if gates:
            hits.append((repo, note, gates))
            print(f"  FLAG {repo:52} {gates}  ({note})")

    unreachable = len(repos) - audited - refused
    print(f"\n  audited {audited}, refused-to-guess {refused}, unreachable {unreachable}")
    if audited:
        print(f"  datasets with >=1 GATING finding: {len(hits)} of {audited} "
              f"= {len(hits)/audited:.0%}   (lower bound: first {ROWS_PER_DATASET} rows only)")
    print(f"  by check: {dict(fired.most_common())}")

    out = HERE / "RESULT.json"
    out.write_text(json.dumps({
        "note": "PILOT. The corpus is the live internet, so re-running gives different "
                "numbers. This records one dated run, not a stable measurement.",
        "limits": ["first 100 rows of one split only, so rates are a lower bound",
                   "search-biased sample; several hits are variants of one upstream dataset",
                   "a gating flag is a fact about the file, not a verdict about the dataset"],
        "candidates": len(repos), "audited": audited,
        "refused_to_guess_mapping": refused, "unreachable": unreachable,
        "datasets_with_gating_finding": len(hits),
        "by_check": dict(fired),
        "rows_read_per_dataset": ROWS_PER_DATASET,
        "hits": [{"dataset": r, "split": n, "checks": g} for r, n, g in hits],
    }, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"  wrote {out.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
