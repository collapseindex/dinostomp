"""Run ledger: stream to disk, resume, cap the spend.

Ported from the factwash pattern, which was built to the rule that came out of
losing ~$8 to an interrupted paid run: flush every item as it completes, resume
from the file, refuse any call that would blow the budget. Nothing buffers
results in memory until the end.

Layout:

    data/runs/YYYYMMDD_HHMMSS_<name>_<model>_<params>_s<seed>.jsonl   per-item records
    data/runs/..._manifest.json                                        run metadata
    data/results/..._summary.json                                      aggregates
"""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


# USD per million tokens for models we can price without being told.
# Anything absent is "unpriced": a network run then requires explicit rates.
PRICES_USD_PER_MTOK = {
    "claude-opus-5": (5.00, 25.00),
    "claude-fable-5": (10.00, 50.00),
    "claude-sonnet-5": (3.00, 15.00),
    "claude-haiku-4-5": (1.00, 5.00),
}

# Cache multipliers on the input rate (Anthropic). Ignoring these would
# understate spend, and the cap is only as honest as the number it checks.
CACHE_WRITE_MULTIPLIER = 1.25
CACHE_READ_MULTIPLIER = 0.10


class BudgetExceeded(RuntimeError):
    """Raised before a call that would exceed the cap. The run stops; nothing is lost."""


REPLACE_RETRIES = 5
REPLACE_RETRY_DELAY_S = 0.2


def _atomic_write_json(path: Path, obj: dict) -> None:
    """Write via temp file + rename so a kill mid-write never leaves torn JSON.

    On Windows, antivirus and indexing services briefly lock freshly written
    files, making os.replace throw WinError 32; a paid run must never die to
    a virus scanner's curiosity, so the rename retries.
    """
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2)
        fh.flush()
        os.fsync(fh.fileno())
    for attempt in range(1, REPLACE_RETRIES + 1):
        try:
            os.replace(tmp, path)
            return
        except PermissionError:
            if attempt == REPLACE_RETRIES:
                raise
            time.sleep(REPLACE_RETRY_DELAY_S * attempt)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_stamp() -> str:
    return utc_now().strftime("%Y%m%d_%H%M%S")


def slug(text: str) -> str:
    """Filename-safe token that keeps the convention parseable by splitting on '_'."""
    return re.sub(r"[^A-Za-z0-9.-]+", "-", str(text)).strip("-") or "na"


def rates_for(model: str) -> tuple[float, float, str]:
    """(input_rate, output_rate, rate_label) per MTok; ('unpriced' when unknown)."""
    if model in PRICES_USD_PER_MTOK:
        return (*PRICES_USD_PER_MTOK[model], model)
    return (0.0, 0.0, "unpriced")


@dataclass
class Budget:
    """A hard ceiling in USD. Checked before each call, updated from real usage."""

    cap_usd: float
    spent_usd: float = 0.0
    calls: int = 0

    @property
    def remaining_usd(self) -> float:
        return max(0.0, self.cap_usd - self.spent_usd)

    def check(self, estimate_usd: float) -> None:
        """Refuse a call whose worst-case cost would breach the cap."""
        if self.spent_usd + estimate_usd > self.cap_usd:
            raise BudgetExceeded(
                f"next call (est ${estimate_usd:.4f}) would exceed the ${self.cap_usd:.2f} cap; "
                f"spent ${self.spent_usd:.4f} over {self.calls} call(s)"
            )

    def record(self, actual_usd: float) -> None:
        self.spent_usd += actual_usd
        self.calls += 1


@dataclass
class Cost:
    """Cost of one call, raw usage payload kept verbatim.

    `raw` is preserved because provider usage fields differ and some hide
    tokens from the obvious counter. A wrong price table today stays
    recoverable arithmetic tomorrow.
    """

    input_tokens: int
    output_tokens: int
    usd: float
    rate_label: str
    raw: dict = field(default_factory=dict)

    # Nine decimals, not six. Small models bill fractions of a microdollar per
    # call, and rounding each of 120 records to 6dp accumulated enough error to
    # break R3's manifest-equals-ledger identity on the first real fleet. The
    # money invariant had only ever been exercised at exactly zero.
    USD_DECIMALS = 9

    def to_dict(self) -> dict:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cost_usd": round(self.usd, self.USD_DECIMALS),
            "rate_label": self.rate_label,
        }


def price_call(
    model: str,
    input_tokens: int,
    output_tokens: int,
    raw: dict | None = None,
    rate_in: float | None = None,
    rate_out: float | None = None,
    rate_label: str | None = None,
) -> Cost:
    """Price one call. Supplied rates (per MTok) override the table.

    `rate_label` records WHERE the rate came from, because provenance is the
    whole point: a rate declared in the spec is inside spec_sha256 and
    re-derivable by a stranger, while one typed at a shell prompt is gone the
    moment the command scrolls away. Collapsing both to "explicit" would throw
    that distinction away in the one place it is permanently recorded.
    """
    if rate_in is None or rate_out is None:
        table_in, table_out, label = rates_for(model)
        rate_in = table_in if rate_in is None else rate_in
        rate_out = table_out if rate_out is None else rate_out
    else:
        label = "explicit"
    label = rate_label or label
    raw = raw or {}
    cache_write = int(raw.get("cache_creation_input_tokens") or 0)
    cache_read = int(raw.get("cache_read_input_tokens") or 0)
    usd = (
        input_tokens * rate_in
        + cache_write * rate_in * CACHE_WRITE_MULTIPLIER
        + cache_read * rate_in * CACHE_READ_MULTIPLIER
        + output_tokens * rate_out
    ) / 1_000_000
    return Cost(input_tokens + cache_write + cache_read, output_tokens, usd, label, raw)


class RunLog:
    """Append-only JSONL ledger. Every record is flushed and fsynced on write.

    Resumability is keyed on the record's `key` field (item id + repeat):
    reopening an existing run reads the keys already on disk and `is_done()`
    lets the driver skip them without re-paying.
    """

    def __init__(
        self,
        operation: str,
        model: str,
        params: str,
        seed: int,
        data_dir: Path,
        resume_path: Path | None = None,
    ):
        base = Path(data_dir)
        (base / "runs").mkdir(parents=True, exist_ok=True)
        (base / "results").mkdir(parents=True, exist_ok=True)
        self.base = base
        self.resumed = resume_path is not None

        if resume_path is not None:
            self.path = Path(resume_path).resolve()
            if not self.path.is_file():
                raise FileNotFoundError(f"cannot resume: no such run file: {self.path}")
        else:
            name = f"{utc_stamp()}_{slug(operation)}_{slug(model)}_{slug(params)}_s{int(seed)}.jsonl"
            self.path = base / "runs" / name
            # slug() can collide (gpt_4o and gpt-4o both slug to gpt-4o). A
            # collision must never append into another model's ledger.
            counter = 2
            while self.path.exists():
                self.path = base / "runs" / f"{Path(name).stem}-{counter}.jsonl"
                counter += 1

        self.manifest_path = self.path.with_name(self.path.stem + "_manifest.json")
        self._done: set[str] = set()
        self.prior_spend_usd = 0.0
        if self.path.exists():
            self._load_existing()
        self._fh = self.path.open("a", encoding="utf-8")

    def _load_existing(self) -> None:
        text = self.path.read_text(encoding="utf-8")
        if text and not text.endswith("\n"):
            # A hard kill tore the final line mid-write. Truncate the wreckage
            # so the ledger holds only complete records; the torn item was
            # never marked done, so it is simply re-run.
            keep = text.rfind("\n") + 1
            self.path.write_bytes(text[:keep].encode("utf-8"))
            text = text[:keep]
        for line in text.splitlines():
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue  # mid-file corruption is left for the stomp battery to flag
            if rec.get("key"):
                self._done.add(rec["key"])
            self.prior_spend_usd += float((rec.get("usage") or {}).get("cost_usd") or 0.0)

    def is_done(self, key: str) -> bool:
        return key in self._done

    @property
    def done_count(self) -> int:
        return len(self._done)

    def append(self, record: dict) -> None:
        """Write one record durably. Costs a syscall per item; that is the point."""
        self._fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        self._fh.flush()
        os.fsync(self._fh.fileno())
        if record.get("key"):
            self._done.add(record["key"])

    def write_manifest(self, meta: dict) -> None:
        meta = {**meta, "run_file": self.path.name}
        _atomic_write_json(self.manifest_path, meta)

    def write_summary(self, summary: dict) -> Path:
        out = self.base / "results" / (self.path.stem + "_summary.json")
        _atomic_write_json(out, summary)
        return out

    def records(self) -> list[dict]:
        out = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return out

    def close(self) -> None:
        if not self._fh.closed:
            self._fh.flush()
            os.fsync(self._fh.fileno())
            self._fh.close()

    def __enter__(self) -> "RunLog":
        return self

    def __exit__(self, *exc) -> None:
        self.close()
