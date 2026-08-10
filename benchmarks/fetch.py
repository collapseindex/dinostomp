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
import time
import urllib.error
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
    "arc-easy": "https://datasets-server.huggingface.co/rows"
                "?dataset=allenai%2Fai2_arc&config=ARC-Easy&split=test",
    "winogrande": "https://datasets-server.huggingface.co/rows"
                  "?dataset=allenai%2Fwinogrande&config=winogrande_xl&split=validation",
    "commonsenseqa": "https://datasets-server.huggingface.co/rows"
                     "?dataset=tau%2Fcommonsense_qa&config=default&split=validation",
    "openbookqa": "https://datasets-server.huggingface.co/rows"
                  "?dataset=allenai%2Fopenbookqa&config=main&split=test",
    "boolq": "https://datasets-server.huggingface.co/rows"
             "?dataset=google%2Fboolq&config=default&split=validation",
    "mmlu-pro": "https://datasets-server.huggingface.co/rows"
                "?dataset=TIGER-Lab%2FMMLU-Pro&config=default&split=test",
    "sciq": "https://datasets-server.huggingface.co/rows"
            "?dataset=allenai%2Fsciq&config=default&split=test",
    "medmcqa": "https://datasets-server.huggingface.co/rows"
               "?dataset=openlifescienceai%2Fmedmcqa&config=default&split=validation",
    # Added because the first thirteen were nearly all short-question, four-option
    # English MCQA, so they exercised the same checks over and over. These bring
    # shapes the battery had never met: a long passage in front of the question,
    # a free-form numeric answer with no options at all, and answer spans.
    "race": "https://datasets-server.huggingface.co/rows"
            "?dataset=ehovy%2Frace&config=high&split=test",
    "musr": "https://datasets-server.huggingface.co/rows"
            "?dataset=TAUR-Lab%2FMuSR&config=default&split=murder_mysteries",
    "logiqa": "https://datasets-server.huggingface.co/rows"
              "?dataset=lucasmccabe%2Flogiqa&config=default&split=test",
    "math500": "https://datasets-server.huggingface.co/rows"
               "?dataset=HuggingFaceH4%2FMATH-500&config=default&split=test",
    "drop": "https://datasets-server.huggingface.co/rows"
            "?dataset=ucinlp%2Fdrop&config=default&split=validation",
}

# Datasets fetched a page at a time, and how many rows to take. MMLU's test
# split is 14042 items; 3000 is the first three thousand in the server's order,
# which is stated here rather than described as "MMLU".
PAGED = {"arc-challenge": 1200, "mmlu": 3000, "arc-easy": 2400, "winogrande": 1300,
         "commonsenseqa": 1200, "openbookqa": 500, "boolq": 3000, "mmlu-pro": 3000,
         "sciq": 1000, "medmcqa": 3000,
         "race": 1500, "musr": 250, "logiqa": 650, "math500": 500, "drop": 2000}
PAGE_ROWS = 100

CANARY = "dinostomp canary DO NOT TRAIN benchmarks"
MAX_BYTES = 100 * 1024 * 1024  # same cap the loader enforces


def fetch(url: str, attempts: int = 6) -> bytes:
    """GET with backoff. The datasets server rate-limits, and a 429 halfway
    through a paged download would otherwise leave a truncated dataset on disk
    that looks complete."""
    delay = 2.0
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(url, timeout=60) as resp:  # noqa: S310 - pinned https
                blob = resp.read(MAX_BYTES + 1)
            if len(blob) > MAX_BYTES:
                raise SystemExit(f"refusing a download over {MAX_BYTES} bytes: {url}")
            return blob
        except urllib.error.HTTPError as exc:
            if exc.code not in (429, 500, 502, 503, 504) or attempt == attempts - 1:
                raise
            print(f"    HTTP {exc.code}, retrying in {delay:.0f}s")
            time.sleep(delay)
            delay *= 2
    raise SystemExit(f"gave up on {url}")


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




def winogrande_items(rows: list[dict]) -> list[dict]:
    """A sentence with a blank and two fillers. `answer` is "1" or "2"."""
    out = []
    for i, r in enumerate(rows):
        row = r["row"]
        opts = [str(row["option1"]).strip(), str(row["option2"]).strip()]
        key = str(row.get("answer") or "").strip()
        if key not in ("1", "2") or len(set(opts)) < 2:
            continue
        out.append({"id": f"wg-{i:05d}",
                    "input": f"Fill in the blank: {str(row['sentence']).strip()}",
                    "choices": opts, "target": opts[int(key) - 1]})
    return out


def boolq_items(rows: list[dict]) -> list[dict]:
    """Passage plus a yes/no question. The passage IS the item; without it the
    question is unanswerable, so it goes in the input rather than being dropped."""
    out = []
    for i, r in enumerate(rows):
        row = r["row"]
        ans = row.get("answer")
        if not isinstance(ans, bool):
            continue
        passage = str(row["passage"]).strip()
        question = str(row["question"]).strip()
        out.append({"id": f"bq-{i:05d}",
                    "input": f"{passage}\n\nQuestion: {question}?",
                    "choices": ["yes", "no"], "target": "yes" if ans else "no"})
    return out


def sciq_items(rows: list[dict]) -> list[dict]:
    """Correct answer plus three distractors as separate columns.

    Option ORDER is reconstructed here, because the source has none: SciQ ships
    the answer and three distractors as separate columns.

    Keeping the source column order put the answer at index 0 on all 1000 items,
    and `position-bias` duly reported gold overshooting position 0 by 75%. That
    was a finding about this fetcher, not about SciQ, and it cascaded into
    `surface-shortcut` too. A report whose findings are about its own loader is
    worse than no report.

    So the options are SHUFFLED, per item, from a seed derived from the item id.
    Deterministic and reproducible, position carries no information, and the
    arbitrariness is explicit rather than smuggled in as column order.
    """
    import hashlib
    import random

    out = []
    for i, r in enumerate(rows):
        row = r["row"]
        correct = str(row.get("correct_answer") or "").strip()
        opts = [correct] + [str(row.get(f"distractor{k}") or "").strip() for k in (1, 2, 3)]
        if not correct or any(not o for o in opts):
            continue
        seed = int(hashlib.sha256(f"sciq|{i}".encode()).hexdigest()[:8], 16)
        random.Random(seed).shuffle(opts)
        out.append({"id": f"sq-{i:05d}", "input": str(row["question"]).strip(),
                    "choices": opts, "target": correct})
    return out


def medmcqa_items(rows: list[dict]) -> list[dict]:
    """Four lettered option columns and an integer key."""
    out = []
    for i, r in enumerate(rows):
        row = r["row"]
        opts = [str(row.get(k) or "").strip() for k in ("opa", "opb", "opc", "opd")]
        cop = row.get("cop")
        if not isinstance(cop, int) or not 0 <= cop < 4 or any(not o for o in opts):
            continue
        out.append({"id": f"mm-{i:05d}", "input": str(row["question"]).strip(),
                    "choices": opts, "target": opts[cop]})
    return out


def mmlu_pro_items(rows: list[dict]) -> list[dict]:
    out = []
    for i, r in enumerate(rows):
        row = r["row"]
        opts = [str(o).strip() for o in (row.get("options") or [])]
        idx = row.get("answer_index")
        if not isinstance(idx, int) or not 0 <= idx < len(opts) or len(opts) < 2:
            continue
        out.append({"id": f"mp-{i:05d}", "input": str(row["question"]).strip(),
                    "choices": opts, "target": opts[idx]})
    return out


def _stem_choice_items(rows: list[dict], prefix: str, stem_field: str) -> list[dict]:
    """CommonsenseQA and OpenBookQA: {text, label} choices with a letter key."""
    out = []
    for i, r in enumerate(rows):
        row = r["row"]
        ch = row.get("choices") or {}
        texts = [str(t).strip() for t in (ch.get("text") or [])]
        labels = [str(l).strip() for l in (ch.get("label") or [])]
        key = str(row.get("answerKey") or "").strip()
        if key not in labels or len(texts) != len(labels) or len(texts) < 2:
            continue
        out.append({"id": f"{prefix}-{i:05d}", "input": str(row[stem_field]).strip(),
                    "choices": texts, "target": texts[labels.index(key)]})
    return out


def race_items(rows: list[dict]) -> list[dict]:
    """A long article, then a question, then four lettered options.

    The passage goes in the INPUT, which is the first item shape here where the
    question is a small part of what the model reads. `answer` is a letter, so
    the target is looked up rather than taken verbatim; a letter target would
    make every option-order check meaningless.
    """
    out = []
    for i, r in enumerate(rows):
        row = r["row"]
        opts = [str(o).strip() for o in (row.get("options") or [])]
        letter = str(row.get("answer") or "").strip().upper()
        idx = "ABCDE".find(letter)
        if not opts or idx < 0 or idx >= len(opts):
            continue
        article = str(row.get("article") or "").strip()
        question = str(row.get("question") or "").strip()
        out.append({"id": f"race-{i:05d}",
                    "input": f"{article}\n\nQuestion: {question}",
                    "choices": opts, "target": opts[idx]})
    return out


def musr_items(rows: list[dict]) -> list[dict]:
    """Narrative plus a question, options as a stringified list on some rows."""
    import ast

    out = []
    for i, r in enumerate(rows):
        row = r["row"]
        raw = row.get("choices")
        if isinstance(raw, str):
            try:
                raw = ast.literal_eval(raw)
            except (ValueError, SyntaxError):
                continue
        opts = [str(o).strip() for o in (raw or [])]
        idx = row.get("answer_index")
        if not opts or not isinstance(idx, int) or not 0 <= idx < len(opts):
            continue
        out.append({"id": f"musr-{i:05d}",
                    "input": f"{str(row.get('narrative') or '').strip()}\n\n"
                             f"Question: {str(row.get('question') or '').strip()}",
                    "choices": opts, "target": opts[idx]})
    return out


def logiqa_items(rows: list[dict]) -> list[dict]:
    out = []
    for i, r in enumerate(rows):
        row = r["row"]
        opts = [str(o).strip() for o in (row.get("options") or [])]
        idx = row.get("correct_option")
        if not opts or not isinstance(idx, int) or not 0 <= idx < len(opts):
            continue
        out.append({"id": f"lq-{i:05d}",
                    "input": f"{str(row.get('context') or '').strip()}\n\n"
                             f"{str(row.get('query') or '').strip()}",
                    "choices": opts, "target": opts[idx]})
    return out


def math500_items(rows: list[dict]) -> list[dict]:
    """Free-form: a problem and a final answer, NO options.

    The choice checks go n/a on this by design, which is the point of including
    it: it exercises the free-form path (answer-leak, duplicate questions) that
    thirteen multiple-choice datasets never reached.
    """
    out = []
    for i, r in enumerate(rows):
        row = r["row"]
        problem = str(row.get("problem") or "").strip()
        answer = str(row.get("answer") or "").strip()
        if not problem or not answer:
            continue
        out.append({"id": f"m500-{i:05d}", "input": problem, "target": answer})
    return out


def drop_items(rows: list[dict]) -> list[dict]:
    """Passage plus question; the answer is a span LIST.

    Every span is kept, as a list target, which the items schema defines as "a
    list means any listed answer is acceptable". That matches DROP: its multiple
    spans are alternative acceptable phrasings from different annotators, not
    parts of one compound answer.

    The first version kept only single-span items and threw away 96% of the
    split, 83 rows of 2000. A loader that silently discards nineteen rows in
    twenty produces a report about the loader, which is the same failure the
    SciQ builder above documents from the other direction.
    """
    out = []
    for i, r in enumerate(rows):
        row = r["row"]
        spans = ((row.get("answers_spans") or {}).get("spans")) or []
        spans = [str(x).strip() for x in spans if str(x).strip()]
        if not spans:
            continue
        # De-duplicated: annotators frequently agree verbatim, and a target list
        # holding the same string three times would say nothing extra while
        # making the item look like it accepts three answers.
        seen, targets = set(), []
        for sp in spans:
            if sp not in seen:
                seen.add(sp)
                targets.append(sp)
        out.append({"id": f"drop-{i:05d}",
                    "input": f"{str(row.get('passage') or '').strip()}\n\n"
                             f"Question: {str(row.get('question') or '').strip()}",
                    "target": targets[0] if len(targets) == 1 else targets})
    return out


BUILDERS = {
    "gsm8k": gsm8k_items,
    "truthfulqa": truthfulqa_items,
    "hellaswag": hellaswag_items,
    "arc-challenge": lambda rows: _hf_choice_items(rows, "arc"),
    "mmlu": lambda rows: _hf_choice_items(rows, "mmlu"),
    "arc-easy": lambda rows: _hf_choice_items(rows, "arce"),
    "winogrande": winogrande_items,
    "commonsenseqa": lambda rows: _stem_choice_items(rows, "cs", "question"),
    "openbookqa": lambda rows: _stem_choice_items(rows, "ob", "question_stem"),
    "boolq": boolq_items,
    "mmlu-pro": mmlu_pro_items,
    "sciq": sciq_items,
    "medmcqa": medmcqa_items,
    "race": race_items,
    "musr": musr_items,
    "logiqa": logiqa_items,
    "math500": math500_items,
    "drop": drop_items,
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
    force = "--force" in sys.argv
    only = [a for a in sys.argv[1:] if not a.startswith("-")]
    for name, url in SOURCES.items():
        if only and name not in only:
            continue
        pod = HERE / name
        if not (pod / "eval.yaml").is_file():
            print(f"no pod at {pod}, skipping")
            continue
        existing = pod / "items.jsonl"
        want = PAGED.get(name)
        if existing.is_file() and not force:
            have = sum(1 for line in existing.read_text(encoding="utf-8").splitlines()
                       if line.strip()) - 1
            if want is None or have >= want * 0.98:
                print(f"{name}: {have} items already on disk, skipping (--force to refetch)")
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
        # newline="\n": the drift boundary hashes these exact bytes, so a pod
        # fetched on Windows and shared would fail to re-derive anywhere else.
        (pod / "items.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8",
                                         newline="\n")
        print(f"  {len(items)} items -> {pod / 'items.jsonl'}")
        print(f"  source sha256: {digest}")
    print("\nNow:  dinostomp stomp benchmarks/<name>/eval.yaml")
    return 0


if __name__ == "__main__":
    sys.exit(main())
