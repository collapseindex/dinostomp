"""Fetch real Inspect AI logs, so the adapter can be checked against reality.

Not vendored, for the usual reason: they belong to their authors and a copy here
would be a copy that silently goes stale. These are test fixtures from
UKGovernmentBEIS/inspect_ai (MIT), which is the only place real Inspect logs are
publicly available in a fixed location.

    python benchmarks/inspect-import/fetch.py
    python -m pytest tests/test_adapters.py -q      # the real-log tests unskip

Without them, `tests/test_adapters.py` still runs: its offline cases use
synthetic logs shaped from these files. The real-log tests SKIP rather than pass
silently, because a test that quietly turns into a no-op is worse than one that
fails.

They are small on purpose (1 to 3 samples each): they are fixtures, not
published runs. That is enough to check that the ADAPTER reads a real log
correctly, and nowhere near enough to audit anybody's eval, which is why this
directory ships no pod.
"""

from __future__ import annotations

import hashlib
import sys
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = "https://raw.githubusercontent.com/UKGovernmentBEIS/inspect_ai/main/"

# One of each shape the adapter has to handle:
#   .eval        a ZIP with header.json + samples/*.json
#   .json        a single nested document
#   an agent run carrying real tool events
FILES = {
    "mmlu-choices.eval": "tests/analysis/test_logs_choices/mmlu-no-summary-choices.eval",
    "security-guide.json": "tests/analysis/test_logs/2025-05-12T20-28-26-04-00_security-guide.json",
    "browser.json": "tests/analysis/test_logs/2025-05-12T20-27-36-04-00_browser.json",
}


def main() -> int:
    for name, rel in FILES.items():
        out = HERE / name
        if out.is_file():
            print(f"{name}: already on disk, skipping")
            continue
        url = BASE + urllib.parse.quote(rel)
        print(f"fetching {name}\n  {rel}")
        try:
            blob = urllib.request.urlopen(url, timeout=120).read()  # noqa: S310 - pinned https
        except Exception as exc:  # noqa: BLE001 - a fetch failure is a message, not a traceback
            print(f"  FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
            return 1
        out.write_bytes(blob)
        print(f"  {len(blob):,} bytes, sha256 {hashlib.sha256(blob).hexdigest()}")
    print("\nNow:  python -m pytest tests/test_adapters.py -q")
    return 0


if __name__ == "__main__":
    sys.exit(main())
