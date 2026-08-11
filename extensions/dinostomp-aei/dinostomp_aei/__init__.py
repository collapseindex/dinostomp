"""dinostomp-aei: audit an Anthropic Economic Index release against its own README.

    dinostomp stomp aei_claude_ai_2026-06-26.csv

The release is not an eval. It has no questions, no answers and no model, so the
core battery correctly declines it: the dataset audit reports that no column
looks like the input and stops rather than guessing a mapping. That refusal is
the right behaviour and it is also the end of what the core can say.

What the release does have is a README that states a schema, a metric
vocabulary with units, a rounding rule, a hierarchy depth per category and an
explicit suppression policy. That is an evidence contract, which is the thing
this project already knows how to audit. These eleven checks read it.

The bar for a finding here is deliberately high, because the subject is somebody
else's published data. A rule fires only when the release contradicts its own
documentation, or breaks an invariant the release itself holds essentially
everywhere. Where the README is silent, so is this extension.
"""

from __future__ import annotations

from pathlib import Path

from dinostomp.extensions import ExtensionCheck

from . import rules

NAME = "dinostomp-aei"
VERSION = "0.1.0"

# id -> (one-line name, gating, when it applies)
SPEC = {
    "A1": ("the file carries exactly the documented columns", True, "an AEI release CSV"),
    "A2": ("every metric, geo level and category is one the README documents", True,
           "an AEI release CSV"),
    "A3": ("no value exceeds the documented two decimal places", True, "an AEI release CSV"),
    "A4": ("no value falls outside the range its documented unit permits", True,
           "an AEI release CSV"),
    "A5": ("no cell is published twice at the same grain", True, "an AEI release CSV"),
    "A6": ("partition families sum to 100 wherever the release declares that they do", True,
           "complete partition groups"),
    "A7": ("no row sits deeper than its category's documented hierarchy", True,
           "an AEI release CSV"),
    "A8": ("reporting periods tile as half-open calendar months", True, "an AEI release CSV"),
    "A9": ("every geo_id matches the form its geo_level documents", True, "an AEI release CSV"),
    "A10": ("node_name and node_external_id agree one-to-one", False, "rows carrying a node id"),
    "A11": ("how much of each `pct` distribution was actually published", False,
            "rows carrying the `pct` metric"),
}


def _looks_like_aei(path: Path) -> bool:
    """Cheap enough to run on every dataset audit, specific enough not to misfire.

    Reads one line. An extension that scanned 209MB to discover the file was not
    its business would make every unrelated audit pay for this one.
    """
    try:
        with path.open(encoding="utf-8", newline="") as fh:
            header = fh.readline().strip().split(",")
    except OSError:
        return False
    from . import contract as C

    return set(header) == set(C.COLUMNS)


def _make_runner(check_id: str):
    def run(ctx, out) -> None:
        path = ctx.get("data_path") if isinstance(ctx, dict) else None
        if not path:
            # n/a, not skip. Extensions load on the pod path too, and a `skip`
            # there would staple eleven grey lines to every eval report in the
            # repository for the crime of having this package installed. A check
            # that does not apply says so and gets out of the way; `skip` is for
            # a check that SHOULD have run and could not.
            out.finding(check_id, "n/a",
                        "this check reads a dataset file; it does not apply to an eval pod")
            return
        path = Path(path)
        if not _looks_like_aei(path):
            out.finding(check_id, "n/a", "not an Anthropic Economic Index release CSV")
            return
        # One scan serves all eleven, cached on the context so the file is read
        # once per audit rather than once per check.
        cache = ctx.setdefault("_aei_findings", {})
        if not cache:
            collected: dict[str, list] = {}

            class _Tee:
                def finding(self, cid, level, detail, **kw):
                    collected.setdefault(cid, []).append((level, detail, kw))

            rules.audit(path, _Tee())
            cache.update(collected)
        for level, detail, kw in cache.get(check_id, []):
            out.finding(check_id, level, detail, **kw)

    return run


CHECKS = [ExtensionCheck(id=cid, name=name, gating=gating, applies_when=when,
                         run=_make_runner(cid))
          for cid, (name, gating, when) in SPEC.items()]

# The evidence tax. Every check ships a planted defect it must catch and a clean
# release it must stay silent on; both live in fixtures/ and are exercised by
# tests/test_aei.py. Until both pass, these checks are reported but excluded
# from coverage, which is the core's rule and not one this extension may waive.
_FIX = Path(__file__).resolve().parent / "fixtures"
TRIALS = [(f"{cid}: planted defect in a conforming release", _FIX / f"mutant_{cid}.csv")
          for cid in ("A1", "A2", "A3", "A4", "A5", "A6", "A7", "A8", "A9", "A10")]
CLEAN_PODS = [("a conforming miniature release", _FIX / "clean.csv")]
