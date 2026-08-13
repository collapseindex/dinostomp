"""Load AISafetyLab's real scorers with the model backends amputated.

Provenance, so every claim is checkable line by line:
  repo   https://github.com/thu-coai/AISafetyLab
  commit 3fd15737dee5c6858466162d6a68e6cb6f996b27
  files  aisafetylab/evaluation/scorers/{prompted_llm,overrefusal,pattern}_scorer.py

Nothing is reimplemented. The model backends (aisafetylab.models), loguru, tqdm
and torch are stubbed, so the pure-Python parse layer runs untouched and nothing
reaches the network. The defects under audit live in text parsing, which is why
this costs nothing.
"""
from __future__ import annotations

import importlib.util
import pathlib
import sys
import types

REPO_URL = "https://github.com/thu-coai/AISafetyLab"
REPO_COMMIT = "3fd15737dee5c6858466162d6a68e6cb6f996b27"
SCORERS = "aisafetylab/evaluation/scorers"


def _stub_deps() -> None:
    for name in ("loguru", "tqdm", "torch", "aisafetylab", "aisafetylab.models",
                 "aisafetylab.evaluation", "aisafetylab.evaluation.scorers"):
        sys.modules.setdefault(name, types.ModuleType(name))
    sys.modules["loguru"].logger = types.SimpleNamespace(
        warning=lambda *a, **k: None, info=lambda *a, **k: None, debug=lambda *a, **k: None)
    sys.modules["tqdm"].tqdm = lambda x, *a, **k: x
    sys.modules["aisafetylab.models"].OpenAIModel = object


def load(repo_root: pathlib.Path, fname: str):
    """Import one scorer file directly, under its real dotted name so relative
    imports resolve, bypassing the package __init__ and its heavy deps."""
    _stub_deps()
    root = repo_root / "aisafetylab" / "evaluation" / "scorers"
    base = root / "base_scorer.py"
    if not base.exists():
        raise SystemExit(
            f"AISafetyLab not found at {repo_root}\n\n"
            f"This audit reads a third-party repository that is not vendored here.\n"
            f"Clone the pinned commit and point the audit at it:\n\n"
            f"    git clone {REPO_URL} aisafetylab\n"
            f"    git -C aisafetylab checkout {REPO_COMMIT}\n"
            f"    python audit.py aisafetylab\n")
    bspec = importlib.util.spec_from_file_location(
        "aisafetylab.evaluation.scorers.base_scorer", base)
    bmod = importlib.util.module_from_spec(bspec)
    bspec.loader.exec_module(bmod)
    sys.modules["aisafetylab.evaluation.scorers.base_scorer"] = bmod
    full = f"aisafetylab.evaluation.scorers.{fname}"
    spec = importlib.util.spec_from_file_location(full, root / f"{fname}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[full] = mod
    spec.loader.exec_module(mod)
    return mod
