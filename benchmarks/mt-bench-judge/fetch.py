"""Fetch MT-Bench human judgments: an external answer key for a JUDGE check.

    python benchmarks/mt-bench-judge/fetch.py
    python benchmarks/mt-bench-judge/compare.py

WHY THIS EXISTS. Both other external calibrations in this repository grade checks
that read a dataset at rest. The run, scorer and judge families are the ones with
the least prior art and the strongest claims, and until now their entire evidence
base was planted trials we wrote and clean pods we chose: exactly the self-scored
arrangement this project complains about elsewhere, applied to the part a reader
has most reason to doubt.

\\citet{zheng2023judging} published 3,355 pairwise preference votes from 65 human
annotators, and separately the decisions GPT-4 made as a judge on the same
comparisons. The judge has already been run and its verdicts recorded, so this
calibration costs no API spend and no model: it is a join between somebody else's
answer key and somebody else's judge.

WHAT IT CAN AND CANNOT MEASURE, before any number appears.

  J1  judge agrees with cases whose verdict is known   <- reachable
  J2  judge invariant to content-free perturbations    <- NOT reachable here
  J3  judge agrees with itself on identical input      <- NOT reachable here
  J4  judge does not favour its own family             <- NOT reachable here

J2 needs the same comparison presented in both orders. The release records **0 of
2,400** GPT-4 comparisons in both orders, so position bias cannot be measured
from it however much one would like to; J2 keeps exactly the self-scored evidence
it had. J3 needs the same input graded twice and J4 needs a second judge family.
Publishing a judge-side calibration and letting a reader assume it covers all
four would be worse than not publishing one.

THE KEY IS NOISIER THAN A CONSTRUCTED ONE. dinostomp's judge probe uses cases
whose correct verdict is true by construction. A human majority vote is not that:
annotators disagree, so the key has its own error rate, and a judge cannot be
held to a standard the annotators do not meet themselves. `compare.py` therefore
computes a leave-one-out human baseline on the identical statistic and prints it
beside the judge's number. Without that control the judge's score is
uninterpretable in either direction.

Source: https://huggingface.co/datasets/lmsys/mt_bench_human_judgments (CC-BY-4.0)
Not vendored; `data/raw/` is gitignored.
"""

from __future__ import annotations

import pathlib
import sys
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent
RAW = HERE / "data" / "raw"
BASE = "https://huggingface.co/datasets/lmsys/mt_bench_human_judgments/resolve/main/data/"
FILES = {
    "human.parquet": "human-00000-of-00001-25f4910818759289.parquet",
    "gpt4_pair.parquet": "gpt4_pair-00000-of-00001-c0b431264a82ddc0.parquet",
}


def main() -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    for local, remote in FILES.items():
        dest = RAW / local
        if dest.is_file():
            print(f"  cached   {local} ({dest.stat().st_size/1e6:.1f} MB)")
            continue
        print(f"  fetching {local} ...")
        with urllib.request.urlopen(BASE + remote, timeout=300) as r:  # noqa: S310 - pinned https
            dest.write_bytes(r.read())
        print(f"  wrote    {local} ({dest.stat().st_size/1e6:.1f} MB)")
    try:
        import pyarrow.parquet as pq
    except ImportError:
        print("\n  pyarrow is needed to read these; pip install pyarrow", file=sys.stderr)
        return 2
    for local in FILES:
        t = pq.read_table(RAW / local)
        print(f"  {local}: {t.num_rows:,} rows, columns {t.column_names}")
    print("\n  next: python benchmarks/mt-bench-judge/compare.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
