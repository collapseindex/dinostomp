"""X1 `semantic-duplicate-options`: the first check in this ecosystem that ASKS a model.

WHY THIS IS AN EXTENSION AND NOT A CORE CHECK
=============================================

REFERENCES.md commits the core to two things this check cannot honour:

    No LLM-as-judge for the battery's own verdicts. A judge is something
    dinostomp AUDITS (J1-J4), never something it ASKS.
    Nothing here needs a GPU and nothing needs a network; `stomp` is offline
    by construction.

Both are load-bearing. `stomp` being free, offline and deterministic is why you
can run it on a stranger's pod, in CI, without a key. A judge-based check in the
core would quietly end that for everyone, including people who never wanted this
check. So it lives out here, where installing it is a deliberate act and the
report names, versions and hashes it.

WHAT IT IS FOR
==============

Scoring the core's `dup-options` (S5) against MMLU-Redux's human annotation
(N-012) measured exactly where a byte comparison runs out: of 39 items humans
labelled `multiple_correct_answers`, S5 reaches 2. The other 37 are SEMANTIC
duplicates, and no amount of normalising finds them:

    ['steadily in one direction', 'in one direction', 'to and fro', 'All of these']
    ['If neither Marina reads ... nor Izzy plays ...', "If it's not the case that both ..."]

Recognising those needs a reader. That is what a judge is, and it is the only
job in this repository where asking one is better than computing something.

WHAT IT COSTS, AND WHAT IT PROMISES
===================================

It is OPT-IN per pod, capped, cached, and it SKIPS rather than failing when it
cannot run. A check that spends money by default, or that turns an offline audit
into a network call without being asked, would be a worse defect than the one it
detects.

MEASURED, AND NOT RECOMMENDED
============================

It was validated before shipping, against 39 human-confirmed positives and 250
human-labelled clean items, and it does not work well enough to use:

    "do any two mean the same?"   llama-3.1-8b   recall 100%  FPR 98.4%
    "do any two mean the same?"   qwen3-30b      recall  38%  FPR 27.6%
    "is any OTHER also correct?"  qwen3-30b      recall  95%  FPR 69.2%

Precision is 14-18% across all three. On a 3,000-item benchmark that is 830 to
2,950 false flags to find ~37 real ones. Changing the prompt slides recall and
the false-positive rate along one curve without improving the discrimination,
which is the signature of a task limit rather than a prompt limit: a good
multiple-choice question has distractors DESIGNED to be confusable, so "could a
second option be defended?" is close to the question the item exists to ask.

See README.md and N-013. The code is kept because the apparatus is reusable and
the negative result is worth more than another untested plugin.

Its findings are advisory (`warn`), never gating, and every finding states its
own measured false-positive rate. A judge is fallible, this one is measurably
so, and no model's opinion should be able to turn somebody's dataset `BROKEN` or
be quotable without its error rate attached.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from dinostomp.extensions import ExtensionCheck

NAME = "semdup"
VERSION = "0.1.0"

# One call per ITEM, not per pair: a four-option item is one question, not six.
PROMPT = """You are checking a multiple-choice question for a defect.

Question: {question}

Options:
{options}

Do any TWO of these options mean the same thing, such that both would have to be
counted correct? Ignore differences in wording, formatting, case and notation;
judge only whether two options assert the same thing.

Be strict. Options that are merely SIMILAR, or that describe related but
distinct things, are NOT duplicates. Most questions have no duplicates.

Answer with exactly one line:
DUPLICATE: <option letter>, <option letter>
or
NONE"""

DEFAULT_MAX_ITEMS = 300


def _config(ctx) -> dict | None:
    """Per-pod opt-in, read from `metadata.semdup`. Absent means do nothing."""
    spec = getattr(ctx, "get", lambda *_: None)("spec") if hasattr(ctx, "get") else None
    if spec is None:
        spec = ctx.get("spec") if isinstance(ctx, dict) else None
    cfg = ((spec or {}).get("metadata") or {}).get("semdup")
    return cfg if isinstance(cfg, dict) else None


def _cache_path(ctx, cfg) -> Path:
    spec_path = ctx.get("spec_path") if isinstance(ctx, dict) else None
    base = Path(spec_path).resolve().parent if spec_path else Path(".")
    return base / "data" / "semdup-cache.json"


def _key(item, model: str) -> str:
    blob = json.dumps({"q": item.get("input"), "c": item.get("choices"), "m": model},
                      sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:32]


def parse(text: str) -> bool | None:
    """Did the judge say two options are equivalent?

    Returns None for an unparseable reply, which is counted and reported rather
    than folded into either answer. A judge that returned prose is a fact about
    the run, not a NONE.
    """
    if not text:
        return None
    head = text.strip().splitlines()[0].strip().upper() if text.strip() else ""
    if head.startswith("NONE"):
        return False
    if head.startswith("DUPLICATE"):
        return True
    body = text.strip().upper()
    if "DUPLICATE:" in body:
        return True
    if "NONE" in body:
        return False
    return None


def _ask(provider, item, params) -> tuple[bool | None, int, int, str]:
    letters = "ABCDEFGH"
    opts = "\n".join(f"{letters[n]}. {c}" for n, c in enumerate(item.get("choices") or []))
    prompt = PROMPT.format(question=item.get("input"), options=opts)
    completion = provider.complete({"id": item.get("id"), "input": prompt, "target": ""},
                                   0, params)
    return (parse(completion.text), completion.input_tokens, completion.output_tokens,
            completion.text)


def run(ctx, out) -> None:
    cfg = _config(ctx)
    if not cfg:
        out.finding("X1", "n/a",
                    "not enabled for this pod. This check calls a hosted model, so it is opt-in: "
                    "add `metadata.semdup.judge` to the spec to turn it on")
        return

    items = [i for i in (ctx.get("items") or []) if i.get("choices")]
    if not items:
        out.finding("X1", "n/a", "no choice items; there are no options to compare")
        return

    judge = cfg.get("judge") or {}
    model = str(judge.get("model") or "")
    if not model:
        out.finding("X1", "skip", "metadata.semdup.judge.model is not set")
        return

    cache_path = _cache_path(ctx, cfg)
    cache = {}
    if cache_path.is_file():
        try:
            cache = json.loads(cache_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            cache = {}

    max_items = int(cfg.get("max_items") or DEFAULT_MAX_ITEMS)
    todo = [i for i in items if _key(i, model) not in cache][:max_items]

    provider = None
    if todo:
        env = {"openrouter": "OPENROUTER_API_KEY", "openai": "OPENAI_API_KEY",
               "anthropic": "ANTHROPIC_API_KEY"}.get(str(judge.get("provider")))
        if env and not os.environ.get(env):
            out.finding("X1", "skip",
                        f"{len(todo)} item(s) are not cached and {env} is not set. This check "
                        "will not guess and will not silently pass: run it once with a key, and "
                        "the cached verdicts make every later run free and offline")
            return
        try:
            from dinostomp.providers import make_provider
            provider = make_provider(str(judge.get("provider")), model)
        except Exception as exc:  # noqa: BLE001 - a provider problem is a skip, not a crash
            out.finding("X1", "skip", f"cannot build the judge: {exc}")
            return

    params = dict(judge.get("params") or {"temperature": 0, "max_tokens": 40})
    asked = unparsed = 0
    for item in todo:
        try:
            verdict, _, _, raw = _ask(provider, item, params)
        except Exception as exc:  # noqa: BLE001 - stop cleanly, keep what was paid for
            out.finding("X1", "skip",
                        f"the judge stopped after {asked} call(s): {exc}. Cached verdicts are "
                        "kept, so re-running resumes rather than re-paying")
            _save(cache_path, cache)
            return
        asked += 1
        if verdict is None:
            unparsed += 1
        cache[_key(item, model)] = {"dup": verdict, "raw": raw[:200]}
    if todo:
        _save(cache_path, cache)

    judged = [(i, cache.get(_key(i, model))) for i in items]
    judged = [(i, v) for i, v in judged if v is not None]
    flagged = [str(i["id"]) for i, v in judged if v.get("dup") is True]
    undecided = sum(1 for _, v in judged if v.get("dup") is None)
    skipped = len(items) - len(judged)

    detail = (f"{len(flagged)} of {len(judged)} item(s) offer two options a judge reads as "
              f"equivalent. ADVISORY, AND MEASURABLY UNRELIABLE: on MMLU-Redux this check's "
              f"false-positive rate was 28% to 98% depending on the judge, so most flags here "
              f"are expected to be wrong. It is published as a negative result (N-013). The "
              f"core's dup-options finding is the deterministic one")
    if skipped:
        detail += f"; {skipped} item(s) were not judged (max_items={max_items})"
    if undecided:
        detail += f"; {undecided} reply(ies) were unparseable and are counted as neither"
    out.finding("X1", "pass" if not flagged else "warn", detail,
                n=len(judged), examples=flagged[:20],
                evidence={"judge": model, "asked_this_run": asked, "cached": len(judged) - asked,
                          "unparseable": undecided, "advisory": True})


def _save(path: Path, cache: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cache, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8", newline="\n")


CHECKS = [
    ExtensionCheck(
        id="X1",
        name="two options a judge reads as equivalent",
        gating=False,
        applies_when="choice items, and metadata.semdup enabled",
        run=run,
        slug="semantic-duplicate-options",
    ),
]
