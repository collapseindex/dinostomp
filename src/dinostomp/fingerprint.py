"""The engine's own SHA-256: which bytes produced this verdict.

The doctrine everywhere else in this toolkit is that anything influencing a run
gets its hash into the manifest: the spec, the data, the scorer, the agent, the
judge. The ENGINE influences every run and was the one input never hashed, which
is a hole in the tool's own rule.

This closes it. The fingerprint covers the shipped code and the schema pack, in
sorted path order, each file contributing both its path and its bytes so that
renaming a file changes the fingerprint as surely as editing one.

Two deliberate exclusions:

  - the README, the changelog, and the tests. The README PUBLISHES this value,
    so including it would make the number impossible to state correctly: any
    value you wrote down would change the thing it describes.
  - anything outside `src/dinostomp`. What a reader needs to authenticate is
    the code that computed their verdict, not the prose around it.

Recompute it yourself with `dinostomp fingerprint`, and compare against the
value published in the README. They should be identical; if they are not, you
are not running the code that README describes.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

# Extensions that carry behaviour. A stray .pyc or .md inside the package must
# not move the fingerprint, and neither must a __pycache__ directory.
CODE_SUFFIXES = (".py", ".json")
SKIP_DIRS = {"__pycache__", ".pytest_cache"}


def engine_files(root: Path | None = None) -> list[Path]:
    """Every shipped file the fingerprint covers, in sorted path order."""
    base = Path(root) if root else Path(__file__).resolve().parent
    out = []
    for path in sorted(base.rglob("*")):
        if not path.is_file() or path.suffix not in CODE_SUFFIXES:
            continue
        if any(part in SKIP_DIRS for part in path.relative_to(base).parts):
            continue
        out.append(path)
    return out


def engine_fingerprint(root: Path | None = None) -> str:
    """SHA-256 over the engine's own code and schemas.

    Path AND bytes go into the digest, so moving a file is as visible as
    changing one. Newlines are normalised, because a checkout that converted
    line endings is the same engine and should not read as a different one.
    """
    base = Path(root) if root else Path(__file__).resolve().parent
    digest = hashlib.sha256()
    for path in engine_files(base):
        rel = path.relative_to(base).as_posix()
        body = path.read_bytes().replace(b"\r\n", b"\n")
        digest.update(rel.encode("utf-8"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(body).digest())
    return digest.hexdigest()


def short(value: str | None = None) -> str:
    """The first 16 hex characters: enough to compare by eye in a README."""
    return (value or engine_fingerprint())[:16]
