"""Report rendering: the first attachment on the report rail.

One source of truth (the lint report dict), two renderings:

  STOMP.md         markdown, GitHub/HF-native, receipts in <details> blocks
  stomp-badge.svg  a README badge carrying the verdict and coverage
  STOMP.json       the raw report, published next to the rendering so the
                   numbers stay re-analyzable (the HELM habit)

Both published artifacts are byte-stable: an unchanged pod re-reports to
identical STOMP.md AND STOMP.json, because reports are meant to live in git
and a diff should mean something changed. The volatile `generated_at` field
exists only in the in-memory report (and `stomp --json` output); the
published raw report strips it. Timestamps for provenance live in the run
manifests, which is where time actually happened.
"""

from __future__ import annotations

import json
from pathlib import Path

from dinostomp.lint import lint_eval
from dinostomp.spec import Issue


LEVEL_LABELS = {"pass": "ok", "fail": "FAIL", "warn": "warn", "skip": "skip", "n/a": "n/a"}

BADGE_COLORS = {
    "sound": "#2ea44f",
    "ok": "#b8a018",
    "incomplete": "#fe7d37",
    "broken": "#e05d44",
}

MD_NAME = "STOMP.md"
JSON_NAME = "STOMP.json"
BADGE_NAME = "stomp-badge.svg"


def _md_escape(text: str) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")


def _verdict_line(report: dict) -> str:
    cov = report["coverage"]
    summary = report["summary"]
    suffix = (f"({cov['ran']} of {cov['declared']} ran; "
              f"{len(cov['not_applicable'])} n/a of {cov['declared_total']} declared)")
    verdict = summary["verdict"]
    scope = summary.get("scope", "pod")
    if verdict == "sound":
        # Deliberately not "CLEAN": a badge saying CLEAN gets read as "this eval
        # is good", and the claim is only that no mechanical defect was found,
        # at full coverage, by this battery. A trivial eval can be sound.
        return (f"**MECHANICALLY SOUND**: no integrity findings at {scope} scope, full "
                f"coverage {suffix}")
    if verdict == "ok":
        return f"**OK**: no failures, {summary['warn']} warning(s) {suffix}"
    if verdict == "incomplete":
        return (f"**INCOMPLETE**: no failures, but only {cov['ran']} of {cov['declared']} "
                f"checks ran {suffix}. Not a clean bill of health.")
    return f"**BROKEN**: {summary['fail']} gated finding(s) {suffix}"


def render_markdown(report: dict) -> str:
    lines: list[str] = []
    target = Path(report["target"])
    lines.append(f"# 🦖 stomp report: {target.parent.name or target.name}")
    lines.append("")
    lines.append(_verdict_line(report))
    lines.append("")

    runs = report.get("runs") or []
    if runs and all(r["dry_run"] for r in runs):
        lines.append("> All runs used the offline dry provider; "
                     "results exercise the benchmark, not any real model.")
        lines.append("")

    verdict = report["summary"]["verdict"]
    claims = report.get("entitled_claims") or []
    typed = report.get("claims") or []
    lines.append("## Entitled claims")
    lines.append("")
    if verdict not in ("sound", "ok"):
        lines.append(f"**None.** The verdict is `{verdict}`; "
                     "this eval is not currently entitled to publish claims.")
    elif claims or typed:
        if claims:
            lines.append("This result is entitled to claim:")
            lines.append("")
            for claim in claims:
                lines.append(f"- {claim}")
            lines.append("")
    else:
        lines.append("The spec declares no claims; a green result here claims nothing in particular.")
    if typed:
        lines.append("Typed claims, compiled to evidence requirements and checked off:")
        lines.append("")
        for c in typed:
            status = "**SUPPORTED**" if c["supported"] else "**NOT SUPPORTED**"
            lines.append(f"- {status}: {c['description']}")
            for r in c["requirements"]:
                box = "x" if r["ok"] else " "
                lines.append(f"  - [{box}] {r['name']}: {r['detail']}")
    lines.append("")

    def check_table(findings: list[dict]) -> list[str]:
        rows = ["| | check | witnesses | detail |", "|---|---|---:|---|"]
        for f in findings:
            label = LEVEL_LABELS[f["level"]]
            marker = f"**{label}**" if f["level"] == "fail" else label
            rows.append(f"| {marker} | {_md_escape(f['check'])} | {f['witnesses']} | {_md_escape(f['detail'])} |")
        return rows

    lines.append("## Checks")
    lines.append("")
    lines.append("### Invariants (deterministic, gating)")
    lines.append("")
    lines.append("Facts, not heuristics: a failure here means something is mechanically wrong "
                 "(a duplicate exists, a hash changed, a number does not re-derive) and it breaks the verdict.")
    lines.append("")
    lines.extend(check_table([f for f in report["findings"] if f["gating"]]))
    lines.append("")
    lines.append("### Diagnostics (statistical, advisory)")
    lines.append("")
    lines.append("Threshold-based signals: they warn, expose their underlying values, and can have "
                 "legitimate explanations. A warning is evidence of possible trouble, never a proof of invalidity.")
    lines.append("")
    lines.extend(check_table([f for f in report["findings"] if not f["gating"]]))
    lines.append("")

    with_receipts = [f for f in report["findings"] if f.get("examples") or f.get("evidence")]
    if with_receipts:
        lines.append("### Receipts")
        lines.append("")
        for f in with_receipts:
            lines.append(f"<details><summary>[{LEVEL_LABELS[f['level']]}] {f['check']}</summary>")
            lines.append("")
            for ex in f.get("examples", []):
                lines.append(f"- {ex}")
            if f.get("evidence"):
                lines.append(f"- evidence: `{json.dumps(f['evidence'], sort_keys=True)}`")
            lines.append("")
            lines.append("</details>")
        lines.append("")

    if runs:
        lines.append("## Runs")
        lines.append("")
        lines.append("| run file | model | reported as | provider | dry | seed | records | uncheckable |")
        lines.append("|---|---|---|---|---|---:|---:|---:|")
        for r in runs:
            reported = r.get("model_reported") or ""
            reported_cell = "(same)" if reported == r["model"] else (_md_escape(reported) or "?")
            lines.append(
                f"| {_md_escape(r['run_file'])} | {_md_escape(r['model'])} | {reported_cell} "
                f"| {_md_escape(r['provider'])} | {'yes' if r['dry_run'] else 'no'} "
                f"| {r['seed']} | {r['records']} | {r.get('uncheckable', 0)} |"
            )
        lines.append("")

    lines.append("## Provenance")
    lines.append("")
    lines.append(f"- tool: dinostomp {report['version']}")
    power = report.get("power") or {}
    if power.get("mde_unpaired_80pct"):
        lines.append(f"- statistical power: at n={power['n_items']} items, an UNPAIRED comparison "
                     f"(worst case p=0.5) resolves gaps down to ~{power['mde_unpaired_80pct']:.0%} accuracy "
                     "(80% power, two-sided alpha 0.05); the paired bootstrap behind P6/C1 resolves "
                     "smaller gaps when model errors overlap")
    for key, value in (report.get("inputs") or {}).items():
        lines.append(f"- {key}: `{value}`")
    moved = [k for k, v in report.get("thresholds", {}).items() if v.get("source") != "default"]
    lines.append("- thresholds: all defaults" if not moved
                 else f"- thresholds moved from defaults: {', '.join(sorted(moved))}")
    lines.append("- reproducibility tiers, stated honestly: local inputs hash-pinned (spec, data, scorer); "
                 "requests reproducible given each manifest's environment envelope; hosted-model "
                 "immutability UNKNOWN unless the provider exposes a pinned revision (the runs table "
                 "records what each provider claims answered)")
    lines.append(f"- raw report: [{JSON_NAME}]({JSON_NAME}) (both files omit volatile fields, "
                 "so an unchanged pod re-reports to identical bytes; run manifests carry the timestamps)")
    lines.append("")
    return "\n".join(lines)


def render_badge(report: dict) -> str:
    """A small flat SVG badge: 'stomped | <verdict> N/M'.

    The coverage fraction rides ON the badge on purpose. This is the artifact
    that ends up on repos nobody here controls, and a bare word would be read
    as a grade; `sound 54/54` states what was checked in the same breath as
    the verdict, so the badge cannot outrun its evidence.
    """
    cov = report["coverage"]
    verdict = report["summary"]["verdict"]
    left = "stomped"
    # `integrity`, not `sound`. The badge is the artifact that travels furthest
    # from its own documentation, so it says what was checked rather than
    # offering a word a reader will hear as a grade.
    label = "integrity" if verdict == "sound" else verdict
    right = f"{label} {cov['ran']}/{cov['declared']}"
    char_w = 7
    pad = 10
    lw = len(left) * char_w + pad
    rw = len(right) * char_w + pad
    color = BADGE_COLORS[verdict]
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{lw + rw}" height="20" '
        f'role="img" aria-label="{left}: {right}">'
        f'<rect width="{lw}" height="20" rx="3" fill="#3a3a3a"/>'
        f'<rect x="{lw}" width="{rw}" height="20" rx="3" fill="{color}"/>'
        f'<rect x="{lw - 3}" width="6" height="20" fill="{color}"/>'
        f'<g fill="#fff" font-family="Verdana,DejaVu Sans,sans-serif" font-size="11" text-anchor="middle">'
        f'<text x="{lw / 2:.0f}" y="14">{left}</text>'
        f'<text x="{lw + rw / 2:.0f}" y="14">{right}</text>'
        f"</g></svg>"
    )


def verify_report(spec_path: str | Path, trust_code: bool = False) -> tuple[str, list[str], dict | None]:
    """Re-derive the report from the pod's current state and byte-compare it
    against the PUBLISHED artifacts. This is the whole thesis weaponized: a
    stranger can check a published verdict offline without trusting the
    publisher.

    Returns (status, details, fresh_report) where status is:
      "verified"     every published artifact re-derives byte-for-byte
      "mismatch"     an artifact differs from what the pod re-derives (stale
                     after changes, or edited by hand; either way, not the
                     pod's current truth)
      "unverifiable" no published report to check, or the pod cannot be
                     stomped at all
    """
    report, issues = lint_eval(spec_path, trust_code=trust_code)
    if report is None:
        return "unverifiable", [f"cannot stomp: {i.message}" for i in issues[:3]], None
    pod = Path(spec_path).resolve().parent
    stable = {k: v for k, v in report.items() if k != "generated_at"}
    expected = {
        MD_NAME: render_markdown(report),
        JSON_NAME: json.dumps(stable, indent=2) + "\n",
        BADGE_NAME: render_badge(report) + "\n",
    }
    details = []
    missing = [name for name in expected if not (pod / name).is_file()]
    if missing:
        return "unverifiable", [f"no published {name} to verify" for name in missing], report
    for name, want in expected.items():
        got = (pod / name).read_text(encoding="utf-8")
        if got != want:
            details.append(f"{name} does not re-derive from the pod's current state")
    if details:
        return "mismatch", details, report
    return "verified", [f"{name} re-derives byte-for-byte" for name in expected], report


def write_report(spec_path: str | Path, trust_code: bool = False) -> tuple[dict | None, list[Issue], list[Path]]:
    """Stomp the pod and write STOMP.md, STOMP.json, and the badge next to
    the spec. Returns (report, issues, written_paths)."""
    report, issues = lint_eval(spec_path, trust_code=trust_code)
    if report is None:
        return None, issues, []
    pod = Path(spec_path).resolve().parent
    stable = {k: v for k, v in report.items() if k != "generated_at"}
    written = []
    for name, content in (
        (MD_NAME, render_markdown(report)),
        (JSON_NAME, json.dumps(stable, indent=2) + "\n"),
        (BADGE_NAME, render_badge(report) + "\n"),
    ):
        path = pod / name
        # newline="\n" always. Python otherwise translates to CRLF on Windows,
        # and `verify` byte-compares these artifacts, so a report published from
        # here would not re-derive anywhere else.
        path.write_text(content, encoding="utf-8", newline="\n")
        written.append(path)
    return report, [], written
