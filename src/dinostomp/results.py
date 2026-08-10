"""The RESULTS half of an evaluation report: what the models actually did.

Everything else in this package asks whether an eval is trustworthy. This
module asks what it found, which is the question the eval was run to answer and
which the report had almost nothing to say about: per-model accuracy existed
only inside one check's evidence blob, item difficulty was computed and thrown
away, and cost was checked but never totalled.

THE RULE THAT SHAPES THIS FILE. Results are recomputed from the RECORDS, the
same re-scored records every check reads, and never copied from a summary. A
summary on disk is a derived artifact this project treats as untrusted
everywhere else (R9 exists to catch one that disagrees), and a results table
that trusted it would be the one place in the report where a hand-edited number
survives. `tests/test_results.py` asserts the accuracy here equals the
accuracy R7 reports, on the same runs, because two numbers for one quantity is
the defect this codebase names Parity.

WHAT THIS MODULE MAY NOT DO. It computes no verdict and gates nothing. A
difficult item is not a defect, an expensive model is not a defect, and a wide
interval is not a defect. Findings come from the checks; this describes.

Nothing here is capped. The renderer decides how much to show and says what it
left out; the full tables go to STOMP.json, because a report that silently
truncates is the thing this project exists to complain about.
"""

from __future__ import annotations

from collections import Counter
from statistics import fmean

from dinostomp.psychometrics import (dead_items, kr20, min_detectable_effect,
                                     point_biserials, wilson_ci)

# Verdicts that count toward accuracy. `flag` rides with them because it is a
# scored outcome; `uncheckable` never does, which is the rule the runner uses
# and the reason accuracy is always reported ON CHECKABLE.
SCORED = ("pass", "fail", "flag")


def _round(x, places=4):
    return None if x is None else round(float(x), places)


def per_model(entries: list[dict]) -> list[dict]:
    """One row per model, recomputed from its records.

    `spend_usd` and token totals are summed from the RECORDS rather than read
    from the manifest ledger. R3 is the check that compares the two; if they
    disagree the report says so there, and this table shows what the evidence
    itself adds up to.
    """
    by_model: dict[str, dict] = {}
    for entry in entries:
        manifest = entry.get("manifest") or {}
        model = str(manifest.get("model") or "?")
        row = by_model.setdefault(model, {
            "model": model,
            "provider": str(manifest.get("provider") or "?"),
            "dry_run": bool(manifest.get("dry_run")),
            "runs": 0, "n_records": 0,
            "verdicts": Counter(), "finish_reasons": Counter(),
            "tokens_in": 0, "tokens_out": 0, "spend_usd": 0.0,
            "outputs": Counter(),
        })
        row["runs"] += 1
        for r in entry.get("records") or ():
            if r.get("model") != manifest.get("model"):
                continue
            row["n_records"] += 1
            row["verdicts"][(r.get("score") or {}).get("verdict") or "?"] += 1
            row["finish_reasons"][str(r.get("finish_reason") or "unreported")] += 1
            usage = r.get("usage") or {}
            row["tokens_in"] += int(usage.get("input_tokens") or 0)
            row["tokens_out"] += int(usage.get("output_tokens") or 0)
            row["spend_usd"] += float(usage.get("cost_usd") or 0.0)
            row["outputs"][str(r.get("output") or "")] += 1

    out = []
    for model in sorted(by_model):
        row = by_model[model]
        v = row["verdicts"]
        checkable = sum(v[k] for k in SCORED)
        passes = v["pass"]
        ci = wilson_ci(passes, checkable) if checkable else None
        top_output, top_n = (row["outputs"].most_common(1) or [("", 0)])[0]
        out.append({
            "model": model,
            "provider": row["provider"],
            "dry_run": row["dry_run"],
            "runs": row["runs"],
            "n_records": row["n_records"],
            "n_checkable": checkable,
            "n_uncheckable": row["n_records"] - checkable,
            "n_passes": passes,
            "n_failures": v["fail"],
            "accuracy": _round(passes / checkable) if checkable else None,
            "ci95": [_round(ci[0], 3), _round(ci[1], 3)] if ci else None,
            # Share of output the scorer could reach a verdict on at all. 80%
            # accurate on 60%-judgeable output is not 80% accurate, and putting
            # the two in one row is the only way a reader sees both.
            "judgeability": _round(checkable / row["n_records"]) if row["n_records"] else None,
            "tokens_in": row["tokens_in"],
            "tokens_out": row["tokens_out"],
            "spend_usd": _round(row["spend_usd"], 6),
            "finish_reasons": dict(sorted(row["finish_reasons"].items())),
            # Not a finding: R14 is the check that decides whether this is a
            # collapse. Shown because a model whose modal answer covers most of
            # its records is worth a reader's eye before its accuracy is.
            "modal_output": {"text": top_output[:120], "count": top_n,
                             "share": _round(top_n / row["n_records"]) if row["n_records"] else None},
        })
    return out


def per_item(matrix: dict, items: list[dict], outputs: dict) -> list[dict]:
    """One row per item: how hard it was, and whether it separated anybody.

    Difficulty `p` is the share of the fleet that got it right, the oldest
    statistic in item analysis. Discrimination is the point-biserial already
    computed for P2. Both are DESCRIPTIVE here; the checks decide what is wrong.
    """
    if not matrix:
        return []
    rpb = point_biserials(matrix)
    by_id = {str(i.get("id")): i for i in items}
    seen: dict[str, list[str]] = {}
    for model, row in matrix.items():
        for item_id in row:
            seen.setdefault(item_id, []).append(model)

    out = []
    for item_id in sorted(seen):
        answered = sorted(seen[item_id])
        correct = [m for m in answered if matrix[m].get(item_id) == 1]
        missed = [m for m in answered if matrix[m].get(item_id) == 0]
        item = by_id.get(item_id) or {}
        target = item.get("target")
        wrong = Counter(outputs.get(m, {}).get(item_id, "") for m in missed)
        out.append({
            "id": item_id,
            "target": (target if isinstance(target, str) else
                       ", ".join(str(t) for t in target) if isinstance(target, list) else str(target)),
            "n_answered": len(answered),
            "n_correct": len(correct),
            "p": _round(len(correct) / len(answered)) if answered else None,
            "discrimination": _round(rpb.get(item_id)),
            "missed_by": missed,
            "top_wrong_answer": (wrong.most_common(1)[0][0][:120] if wrong else None),
            # An item everyone passes or everyone fails measures nothing about
            # this fleet. P3 is what decides whether there are too many.
            "separates": 0 < len(correct) < len(answered),
        })
    return out


def fleet(matrix: dict, model_rows: list[dict]) -> dict:
    """Aggregates over the whole fleet, all descriptive."""
    accs = [r["accuracy"] for r in model_rows if r["accuracy"] is not None]
    all_right, all_wrong = dead_items(matrix) if matrix else ([], [])
    n_items = len({i for row in matrix.values() for i in row}) if matrix else 0
    return {
        "n_models": len(model_rows),
        "n_items": n_items,
        "mean_accuracy": _round(fmean(accs)) if accs else None,
        "min_accuracy": _round(min(accs)) if accs else None,
        "max_accuracy": _round(max(accs)) if accs else None,
        "spread": _round(max(accs) - min(accs)) if len(accs) > 1 else None,
        "kr20": _round(kr20(matrix)) if matrix else None,
        "n_all_right": len(all_right),
        "n_all_wrong": len(all_wrong),
        "dead_share": _round((len(all_right) + len(all_wrong)) / n_items) if n_items else None,
        "mde_unpaired": _round(min_detectable_effect(n_items)) if n_items else None,
    }


def slices(matrix: dict, items: list[dict]) -> dict:
    """Accuracy broken down by every metadata field the items carry.

    An eval's headline number is an average over whatever mix of items happened
    to be in it, and a fleet at 70% overall can be at 95% on one subject and 30%
    on another. Nothing here decides that a gap matters: subgroup counts are
    small and this makes no multiplicity correction, which is stated in the
    rendered report next to the table rather than left for a reader to assume.
    """
    keys: dict[str, dict[str, list[str]]] = {}
    for item in items:
        meta = item.get("metadata")
        if not isinstance(meta, dict):
            continue
        item_id = str(item.get("id"))
        for key, value in meta.items():
            if isinstance(value, (str, int, float, bool)):
                keys.setdefault(str(key), {}).setdefault(str(value), []).append(item_id)

    out: dict[str, list[dict]] = {}
    for key in sorted(keys):
        rows = []
        for value in sorted(keys[key]):
            ids = set(keys[key][value])
            correct = total = 0
            per_model_acc = {}
            for model, row in sorted(matrix.items()):
                hit = [row[i] for i in ids if i in row]
                if hit:
                    per_model_acc[model] = _round(sum(hit) / len(hit))
                    correct += sum(hit)
                    total += len(hit)
            if not total:
                continue
            ci = wilson_ci(correct, total)
            rows.append({
                "value": value,
                "n_items": len(ids),
                "n_scored": total,
                "accuracy": _round(correct / total),
                "ci95": [_round(ci[0], 3), _round(ci[1], 3)] if ci else None,
                "by_model": per_model_acc,
            })
        if rows:
            out[key] = rows
    return out


def compute(entries: list[dict], items: list[dict], matrix: dict,
            outputs: dict | None = None) -> dict:
    """The full results block, or None-ish empties when there is nothing to say."""
    model_rows = per_model(entries)
    return {
        "models": model_rows,
        "fleet": fleet(matrix, model_rows),
        "items": per_item(matrix, items, outputs or {}),
        "slices": slices(matrix, items),
        "cost": {
            "total_usd": _round(sum(r["spend_usd"] for r in model_rows), 6),
            "total_tokens_in": sum(r["tokens_in"] for r in model_rows),
            "total_tokens_out": sum(r["tokens_out"] for r in model_rows),
            "all_dry": all(r["dry_run"] for r in model_rows) if model_rows else False,
        },
    }
