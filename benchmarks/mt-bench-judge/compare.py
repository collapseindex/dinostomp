"""Score dinostomp's J1 against MT-Bench's human key, with a human baseline.

    python benchmarks/mt-bench-judge/compare.py

This calls the REAL `_judge_checks` from `dinostomp.lint`, on records shaped to
the contract J1 declares, rather than recomputing an agreement rate here. A
benchmark that scores a reimplementation of the thing it claims to score is
measuring the benchmark; ciFAIR taught this project the same lesson about
`dhash_image`.

TWO NUMBERS, NEVER ONE. The judge's agreement with the human majority is
meaningless without the rate at which the humans achieve it themselves, so a
leave-one-out baseline is computed on the identical statistic: hold out one
annotator, recompute the majority of the rest, ask whether the held-out human
agrees. That is exactly what the judge is being asked to do.
"""

from __future__ import annotations

import collections
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dinostomp.lint import THRESHOLDS, Reporter, _judge_checks  # noqa: E402

RAW = HERE / "data" / "raw"


def _load():
    import pyarrow.parquet as pq

    return (pq.read_table(RAW / "human.parquet").to_pylist(),
            pq.read_table(RAW / "gpt4_pair.parquet").to_pylist())


def _comparison(row) -> tuple:
    """Identity of a comparison, independent of which side was shown first."""
    return (row["question_id"], tuple(sorted((row["model_a"], row["model_b"]))), row["turn"])


def _winner(row) -> str:
    return row["model_a"] if row["winner"] == "model_a" else (
        row["model_b"] if row["winner"] == "model_b" else "tie")


def human_majority(rows) -> dict:
    votes = collections.defaultdict(list)
    for r in rows:
        votes[_comparison(r)].append(_winner(r))
    out = {}
    for k, v in votes.items():
        ranked = collections.Counter(v).most_common()
        if len(ranked) == 1 or ranked[0][1] > ranked[1][1]:
            out[k] = ranked[0][0]
    return out, votes


def leave_one_out(votes) -> tuple[int, int]:
    """How often one annotator agrees with the majority of the others.

    The same statistic the judge is scored on, so the two numbers are
    comparable. Unanimity is a different question and is not used here: it would
    have made the judge look better than it is by about twenty points.
    """
    hit = tot = 0
    for v in votes.values():
        if len(v) < 3:
            continue
        for i in range(len(v)):
            rest = collections.Counter(v[:i] + v[i + 1:]).most_common()
            if (len(rest) > 1 and rest[0][1] == rest[1][1]) or rest[0][0] == "tie":
                continue
            tot += 1
            hit += v[i] == rest[0][0]
    return hit, tot


def as_judge_probe(maj, gpt) -> list[dict]:
    """MT-Bench comparisons in the record shape J1 reads.

    One case per comparison. `polarity` carries the externally known answer, and
    the judge's recorded verdict is translated into the pass/fail J1 expects:
    the case asks "is the human-preferred answer the better one?", so a judge
    naming that model passes and anything else fails. A GPT-4 "tie" is a fail,
    because the humans were decisive and the judge was not.
    """
    records = []
    for key, human in maj.items():
        if human == "tie" or key not in gpt:
            continue
        qid, models, turn = key
        records.append({
            "item_id": f"q{qid}-{models[0]}-vs-{models[1]}-t{turn}",
            "key": f"q{qid}/{models[0]}|{models[1]}/turn{turn}",
            "polarity": "correct",
            "perturbation": None,
            "score": {"verdict": "pass" if gpt[key] == human else "fail"},
        })
    return records


def main() -> int:
    if not (RAW / "human.parquet").is_file():
        print("  run fetch.py first", file=sys.stderr)
        return 2
    human_rows, gpt_rows = _load()
    maj, votes = human_majority(human_rows)
    gpt = {_comparison(r): _winner(r) for r in gpt_rows}
    records = as_judge_probe(maj, gpt)

    rep = Reporter()
    probes = [{"manifest": {"probe": "judge"}, "records": records}]
    _judge_checks(rep, probes, [], {"scorer": {"kind": "judge"}})

    print(f"MT-BENCH JUDGE CALIBRATION: dinostomp J1 vs {len(votes):,} human-annotated "
          f"comparisons\n")
    for cid in ("J1", "J2", "J3", "J4"):
        f = rep.findings.get(cid)
        if f is None:
            continue
        print(f"  [{f.level:4}] {cid}  {f.detail}")

    hit, tot = leave_one_out(votes)
    agree = sum(1 for r in records if r["score"]["verdict"] == "pass")
    print(f"\n  THE CONTROL, without which the line above means nothing:")
    print(f"    judge agrees with the human majority   {agree:>5,} / {len(records):,}"
          f"  = {agree/len(records):.1%}")
    print(f"    a HUMAN agrees with the same majority   {hit:>5,} / {tot:,}"
          f"  = {hit/tot:.1%}   (leave-one-out)")
    print(f"    J1's shipped threshold                                 "
          f"= {THRESHOLDS['judge_agreement_min']:.0%}")

    ties = sum(1 for k, h in maj.items() if h != "tie" and k in gpt and gpt[k] == "tie")
    print(f"\n    of the judge's misses, {ties:,} are it calling a tie where humans decided")

    out = HERE / "RESULT.json"
    out.write_text(json.dumps({
        "comparisons_scored": len(records),
        "judge_agreement": round(agree / len(records), 4),
        "human_leave_one_out_agreement": round(hit / tot, 4),
        "human_baseline_n": tot,
        "judge_threshold": THRESHOLDS["judge_agreement_min"],
        "judge_ties_where_humans_decided": ties,
        "j1_level": rep.findings["J1"].level if "J1" in rep.findings else None,
        "not_measurable_here": {
            "J2": "0 of 2,400 GPT-4 comparisons are recorded in both presentation orders",
            "J3": "no comparison is graded twice on identical input",
            "J4": "only one judge family is present",
        },
        # newline="\n" is not cosmetic: tracked pod artifacts are LF on disk and
        # a test enforces it, because a file that re-derives differently on
        # Windows is a file whose published hash depends on the author's OS.
    }, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"\n  wrote {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
