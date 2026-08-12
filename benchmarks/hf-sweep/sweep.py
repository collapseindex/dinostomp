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

import argparse
import json
import sys
import time
import urllib.error
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
# NO NAMED BENCHMARKS HERE. An early version searched "mmlu", and 23 of 35
# audited files came back as MMLU variants: a base-rate estimate over one
# benchmark, dressed as an estimate over the ecosystem. A search term that names
# an artifact returns that artifact's derivatives, so the term chooses the
# answer.
SEARCH_TERMS = ("multiple choice", "exam questions", "quiz",
                # Not MCQ vocabulary, so these reach shapes the loader has
                # never met and datasets that never use the phrase.
                "evaluation benchmark", "question answering", "reasoning benchmark",
                "llm eval", "test set", "leaderboard", "safety benchmark",
                "instruction following", "reading comprehension", "science questions")

# No upstream family may contribute more than this many audited files. Without
# it one prolific re-uploader sets the rate for the whole ecosystem.
MAX_PER_FAMILY = 3

# Upstream families. Five of eight hits in the first run were
# `joey234/mmlu-*-neg` variants: one upstream artifact counted five times. A
# rate over those is a rate over one dataset, so the report gives both.
FAMILIES = ("mmlu", "truthfulqa", "truthful_qa", "commonsenseqa", "commonsense_qa",
            "hellaswag", "arc", "race", "openbookqa", "boolq", "winogrande",
            "piqa", "siqa", "gsm8k", "math", "logiqa", "sciq", "medmcqa",
            "medqa", "agieval", "bbh", "big-bench", "squad", "drop", "quartz",
            "copa", "anli", "wmdp", "gpqa", "musr", "openorca")


def family(dataset: str) -> str:
    """The upstream benchmark a repo is a variant of, or the repo itself.

    Crude on purpose: it groups `joey234/mmlu-econometrics-neg` with
    `cais/mmlu` and leaves anything unrecognised alone. Over-grouping would
    understate independence, so the raw count is always printed beside it.
    """
    name = dataset.split("/")[-1].lower()
    for fam in sorted(FAMILIES, key=len, reverse=True):
        if fam in name:
            return fam
    return dataset.lower()


# Politeness and retry. The first wide run asked for 120 datasets back to back
# with no pause and recorded every failure as "unreachable": 78 of 120. Retried
# one at a time, four of the first eight answered 200 immediately. The sweep was
# measuring its own request rate and reporting it as a property of the
# ecosystem, over a denominator that had quietly shrunk to a tenth.
# 0.8s was still too fast: 58 of 64 failures in the next run were HTTP 429, so
# nearly two thirds of it never happened and the surviving sample was whatever
# the server felt like serving first. This is a free public service and the
# sweep is a courtesy guest on it.
PAUSE_SECONDS = 3.0
RETRIES = 4
# 429 means "you specifically are going too fast", which a 1.6s backoff does not
# answer. It gets its own, much longer wait.
RATE_LIMIT_BACKOFF = 20.0

# 401/404 mean gated or absent and will mean the same tomorrow. 429 and 5xx are
# the server asking for patience. Recording them in one bucket is what let a
# rate limit masquerade as a missing dataset.
PERMANENT_CODES = {401, 403, 404}


class Transient(Exception):
    """A failure worth retrying, and worth NOT writing to the log."""


def get(url: str, timeout: int = 60):
    last = None
    for attempt in range(RETRIES):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as r:  # noqa: S310
                return json.load(r)
        except urllib.error.HTTPError as exc:
            if exc.code in PERMANENT_CODES:
                raise
            last = exc
            if exc.code == 429:
                time.sleep(RATE_LIMIT_BACKOFF * (attempt + 1))
                continue
        except Exception as exc:            # noqa: BLE001 - timeouts, resets, DNS
            last = exc
        time.sleep(PAUSE_SECONDS * (2 ** attempt))
    raise Transient(f"{type(last).__name__}"
                    + (f" {last.code}" if isinstance(last, urllib.error.HTTPError) else ""))


def candidates(limit: int = 60, skip: set[str] | None = None) -> list[str]:
    """Datasets to try, newest search results first, skipping ones already seen.

    `skip` carries the append-only log forward: re-running the sweep should
    WIDEN the sample rather than re-audit the same top-of-search results, which
    is what made every run report a number about the same thirty datasets.
    """
    skip = skip or set()
    seen: set[str] = set()
    out: list[str] = []
    for term in SEARCH_TERMS:
        q = urllib.parse.urlencode({"search": term, "limit": 60})
        try:
            rows = get(f"https://huggingface.co/api/datasets?{q}")
        except Exception:      # noqa: BLE001 - one dead query must not end the sweep
            continue
        for d in rows:
            if d["id"] not in seen and d["id"] not in skip:
                seen.add(d["id"])
                out.append(d["id"])
    return out[:limit]


def load_log() -> dict:
    """Every dataset any run has resolved, keyed by id. Append-only."""
    path = HERE / "SWEEP-LOG.jsonl"
    if not path.is_file():
        return {}
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rec = json.loads(line)
            out[rec["dataset"]] = rec
    return out


def append_log(records: list[dict]) -> None:
    path = HERE / "SWEEP-LOG.jsonl"
    with path.open("a", encoding="utf-8", newline="\n") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n")
            fh.flush()


def first_rows(repo: str) -> tuple[list | None, str, str]:
    """Rows, a split label, and WHY if there are none.

    The third value is the outcome class: "gated" and "no-splits" are facts
    about the dataset, "transient" is a fact about the network and must never
    be written to the log, because the log is what future runs skip.
    """
    time.sleep(PAUSE_SECONDS)
    try:
        info = get("https://datasets-server.huggingface.co/splits?"
                   + urllib.parse.urlencode({"dataset": repo}), timeout=45)
    except urllib.error.HTTPError as exc:
        return None, f"splits HTTP {exc.code}", "gated"
    except Transient as exc:
        return None, f"splits {exc}", "transient"
    splits = info.get("splits") or []
    if not splits:
        return None, "no splits", "no-splits"
    s = splits[0]
    time.sleep(PAUSE_SECONDS)
    try:
        d = get("https://datasets-server.huggingface.co/rows?" + urllib.parse.urlencode(
            {"dataset": repo, "config": s["config"], "split": s["split"],
             "offset": 0, "length": ROWS_PER_DATASET}), timeout=60)
    except urllib.error.HTTPError as exc:
        return None, f"rows HTTP {exc.code}", "gated"
    except Transient as exc:
        return None, f"rows {exc}", "transient"
    return ([r["row"] for r in d.get("rows", [])],
            f"{s['config']}/{s['split']}", "ok")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--limit", type=int, default=60,
                    help="datasets to try this run (default 60)")
    ap.add_argument("--fresh", action="store_true",
                    help="ignore the log and re-audit from the top of search")
    args = ap.parse_args()

    RAW.mkdir(parents=True, exist_ok=True)
    log = {} if args.fresh else load_log()
    repos = candidates(args.limit, skip=set(log))
    print(f"  {len(log)} datasets already in the log; trying {len(repos)} new, "
          f"reading {ROWS_PER_DATASET} rows each\n")

    audited = refused = 0
    fired: Counter = Counter()
    refused_by: Counter = Counter()
    refusals: list[dict] = []
    hits = []
    new_records: list[dict] = []
    transient = capped = 0
    per_family = Counter(r["family"] for r in log.values()
                         if r["outcome"] == "audited")
    for repo in repos:
        if per_family[family(repo)] >= MAX_PER_FAMILY:
            capped += 1
            continue
        rows, note, why = first_rows(repo)
        if not rows:
            if why == "transient":
                # NOT logged. The log is the skip-list for future runs, so
                # writing a network hiccup here would exclude this dataset from
                # every sweep from now on: a sample that shrinks permanently
                # each time the server is busy.
                transient += 1
                print(f"  skip {repo:52} {note}  (retryable, not logged)")
                continue
            new_records.append({"dataset": repo, "outcome": "unreachable",
                                "family": family(repo), "note": note,
                                "reason": why})
            continue
        path = RAW / (repo.replace("/", "__") + ".jsonl")
        path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
                        encoding="utf-8", newline="\n")
        report, issues, _ctx = lint_dataset(path, use_extensions=False)
        if report is None:
            # The reason was previously discarded, so this pilot reported a bare
            # "refused: 15" over half its sample with nothing to act on. A
            # refusal is only a defensible design choice if you can say what was
            # ambiguous; without the reason it is indistinguishable from a
            # loader that cannot read shapes everyone else reads fine.
            why = sorted({i.check or "(unnamed)" for i in issues}) or ["(none recorded)"]
            refused_by.update(why)
            refusals.append({
                "dataset": repo,
                "checks": why,
                "columns": sorted(rows[0].keys())[:14],
                "message": issues[0].message if issues else "",
            })
            # The audit declined to guess a column mapping. This is the number
            # that decides whether unattended breadth is survivable: a tool that
            # guesses here produces confident findings about the wrong columns.
            refused += 1
            new_records.append({"dataset": repo, "outcome": "refused",
                                "family": family(repo), "note": note,
                                "checks": why,
                                "columns": sorted(rows[0].keys())[:14]})
            continue
        audited += 1
        gates = sorted(f["id"] for f in report["findings"]
                       if f["level"] == "fail" and f["id"] in GATES)
        for g in gates:
            fired[g] += 1
        if gates:
            hits.append((repo, note, gates))
            print(f"  FLAG {repo:52} {gates}  ({note})")
        new_records.append({"dataset": repo, "outcome": "audited",
                            "family": family(repo), "note": note, "gates": gates})
        per_family[family(repo)] += 1

    unreachable = len(repos) - audited - refused - transient - capped
    print(f"\n  audited {audited}, refused-to-guess {refused}, "
          f"gated/absent {unreachable}, retryable {transient}, "
          f"skipped at family cap {capped}")
    if audited:
        print(f"  datasets with >=1 GATING finding: {len(hits)} of {audited} "
              f"= {len(hits)/audited:.0%}   (lower bound: first {ROWS_PER_DATASET} rows only)")
    print(f"  by check: {dict(fired.most_common())}")
    if refused_by:
        print(f"  refusals by reason: {dict(refused_by.most_common())}")

    append_log(new_records)
    everything = {**log, **{r["dataset"]: r for r in new_records}}
    cum = Counter(r["outcome"] for r in everything.values())
    cum_hits = [r for r in everything.values() if r.get("gates")]
    cum_audited = cum["audited"]

    # The rate that matters is over independent artifacts. Counting five
    # `mmlu-*-neg` variants as five observations of the ecosystem overstates
    # both the sample and the finding rate.
    fam_audited = {r["family"] for r in everything.values() if r["outcome"] == "audited"}
    fam_hits = {r["family"] for r in cum_hits}

    print(f"\n  CUMULATIVE over {len(everything)} datasets seen in all runs")
    print(f"    audited {cum_audited}, refused {cum['refused']}, "
          f"unreachable {cum['unreachable']}")
    if cum_audited:
        print(f"    with a gating finding: {len(cum_hits)} of {cum_audited} "
              f"= {len(cum_hits) / cum_audited:.0%} of files")
    if fam_audited:
        print(f"    deduplicated to upstream families: {len(fam_hits)} of "
              f"{len(fam_audited)} = {len(fam_hits) / len(fam_audited):.0%}"
              f"   <- the honest rate")

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
        "cumulative": {
            "datasets_seen": len(everything),
            "audited": cum_audited,
            "refused": cum["refused"],
            "unreachable": cum["unreachable"],
            "with_gating_finding": len(cum_hits),
            "upstream_families_audited": len(fam_audited),
            "upstream_families_with_finding": len(fam_hits),
        },
        "by_check": dict(fired),
        "refused_by_reason": dict(refused_by),
        "refusals": refusals,
        "rows_read_per_dataset": ROWS_PER_DATASET,
        "hits": [{"dataset": r, "split": n, "checks": g} for r, n, g in hits],
    }, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"  wrote {out.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
