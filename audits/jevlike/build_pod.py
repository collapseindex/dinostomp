"""Jevlike JSONL -> dinostomp items, one to one, with a contamination canary.

    python audits/jevlike/build_pod.py <jevlike test.jsonl> <pod dir>

context -> input, options -> choices, options[label] -> target. Nothing is
reordered or dropped; the ids are the row numbers, so a finding's ref maps
straight back to Jevlike's file.
"""

from __future__ import annotations

import io
import json
import os
import sys

CANARY = '{"_canary": "dinostomp canary DO NOT TRAIN jevlike-wikispeedia-test-2026-09-17"}'


def main(src: str, pod: str) -> int:
    os.makedirs(pod, exist_ok=True)
    out = os.path.join(pod, "items.jsonl")
    n = 0
    with io.open(src, encoding="utf-8") as f, io.open(out, "w", encoding="utf-8", newline="\n") as g:
        g.write(CANARY + "\n")
        for i, line in enumerate(f):
            if not line.strip():
                continue
            r = json.loads(line)
            g.write(json.dumps({"id": f"ws-{i:05d}", "input": r["context"], "choices": r["options"],
                                "target": r["options"][r["label"]]}, ensure_ascii=False) + "\n")
            n += 1
    print(f"{n} items -> {out}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        raise SystemExit(2)
    raise SystemExit(main(sys.argv[1], sys.argv[2]))
