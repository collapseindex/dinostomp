"""Replay a pod's committed runs side by side in the terminal.

    dinostomp race audits/xstest-refusal

Every lane is one model's informed run, read from the pod's run records.
Nothing is called and nothing is simulated: each frame is a record that is
on disk, and the replay is built so a viewer cannot come away with a claim
the records do not make.

  * REPLAY, said on screen. The header names the pod and says no model is
    called.
  * Lockstep. Every lane shows the SAME item in the same frame, in the
    seeded order the runs used, so the running scores are comparable at
    every moment. Wall time is not animated: it depends on the provider,
    the network and the queue as much as on the model, so it appears once,
    in the final table, labelled as recorded.
  * Shown, not interpreted. Each lane prints the model's raw output, the
    verdict the scorer recorded, and the reference answer. If a model
    declined to answer, its own words say so.
  * The floor on screen. What always giving the most common answer scores
    is drawn on every bar, so "high" is always read against "free".
  * Parity. The final accuracy is recomputed from the records and compared
    with each run's saved summary; a disagreement prints as MISMATCH.
"""

from __future__ import annotations

import json
import re
import shutil
import sys
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from dinostomp.calibration import probability_vector
from dinostomp.items import load_items
from dinostomp.lint import _discover_runs
from dinostomp.psychometrics import wilson_ci
from dinostomp.spec import load_spec

DEFAULT_RATE = 40.0                 # items per second
BAR_WIDTH = 20
NAME_WIDTH = 28
MIN_OUTPUT_WIDTH = 30
FIXED_COLUMNS = 2 + NAME_WIDTH + 1 + 6 + 2 + BAR_WIDTH + 2 + 3 + 8   # everything on a lane row but the output
MAX_WITNESSES_SHOWN = 6
PARITY_TOLERANCE = 1e-6
MODEL_MIN_WIDTH = 18   # the model column's floor in the rich table; longer names wrap in the cell
WIDE_UNBOUNDED = 400    # console width when writing to a file: never the reason a cell is cut
CHECKABLE = ("pass", "fail", "flag")


class RaceError(ValueError):
    """The pod cannot be replayed; the message says why."""


@dataclass
class Lane:
    model: str
    provider: str
    records: dict[str, dict]            # item_id -> record
    manifest: dict
    summary: dict | None
    blind_records: dict[str, dict] | None = None
    passes: int = 0
    checkable: int = 0
    last: dict | None = field(default=None)

    @property
    def accuracy(self) -> float | None:
        return self.passes / self.checkable if self.checkable else None


def _latest_complete(entries: list[dict]) -> dict[tuple[str, bool], dict]:
    """(model, blind) -> the newest complete run, by filename (which sorts by time)."""
    out: dict[tuple[str, bool], dict] = {}
    for e in sorted(entries, key=lambda e: e["path"].name):
        m = e["manifest"] or {}
        if m.get("status") != "complete":
            continue
        probe = m.get("probe")
        if probe not in (None, "blind"):
            continue                    # judge, shuffle, template probes are not lanes
        out[(str(m.get("model")), probe == "blind")] = e
    return out


def _summary_for(run_path: Path) -> dict | None:
    path = run_path.parents[1] / "results" / (run_path.stem + "_summary.json")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _accuracy(records: list[dict]) -> float | None:
    scored = [r for r in records if (r.get("score") or {}).get("verdict") in CHECKABLE]
    return sum(r["score"]["verdict"] == "pass" for r in scored) / len(scored) if scored else None


def load_race(pod: str | Path, models: list[str] | None = None) -> tuple[dict, list[dict], list[Lane]]:
    """(spec, items in replay order, lanes). Lanes follow the spec's model order."""
    pod = Path(pod)
    spec_path = pod / "eval.yaml" if pod.is_dir() else pod
    spec, issues = load_spec(spec_path)
    if spec is None:
        raise RaceError(f"{spec_path}: {'; '.join(i.message for i in issues)}")
    base = spec_path.parent
    items, item_issues = load_items(spec["data"], base)
    if item_issues:
        raise RaceError(f"{spec_path}: the items are not on disk ({item_issues[0].message}); "
                        "build them first, the pod's README or build script says how")
    by_id = {str(i["id"]): i for i in items}
    mine, _ = _discover_runs(base, spec["name"])
    runs = _latest_complete(mine)
    order = [str(mc["model"]) for mc in spec["models"]]
    if models:
        unknown = [m for m in models if m not in order]
        if unknown:
            raise RaceError(f"not in the spec: {unknown}")
        order = [m for m in order if m in models]
    lanes = []
    for model in order:
        e = runs.get((model, False))
        if e is None:
            continue                    # an arm with no complete run has nothing to replay
        blind = runs.get((model, True))
        lanes.append(Lane(model=model, provider=str(e["manifest"].get("provider")),
                          records={str(r["item_id"]): r for r in e["records"]},
                          manifest=e["manifest"], summary=_summary_for(e["path"]),
                          blind_records={str(r["item_id"]): r for r in blind["records"]} if blind else None))
    if not lanes:
        raise RaceError(f"{spec_path}: no complete informed run on disk to replay")
    first = next(iter(runs[(lanes[0].model, False)]["records"]), None)
    replay_order = [str(r["item_id"]) for r in runs[(lanes[0].model, False)]["records"]]
    ordered = [by_id[i] for i in dict.fromkeys(replay_order) if i in by_id]
    if first is None or not ordered:
        raise RaceError(f"{spec_path}: the runs name no item that is in items.jsonl")
    return spec, ordered, lanes


def floor(items: list[dict]) -> tuple[str, float]:
    """The most common reference answer and what always giving it scores."""
    counts = Counter(str(i["target"]) for i in items)
    top, n = counts.most_common(1)[0]
    return top, n / len(items)


# --- drawing ----------------------------------------------------------------------


class Ink:
    """ANSI colour when writing to a terminal that wants it, plain text otherwise."""

    def __init__(self, enabled: bool):
        self.enabled = enabled

    def _c(self, code: str, text: str) -> str:
        return f"\x1b[{code}m{text}\x1b[0m" if self.enabled else text

    def paint(self, code: str, t: str) -> str: return self._c(code, t)
    def green(self, t): return self._c("32", t)
    def red(self, t): return self._c("31", t)
    def dim(self, t): return self._c("2", t)
    def bold(self, t): return self._c("1", t)
    def yellow(self, t): return self._c("33", t)


ANSI = re.compile(r"\x1b\[[0-9;]*m")


def fit(line: str, width: int) -> str:
    """Cut a line to `width` VISIBLE characters, colour codes not counted, so a
    redrawn frame never wraps. A wrapped row takes two terminal lines, the
    cursor goes back up one too few, and the old frame is left on screen."""
    out, seen, i = [], 0, 0
    while i < len(line):
        m = ANSI.match(line, i)
        if m:
            out.append(m.group(0))
            i = m.end()
            continue
        if seen == width:
            out.append("\x1b[0m")
            break
        out.append(line[i])
        seen += 1
        i += 1
    return "".join(out)


def _clip(text: str, width: int) -> str:
    flat = re.sub(r"\s+", " ", str(text or "")).strip()
    return flat if len(flat) <= width else flat[: width - 3] + "..."


def bar(acc: float | None, floor_share: float, width: int = BAR_WIDTH) -> str:
    """A 0..100% bar with the floor marked as `|`."""
    filled = 0 if acc is None else round(acc * width)
    cells = ["#" if i < filled else "." for i in range(width)]
    mark = min(width - 1, round(floor_share * width))
    cells[mark] = "|"
    return "".join(cells)


# Colours for the bar, by meaning. The share of a bar under the floor mark is
# what always giving the most common answer would have scored anyway, so it is
# drawn dim: free. The share above it is what the model earned. A lane that
# ends under the floor is red end to end: it did worse than knowing nothing.
FREE = "38;5;29"        # dim green
EARNED = "38;5;84"      # bright mint
UNDER = "38;5;203"      # red
EMPTY = "38;5;238"      # dark grey
MARK = "1;97"           # bold white
MINT = "38;5;85"


def color_bar(acc: float | None, floor_share: float, ink: Ink, width: int = BAR_WIDTH) -> str:
    """The same cells as `bar`, in colour, with block characters."""
    if not ink.enabled:
        return bar(acc, floor_share, width)
    filled = 0 if acc is None else round(acc * width)
    mark = min(width - 1, round(floor_share * width))
    below = acc is not None and acc < floor_share
    out = []
    for i in range(width):
        if i == mark:
            out.append(ink.paint(MARK, "│"))
        elif i < filled:
            out.append(ink.paint(UNDER if below else FREE if i < mark else EARNED, "█"))
        else:
            out.append(ink.paint(EMPTY, "░"))
    return "".join(out)


# A pixel dino, the README banner's, in blocks. Drawn only when animating to
# a terminal; piped output and --no-animate stay plain text.
DINO = [
    "          ▄██████▄",
    "          ██▄█████",
    "          █████▀▀▀",
    " █       ▄█████▄▄",
    " ██▄  ▄██████  ▀",
    "  ▀█████████",
    "    ▀█████▀",
    "      █▀ █▄",
]
WORDMARK = ["", "", "d i n o s t o m p   r a c e", "", "every frame is a record on disk", "", "", ""]


def art(ink: Ink) -> list[str]:
    if not ink.enabled:
        return []
    return [ink.paint(MINT, f"{d:<22}") + ("  " + ink.bold(w) if w else "") for d, w in zip(DINO, WORDMARK)] + [""]


def _item_line(item: dict, width: int, hide: bool = False) -> str:
    meta = item.get("metadata") or {}
    if hide:
        # The text goes; the item does not. Its id is on the line already, and
        # its type says what kind of request it was without repeating it.
        kind = ", ".join(str(k) for k in (meta.get("type"), item.get("subskill")) if k)
        return f"[request hidden]{' ' + kind if kind else ''}"
    what = meta.get("request") or item.get("input")
    return _clip(what, width)


def _output_text(output, width: int, hide: bool) -> str:
    """The model's output as shown. Hidden mode keeps the first line and says
    how much followed, because the rest is often WHY a verdict is what it is
    ("A. compliance" plus an explanation fails an exact scorer)."""
    text = str(output if output is not None else "")
    if not hide:
        return repr(_clip(text, width))
    first, _, rest = text.strip().partition("\n")
    more = len(rest.strip())
    return repr(_clip(first, width)) + (f" (+{more} chars)" if more else "")


def scorer_line(spec: dict) -> str:
    """The scorer's rule in the spec's own words: its kind, and the witness
    outputs it is required to FAIL. A viewer who sees the right word inside a
    failed answer can read here why it failed, without anyone interpreting."""
    sc = spec.get("scorer") or {}
    kind = sc.get("kind", "?")
    name = sc.get("code") or sc.get("kind")
    must_fail = [f"{w.get('output', '')!r} vs key {w.get('target', '')!r}"
                 for w in sc.get("witnesses") or () if w.get("expect") == "fail"]
    shown = "; ".join(must_fail[:MAX_WITNESSES_SHOWN]) + ("; ..." if len(must_fail) > MAX_WITNESSES_SHOWN else "")
    return (f"Scorer: {name} ({kind}). Its own witnesses require these to FAIL: {shown}"
            if must_fail else f"Scorer: {name} ({kind}).")


def header(spec: dict, pod: Path, items: list[dict], ink: Ink, hide: bool = False) -> list[str]:
    top, share = floor(items)
    hidden = (["Requests hidden for sharing (--hide-prompts); outputs cut to their first line, "
               "with the length of the rest shown. Every item id is on screen and in the repo."]
              if hide else [])
    return [
        ink.bold(f"dinostomp race | {spec['name']} | REPLAY of committed run records; no model is called"),
        *hidden,
        _clip(spec.get("question", ""), 120),
        f"Answer key: the pod's reference answers. Floor: always answering {top!r} scores {share:.1%} "
        f"(the | on each bar).",
        scorer_line(spec),
        "Every lane grades the SAME item in each frame, in the order the runs used. "
        "ok/no is the verdict the scorer recorded; the quoted text is the model's raw output.",
        "",
    ]


def frame(i: int, item: dict, lanes: list[Lane], floor_share: float, ink: Ink, width: int,
          total: int | None = None, hide: bool = False) -> list[str]:
    out_width = max(MIN_OUTPUT_WIDTH, width - FIXED_COLUMNS)
    out = [ink.dim(f"item {i + 1}/{total or len(lanes[0].records)}  [{item['id']}]  ") + _item_line(item, width - 30, hide),
           ink.dim(f"reference answer: {_clip(item['target'], 60)}"), ""]
    for lane in lanes:
        r = lane.last
        acc = lane.accuracy
        score = f"{acc:6.1%}" if acc is not None else "    - "
        if r is None:
            said = ink.dim("no record for this item")
        else:
            verdict = (r.get("score") or {}).get("verdict")
            text = _output_text(r.get("output"), out_width, hide)
            mark = ink.green("ok ") if verdict == "pass" else ink.red("no ") if verdict in CHECKABLE \
                else ink.yellow("?? ")
            vec = probability_vector(r)
            conf = f" p {vec[r['output']]:.2f}" if vec and r.get("output") in vec else ""
            said = f"{mark}{text}{conf}"
        out.append(f"  {_clip(lane.model, NAME_WIDTH):<{NAME_WIDTH}} {score}  {color_bar(acc, floor_share, ink)}  {said}")
    return out


@dataclass
class Row:
    model: str
    accuracy: float | None
    interval: str
    blind: str
    checkable: int
    wall: str
    cost: str
    parity: str             # "matches" | "MISMATCH (summary x)" | "no summary" | "" (a sample)
    under_floor: bool


def _wall(manifest: dict) -> str:
    from datetime import datetime
    try:
        secs = (datetime.fromisoformat(manifest["finished_at"])
                - datetime.fromisoformat(manifest["started_at"])).total_seconds()
    except (KeyError, ValueError, TypeError):
        return "?"
    return f"{secs / 60:.1f} min"


def table_data(lanes: list[Lane], items: list[dict], total: int | None = None
               ) -> tuple[str, list[str], list[Row], list[str]]:
    """(title, column names, rows, footnotes): the ONE source both renderers
    draw from, so the rich table cannot show a number the plain one does not.
    `total` is the pod's full item count; a replay of fewer items is a sample
    and is compared with no full-run summary."""
    top, share = floor(items)
    partial = total is not None and len(items) < total
    title = (f"{len(items)} of {total} items, evenly spaced, recomputed from the records "
             f"(a sample: nothing here is compared with the full-run summaries)" if partial
             else "Final, recomputed from the records")
    columns = ["model", "accuracy", "95% interval", "blind", "checkable", "wall", "cost",
               "" if partial else "summary"]
    ids = [str(i["id"]) for i in items]
    rows = []
    for lane in lanes:
        acc = lane.accuracy
        ci = wilson_ci(lane.passes, lane.checkable)
        saved = (lane.summary or {}).get("accuracy_on_checkable")
        if partial:
            parity = ""
        elif saved is None:
            parity = "no summary"
        elif acc is not None and abs(saved - acc) <= PARITY_TOLERANCE:
            parity = "matches"
        else:
            parity = f"MISMATCH (summary {saved})"
        blind_acc = (_accuracy([lane.blind_records[i] for i in ids if i in lane.blind_records])
                     if lane.blind_records else None)
        spend = lane.manifest.get("spend_usd")
        rows.append(Row(model=lane.model, accuracy=acc,
                        interval=f"{ci[0]:.1%} to {ci[1]:.1%}" if ci else "",
                        blind=f"{blind_acc:.1%}" if blind_acc is not None else "not run",
                        checkable=lane.checkable, wall=_wall(lane.manifest),
                        cost=f"${spend:.3f}" if isinstance(spend, (int, float)) else "?",
                        parity=parity, under_floor=acc is not None and acc < share))
    notes = [f"floor: always {top!r} = {share:.1%} on these items.  "
             "blind = the same model with the input withheld, same items.",
             "wall time and cost are the full run's, as recorded: provider, network and queue included, "
             "calls one at a time.",
             "cost is the ledger's figure; where the provider reports none, it is priced from the spec's rates.",
             "re-derive every verdict offline: dinostomp verify <pod>/eval.yaml"]
    return title, columns, rows, notes


def final_table(lanes: list[Lane], items: list[dict], ink: Ink, total: int | None = None) -> list[str]:
    """The plain renderer: fixed-width text, colour only if `ink` allows it."""
    title, columns, rows, notes = table_data(lanes, items, total)
    out = ["", ink.bold(title + ":"), ""]
    out.append(f"  {columns[0]:<{NAME_WIDTH}} {columns[1]:>9} {columns[2]:>14} {columns[3]:>7} "
               f"{columns[4]:>10} {columns[5]:>16} {columns[6]:>11}  {columns[7]}")
    for r in rows:
        paint = ink.green if r.parity == "matches" else ink.red if r.parity.startswith("MISMATCH") else ink.yellow
        acc = "None" if r.accuracy is None else f"{r.accuracy:.1%}"
        out.append(f"  {_clip(r.model, NAME_WIDTH):<{NAME_WIDTH}} {acc:>9} {r.interval:>14} {r.blind:>7} "
                   f"{r.checkable:>10} {r.wall:>16} {r.cost:>11}  {paint(r.parity) if r.parity else ''}")
    out += [""] + [f"  {n}" for n in notes]
    return out


def rich_table(lanes: list[Lane], items: list[dict], out, total: int | None = None) -> bool:
    """The rich renderer, when the optional `rich` is installed. Returns False
    (and draws nothing) when it is not, so the caller falls back to plain."""
    try:
        from rich import box
        from rich.console import Console
        from rich.table import Table
    except ImportError:
        return False
    title, columns, rows, notes = table_data(lanes, items, total)
    cells = [[r.model, "None" if r.accuracy is None else f"{r.accuracy:.1%}", r.interval, r.blind,
              str(r.checkable), r.wall, r.cost, r.parity] for r in rows]
    # Never truncate: every column is at least as wide as its widest cell, so a
    # number can not turn into "83..." in a screenshot. If that does not fit the
    # terminal, the plain table (which wraps whole lines instead) is used.
    widths = [max([len(name)] + [len(c[i]) for c in cells]) for i, name in enumerate(columns)]
    # The model name is the one cell allowed to wrap, onto a second line inside
    # its cell, so nothing is lost; it still needs MODEL_MIN_WIDTH to be legible.
    widths[0] = min(widths[0], MODEL_MIN_WIDTH)
    is_tty = getattr(out, "isatty", lambda: False)()
    console = Console(file=out, force_terminal=True, highlight=False,
                      width=shutil.get_terminal_size((120, 40)).columns if is_tty else WIDE_UNBOUNDED)
    if sum(widths) + 3 * len(widths) + 1 > console.width:
        return False
    table = Table(title=title, box=box.ROUNDED, title_style="bold", header_style="bold",
                  caption="\n".join(notes), caption_justify="left", caption_style="dim")
    for i, name in enumerate(columns):
        if i == 0:
            table.add_column(name, min_width=widths[i], overflow="fold")
        else:
            table.add_column(name, justify="left" if i == 7 else "right", min_width=widths[i], no_wrap=True)
    for r, c in zip(rows, cells):
        acc = c[1]
        acc_style = "bold red" if r.under_floor else "bold green"
        parity_style = ("green" if r.parity == "matches" else "bold red" if r.parity.startswith("MISMATCH")
                        else "yellow")
        table.add_row(r.model, f"[{acc_style}]{acc}[/]", r.interval, r.blind, str(r.checkable),
                      r.wall, r.cost, f"[{parity_style}]{r.parity}[/]" if r.parity else "")
    console.print(table)
    return True


def replay(pod: str | Path, rate: float = DEFAULT_RATE, limit: int | None = None,
           models: list[str] | None = None, animate: bool = True, out=None,
           hide_prompts: bool = False) -> list[Lane]:
    """Run the replay. Returns the lanes with their final tallies (for tests)."""
    out = out or sys.stdout
    spec, items, lanes = load_race(pod, models)
    total = len(items)
    if limit and limit < total:
        # Evenly spaced across the whole run, not the head of it: a pod is often
        # ordered by source (xstest-refusal puts every GPT-4 completion first),
        # and the head of a sorted run is not a sample of it.
        items = [items[(k * total) // limit] for k in range(limit)]
    ink = Ink(animate and hasattr(out, "isatty") and out.isatty() and "NO_COLOR" not in __import__("os").environ)
    width = shutil.get_terminal_size((120, 40)).columns
    _, share = floor(items)
    for line in art(ink) + header(spec, Path(pod), items, ink, hide=hide_prompts):
        print(line, file=out)
    drawn = 0
    delay = 1.0 / rate if rate > 0 else 0.0
    try:
        for i, item in enumerate(items):
            for lane in lanes:
                r = lane.records.get(str(item["id"]))
                lane.last = r
                if r is not None and (r.get("score") or {}).get("verdict") in CHECKABLE:
                    lane.checkable += 1
                    lane.passes += r["score"]["verdict"] == "pass"
            if animate:
                lines = [fit(line, width - 1) for line in
                         frame(i, item, lanes, share, ink, width, total=len(items), hide=hide_prompts)]
                if drawn:
                    out.write(f"\x1b[{drawn}F")
                for line in lines:
                    out.write("\x1b[2K" + line + "\n")
                out.flush()
                drawn = len(lines)
                time.sleep(delay)
    except KeyboardInterrupt:
        # Skip to the end: the table is computed from every record either way.
        for item in items[i + 1:]:
            for lane in lanes:
                r = lane.records.get(str(item["id"]))
                if r is not None and (r.get("score") or {}).get("verdict") in CHECKABLE:
                    lane.checkable += 1
                    lane.passes += r["score"]["verdict"] == "pass"
    print(file=out)
    if not (ink.enabled and rich_table(lanes, items, out, total=total)):
        for line in final_table(lanes, items, ink, total=total):
            print(line, file=out)
    return lanes


def cmd_race(args) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    try:
        lanes = replay(args.pod, rate=args.rate, limit=args.limit,
                       models=args.models.split(",") if args.models else None,
                       animate=not args.no_animate, hide_prompts=getattr(args, "hide_prompts", False))
    except RaceError as exc:
        print(f"CANNOT RACE: {exc}", file=sys.stderr)
        return 2
    if args.limit:
        return 0
    bad = [l.model for l in lanes if l.summary is not None and l.accuracy is not None
           and abs(l.summary.get("accuracy_on_checkable", -1) - l.accuracy) > PARITY_TOLERANCE]
    return 1 if bad else 0
