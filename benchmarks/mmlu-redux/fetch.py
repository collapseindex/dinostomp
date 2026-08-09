"""Fetch MMLU-Redux 2.0: 5,700 MMLU questions, re-annotated by hand.

This is the only external ground truth in the repository. Every other finding
here is self-graded, either a defect dinostomp found that nobody independently
confirmed, or a defect in dinostomp found by dinostomp. Redux was produced by
people at Edinburgh who had never heard of this tool, re-reading MMLU items and
labelling what is wrong with each one.

    python benchmarks/mmlu-redux/fetch.py
    python benchmarks/mmlu-redux/compare.py

`fetch.py` writes `items.jsonl` (the dataset, in this tool's item shape) and
`labels.jsonl` (the human annotation, kept separate on purpose). `compare.py`
runs the data-scope battery against the items and scores it against the labels.

Keeping them in two files matters: the audit must not be able to see the answer
key. It reads `items.jsonl` exactly as it would read anybody's dataset.

Reads PARQUET, one request per subject, rather than the paged rows API, which
rate-limited at 429 partway through 57 subjects. Downloads are cached under
`.cache/` so a re-run resumes instead of refetching, which is the same rule this
project applies to paid runs: never lose work you have already paid for, even
when the currency is somebody else's rate limit.

Not vendored. Source: https://huggingface.co/datasets/edinburgh-dawg/mmlu-redux-2.0
(Gema et al., 2024, "Are We Done with MMLU?"). CC-BY-4.0.
"""

from __future__ import annotations

import hashlib
import io
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
CACHE = HERE / ".cache"
DATASET = "edinburgh-dawg/mmlu-redux-2.0"
CANARY = "dinostomp canary DO NOT TRAIN mmlu-redux"


def get(url: str, *, binary: bool = False, attempts: int = 7):
    """Back off properly on 429. The first version gave up after 30s and lost
    50 subjects' worth of downloading."""
    last = "no attempt made"
    for i in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(url, timeout=180) as r:  # noqa: S310 - pinned https
                blob = r.read()
            return blob if binary else json.loads(blob.decode("utf-8"))
        except urllib.error.HTTPError as exc:
            last = f"HTTP {exc.code}"
            wait = int(exc.headers.get("Retry-After") or 0) or min(60, 5 * 2 ** (i - 1))
            if exc.code not in (429, 500, 502, 503, 504):
                break
        except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            last = f"{type(exc).__name__}: {exc}"
            wait = min(60, 5 * 2 ** (i - 1))
        if i < attempts:
            print(f"    {last}, waiting {wait}s")
            time.sleep(wait)
    raise RuntimeError(f"giving up on {url}: {last}")


def main() -> int:
    try:
        import pyarrow.parquet as pq
    except ImportError:
        print("this fetcher needs pyarrow:  pip install pyarrow", file=sys.stderr)
        return 2

    CACHE.mkdir(exist_ok=True)
    index = get("https://huggingface.co/api/datasets/"
                + urllib.parse.quote(DATASET) + "/parquet")
    configs = sorted(index)
    print(f"{len(configs)} subject(s)")

    items, labels = [], []
    for n, config in enumerate(configs, 1):
        urls = index[config].get("test") or []
        if not urls:
            print(f"  [{n:>2}/{len(configs)}] {config}: no test split, skipped")
            continue
        cached = CACHE / f"{config}.parquet"
        if not cached.is_file():
            cached.write_bytes(get(urls[0], binary=True))
        rows = pq.read_table(io.BytesIO(cached.read_bytes())).to_pylist()
        for r in rows:
            choices = list(r.get("choices") or [])
            answer = r.get("answer")
            # `answer` indexes `choices`. An out-of-range index is itself a
            # defect, and it is kept rather than dropped, so the audit meets the
            # same data a user would.
            target = (choices[answer] if isinstance(answer, int)
                      and 0 <= answer < len(choices) else "")
            iid = f"{config}-{len(items):05d}"
            items.append({"id": iid, "input": str(r.get("question") or ""),
                          "target": target, "choices": choices})
            labels.append({"id": iid, "subject": config,
                           "error_type": str(r.get("error_type") or ""),
                           "answer_index": answer,
                           "correct_answer": r.get("correct_answer"),
                           "potential_reason": r.get("potential_reason")})
        print(f"  [{n:>2}/{len(configs)}] {config}: {len(rows)} rows")

    lines = [json.dumps({"_canary": CANARY})]
    lines += [json.dumps(i, ensure_ascii=False) for i in items]
    # newline="\n": the drift boundary hashes these exact bytes.
    (HERE / "items.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    (HERE / "labels.jsonl").write_text(
        "\n".join(json.dumps(x, ensure_ascii=False) for x in labels) + "\n",
        encoding="utf-8", newline="\n")

    digest = hashlib.sha256((HERE / "items.jsonl").read_bytes()).hexdigest()
    print(f"\n  {len(items)} items -> items.jsonl   (sha256 {digest})")
    print(f"  {len(labels)} labels -> labels.jsonl")
    print("\nNow:  python benchmarks/mmlu-redux/compare.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
