"""Re-derive the counts in FINDINGS.md from the public releases, without dinostomp.

No model calls. Reads the Hugging Face cache and two local CSVs; pass --fetch to
allow the datasets library to download what is not cached. Prints counts and
item ids only, never item text.

Usage:
    python audits/typed-decision-corpora/verify.py [--fetch] [--banking DIR] [--output report.json]
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

WORD = re.compile(r"[a-z]+")
MAX_IDS = 8


def whole(phrase: str, text: str) -> bool:
    return re.search(rf"(?<![a-z0-9]){re.escape(phrase)}(?![a-z0-9])", text) is not None


def folded(text: str) -> str:
    key = unicodedata.normalize("NFKC", text).casefold().replace("’", "'")
    key = re.sub(r"[‐-―−-]", " ", key)
    return " ".join(key.split())


def few(ids: list[str]) -> list[str]:
    return ids[:MAX_IDS]


def clinc(report: dict) -> None:
    from datasets import load_dataset

    for split in ("train", "validation", "test"):
        data = load_dataset("clinc/clinc_oos", "plus", split=split)
        names = data.features["intent"].names
        literal, oos, rows = [], 0, 0
        for index, row in enumerate(data):
            intent = names[row["intent"]]
            rows += 1
            if intent == "oos":
                oos += 1
                continue
            if whole(intent.replace("_", " "), " ".join(row["text"].split()).casefold()):
                literal.append(f"{split}:{index}")
        report[f"clinc/{split}"] = {"rows": rows, "oos": oos,
                                   "gold_intent_name_whole_word_in_message": len(literal),
                                   "examples": few(literal)}


def banking(report: dict, folder: Path) -> None:
    for split in ("train", "test"):
        seen: dict[str, str] = {}
        literal, dup, rows = [], [], 0
        with (folder / f"{split}.csv").open(encoding="utf-8", newline="") as handle:
            for index, row in enumerate(csv.DictReader(handle)):
                rows += 1
                key = folded(row["text"])
                if key in seen:
                    dup.append(f"{split}:{index}~{seen[key]}")
                else:
                    seen[key] = f"{split}:{index}"
                if whole(row["category"].replace("_", " "), " ".join(row["text"].split()).casefold()):
                    literal.append(f"{split}:{index}")
        report[f"banking77/{split}"] = {"rows": rows,
                                       "gold_intent_name_whole_word_in_message": len(literal),
                                       "messages_repeated_after_folding": len(dup),
                                       "examples": few(literal), "duplicate_examples": few(dup)}


def fever(report: dict) -> None:
    from huggingface_hub import hf_hub_download

    for split in ("train", "valid"):
        path = hf_hub_download("copenlu/fever_gold_evidence", f"{split}.jsonl", repo_type="dataset")
        seen: dict[str, str] = {}
        dup, verbs, labels = [], [], Counter()
        with open(path, encoding="utf-8") as handle:
            for line in handle:
                row = json.loads(line)
                labels[row["label"]] += 1
                sentences = tuple(e[2] for e in row["evidence"] if len(e) >= 3)
                key = folded(row["claim"]) + "\x1f" + "\x1f".join(folded(s) for s in sentences)
                if key in seen:
                    dup.append(f"{row['id']}~{seen[key]}")
                else:
                    seen[key] = str(row["id"])
                text = folded(row["claim"] + " " + " ".join(sentences))
                has = {v: whole(v, text) for v in ("supports", "refutes")}
                if has["supports"] != has["refutes"]:
                    verbs.append(str(row["id"]))
        report[f"fever_gold_evidence/{split}"] = {"rows": sum(labels.values()), "labels": dict(labels),
                                                  "claim_evidence_pairs_repeated": len(dup),
                                                  "rows_with_exactly_one_of_supports_refutes_as_a_word": len(verbs),
                                                  "duplicate_examples": few(dup), "verb_examples": few(verbs)}


def quality(report: dict) -> None:
    from datasets import load_dataset

    data = load_dataset("emozilla/quality", split="validation")
    verbatim, nbsp = [], []
    for index, row in enumerate(data):
        article = " ".join(row["article"].split()).casefold()
        present = [whole(" ".join(o.split()).casefold(), article) for o in row["options"]]
        gold = int(row["answer"])
        if present[gold] and not any(p for i, p in enumerate(present) if i != gold):
            verbatim.append(f"validation:{index}")
        if " " in row["article"] or " " in row["question"]:
            nbsp.append(f"validation:{index}")
    report["quality/validation"] = {"rows": len(data),
                                    "gold_option_verbatim_in_article_and_no_distractor": len(verbatim),
                                    "rows_with_no_break_space": len(nbsp),
                                    "examples": few(verbatim)}


def pacifaist(report: dict, folder: Path) -> None:
    """PacifAIst as a four-way choice: is the safe action the longest, and does overlap find it."""
    for name in ("nom", "flip"):
        key = "correct_choice" if name == "nom" else "new_correct"
        longest, top, decidable, rows = [], [], 0, 0
        with (folder / f"pacifaist_{name}.csv").open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                rows += 1
                choices = [row[f"choice_{c}"] for c in "abcd"]
                gold = "abcd".index(row[key].strip().lower())
                lengths = [len(c) for c in choices]
                if lengths[gold] > max(v for i, v in enumerate(lengths) if i != gold):
                    longest.append(row["scenario_id"])
                words = set(WORD.findall(row["prompt"].casefold()))
                overlap = [len(words & set(WORD.findall(c.casefold()))) for c in choices]
                best = max(overlap)
                if overlap.count(best) == 1:
                    decidable += 1
                    if overlap.index(best) == gold:
                        top.append(row["scenario_id"])
        report[f"pacifaist/{name}"] = {"rows": rows, "gold_strictly_longest_option": len(longest),
                                       "overlap_decidable": decidable,
                                       "most_overlap_option_is_gold": len(top),
                                       "examples": few(longest), "overlap_examples": few(top)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fetch", action="store_true", help="allow downloads; default is cache only")
    parser.add_argument("--banking", default=os.environ.get("BANKING77_DIR", ""),
                        help="folder with BANKING77's train.csv and test.csv from the authors' GitHub")
    parser.add_argument("--pacifaist", default=os.environ.get("PACIFAIST_DIR", ""),
                        help="folder with pacifaist_nom.csv and pacifaist_flip.csv from the Brittle Safety release")
    parser.add_argument("--output")
    arguments = parser.parse_args()
    if not arguments.fetch:
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["HF_DATASETS_OFFLINE"] = "1"
    report: dict = {}
    clinc(report)
    if arguments.banking:
        banking(report, Path(arguments.banking))
    fever(report)
    quality(report)
    if arguments.pacifaist:
        pacifaist(report, Path(arguments.pacifaist))
    for name, counts in report.items():
        shown = {k: v for k, v in counts.items() if not k.endswith("examples")}
        print(f"{name}: {json.dumps(shown)}")
    if arguments.output:
        Path(arguments.output).write_text(json.dumps(report, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
