"""Fetch a real lm-evaluation-harness log and build this pod around it.

Same discipline as `benchmarks/fetch.py`, for the same reason: the artifact
belongs to its authors and a copy in this repo would be a copy that silently
goes stale. Nothing here is vendored. This script downloads the details file,
writes the pod's `items.jsonl` and the foreign log next to the checked-in
`eval.yaml`, and prints the SHA-256 of exactly what it downloaded.

    python benchmarks/lm-eval-import/fetch.py
    dinostomp import benchmarks/lm-eval-import/eval.yaml \\
        benchmarks/lm-eval-import/lm_eval_arc_challenge.jsonl \\
        --model Corianas/111m --item-id-field example --score-field acc_norm
    dinostomp stomp benchmarks/lm-eval-import/eval.yaml

`--score-field` is not optional and the tool will refuse without it. The log
carries both `acc` and `acc_norm`; they disagree on 221 of 1172 items and the
Open LLM Leaderboard published `acc_norm`. See D-023 in FINDINGS.md.

Requires `pyarrow` (the details files are parquet). It is not a dinostomp
dependency: no part of the battery needs it, only this fetcher does.
"""

from __future__ import annotations

import hashlib
import io
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent

DATASET = "open-llm-leaderboard-old/details_Corianas__111m"
FILE = ("2023-07-19T13:48:53.093937/details_harness|arc:challenge|25_"
        "2023-07-19T13:48:53.093937.parquet")

CANARY = "dinostomp canary DO NOT TRAIN lm-eval-import"

# Dropped on the way in: `input_tokens` and `cont_tokens` are ~40MB of tokenised
# prompt that carries no evidentiary weight for anything this pod checks. Every
# field a score could be derived from is kept, which is the part that matters.
KEEP = ("example", "query", "choices", "gold", "acc", "acc_norm", "predictions",
        "num_asked_few_shots", "num_effective_few_shots")


def main() -> int:
    try:
        import pyarrow.parquet as pq
    except ImportError:
        print("this fetcher needs pyarrow:  pip install pyarrow", file=sys.stderr)
        return 2

    url = f"https://huggingface.co/datasets/{DATASET}/resolve/main/{urllib.parse.quote(FILE)}"
    print(f"fetching {DATASET}\n  {FILE}")
    blob = urllib.request.urlopen(url, timeout=300).read()  # noqa: S310 - pinned https
    print(f"  source sha256: {hashlib.sha256(blob).hexdigest()}")
    rows = pq.read_table(io.BytesIO(blob)).to_pylist()
    print(f"  {len(rows)} rows")

    # The foreign log, in the shape another harness would hand it over.
    log = HERE / "lm_eval_arc_challenge.jsonl"
    log.write_text("\n".join(
        json.dumps({**{k: r[k] for k in KEEP},
                    "truncated": int(any(r["truncated"]))}, ensure_ascii=False)
        for r in rows) + "\n", encoding="utf-8", newline="\n")

    # The pod's items, reconstructed from the log's OWN item fields, so the pod
    # and the log describe the same 1172 items by construction rather than by a
    # join anybody has to trust.
    #
    # newline="\n": the drift boundary hashes these exact bytes, so a pod built
    # on Windows and shared would otherwise fail to re-derive anywhere else.
    lines = [json.dumps({"_canary": CANARY})]
    lines += [json.dumps({"id": r["example"], "input": r["query"],
                          "target": r["choices"][r["gold"]],
                          "choices": r["choices"]}, ensure_ascii=False) for r in rows]
    (HERE / "items.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"  -> {log.name}\n  -> items.jsonl")
    print("\nNow:  dinostomp import benchmarks/lm-eval-import/eval.yaml \\\n"
          "        benchmarks/lm-eval-import/lm_eval_arc_challenge.jsonl \\\n"
          "        --model Corianas/111m --item-id-field example --score-field acc_norm")
    return 0


if __name__ == "__main__":
    sys.exit(main())
