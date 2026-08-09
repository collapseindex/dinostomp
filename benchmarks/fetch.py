"""Download two famous benchmarks and build a dinostomp pod around each.

The datasets are NOT vendored: they belong to their authors, they are large,
and a copy in this repo would be a copy that silently goes stale. This script
fetches them, writes `items.jsonl` next to a checked-in `eval.yaml`, and prints
the SHA-256 of what it fetched so a reader can tell whether they audited the
same bytes this README describes.

    python benchmarks/fetch.py
    dinostomp stomp benchmarks/gsm8k/eval.yaml
    dinostomp stomp benchmarks/truthfulqa/eval.yaml

No API key and no money: `stomp` is a static audit of the dataset and the spec.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent

SOURCES = {
    "gsm8k": "https://raw.githubusercontent.com/openai/grade-school-math/master/"
             "grade_school_math/data/test.jsonl",
    "truthfulqa": "https://raw.githubusercontent.com/sylinrl/TruthfulQA/main/TruthfulQA.csv",
    "hellaswag": "https://raw.githubusercontent.com/rowanz/hellaswag/master/data/"
                 "hellaswag_val.jsonl",
    # These two come through the HuggingFace datasets server, which pages at 100
    # rows. `fetch` handles a plain URL; PAGED names the ones that need paging.
    "arc-challenge": "https://datasets-server.huggingface.co/rows"
                     "?dataset=allenai%2Fai2_arc&config=ARC-Challenge&split=test",
    "mmlu": "https://datasets-server.huggingface.co/rows"
            "?dataset=cais%2Fmmlu&config=all&split=test",
}

# Datasets fetched a page at a time, and how many rows to take. MMLU's test
# split is 14042 items; 3000 is the first three thousand in the server's order,
# which is stated here rather than described as "MMLU".
PAGED = {"arc-challenge": 1200, "mmlu": 3000}
PAGE_ROWS = 100

CANARY = "dinostomp canary DO NOT TRAIN benchmarks"
MAX_BYTES = 100 * 1024 * 1024  # same cap the loader enforces


def fetch(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=60) as resp:  # noqa: S310 - pinned https
        blob = resp.read(MAX_BYTES + 1)
    if len(blob) > MAX_BYTES:
        raise SystemExit(f"refusing a download over {MAX_BYTES} bytes: {url}")
    return blob


def gsm8k_items(blob: bytes) -> list[dict]:
    """The reference answer is the text after the #### marker."""
    out = []
    for i, line in enumerate(blob.decode("utf-8").splitlines()):
        if not line.strip():
            continue
        row = json.loads(line)
        answer = row["answer"].rpartition("####")[2].strip().replace(",", "")
        out.append({"id": f"gsm-{i:04d}", "input": row["question"], "target": answer})
    return out


def truthfulqa_items(blob: bytes) -> list[dict]:
    """Multi-target: every correct answer the authors accept, as a list."""
    out = []
    reader = csv.DictReader(io.StringIO(blob.decode("utf-8")))
    for i, row in enumerate(reader):
        answers = [a.strip() for a in (row.get("Correct Answers") or "").split(";") if a.strip()]
        if not answers:
            continue
        out.append({"id": f"tqa-{i:04d}", "input": row["Question"], "target": answers})
    return out


def hellaswag_items(blob: bytes) -> list[dict]:
    """Sentence completion. The context is the prompt, the four endings are the
    options, and the label indexes the correct one."""
    out = []
    for i, line in enumerate(blob.decode("utf-8").splitlines()):
        if not line.strip():
            continue
        row = json.loads(line)
        endings = [e.strip() for e in row["endings"]]
        # Keyed on the LINE, not on `ind`. 433 of the file's `ind` values are
        # reused for entirely different items across split types, so `ind` is
        # not a primary key. dinostomp's loader refused the pod over it before
        # anything was scored, which is the only reason this is a comment and
        # not a silent id collision in a published number.
        out.append({"id": f"hs-{i:05d}",
                    "input": f"Complete this passage: {row['ctx'].strip()}",
                    "choices": endings,
                    "target": endings[int(row["label"])],
                    "metadata": {"ind": row["ind"], "split_type": row["split_type"]}})
    return out


def _hf_choice_items(rows: list[dict], prefix: str) -> list[dict]:
    """ARC and MMLU both arrive as {question, choices, answer/answerKey}."""
    out = []
    for i, r in enumerate(rows):
        row = r["row"]
        ch = row["choices"]
        if isinstance(ch, dict):                       # ARC: {text: [...], label: [...]}
            texts, labels = ch["text"], ch["label"]
            key = row.get("answerKey")
            if key not in labels:
                continue
            target = texts[labels.index(key)]
        else:                                          # MMLU: a plain list + an index
            texts = ch
            idx = row.get("answer")
            if not isinstance(idx, int) or not 0 <= idx < len(texts):
                continue
            target = texts[idx]
        texts = [str(t).strip() for t in texts]
        target = str(target).strip()
        if len(texts) < 2 or target not in texts:
            continue
        out.append({"id": f"{prefix}-{i:05d}", "input": str(row["question"]).strip(),
                    "choices": texts, "target": target})
    return out


BUILDERS = {
    "gsm8k": gsm8k_items,
    "truthfulqa": truthfulqa_items,
    "hellaswag": hellaswag_items,
    "arc-challenge": lambda rows: _hf_choice_items(rows, "arc"),
    "mmlu": lambda rows: _hf_choice_items(rows, "mmlu"),
}


def fetch_pages(url: str, want: int) -> tuple[list[dict], str]:
    """Page the datasets server. Returns (rows, digest of the exact bytes)."""
    rows, digest = [], hashlib.sha256()
    while len(rows) < want:
        page = fetch(f"{url}&offset={len(rows)}&length={PAGE_ROWS}")
        digest.update(page)
        got = json.loads(page).get("rows") or []
        if not got:
            break
        rows.extend(got)
        print(f"  {len(rows)} rows so far")
    return rows[:want], digest.hexdigest()


def main() -> int:
    for name, url in SOURCES.items():
        pod = HERE / name
        if not (pod / "eval.yaml").is_file():
            print(f"no pod at {pod}, skipping")
            continue
        print(f"fetching {name} from {url}")
        if name in PAGED:
            payload, digest = fetch_pages(url, PAGED[name])
        else:
            blob = fetch(url)
            payload, digest = blob, hashlib.sha256(blob).hexdigest()
        items = BUILDERS[name](payload)
        lines = [json.dumps({"_canary": CANARY})]
        lines += [json.dumps(it, ensure_ascii=False) for it in items]
        (pod / "items.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"  {len(items)} items -> {pod / 'items.jsonl'}")
        print(f"  source sha256: {digest}")
    print("\nNow:  dinostomp stomp benchmarks/<name>/eval.yaml")
    return 0


if __name__ == "__main__":
    sys.exit(main())
