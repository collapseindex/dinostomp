"""Verify structural observations directly from a local Nemotron Parquet file.

Requires the optional PyArrow package. No network requests or model calls.
Usage: python verify.py validation.parquet --output data/exports/nvidia-audit/report.json
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

BATCH_ROWS = 1000
HASH_BYTES = 1024 * 1024
MAX_SOURCE_BYTES = 100 * 1024 * 1024
MAX_EXAMPLES = 8
LETTERS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'


def digest_file(path: Path) -> str:
    """Hash an artifact without loading it into memory."""
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(HASH_BYTES), b''):
            digest.update(chunk)
    return digest.hexdigest()


def inspect_source(source: Path) -> dict:
    """Count structural properties without treating options as question stems."""
    import pyarrow.parquet as pq

    counts = Counter()
    examples: dict[str, list[str]] = {}
    seen_ids: set[str] = set()
    def record(name: str, item_id: str) -> None:
        counts[name] += 1
        values = examples.setdefault(name, [])
        if len(values) < MAX_EXAMPLES:
            values.append(item_id)

    with pq.ParquetFile(source) as parquet:
        for batch in parquet.iter_batches(batch_size=BATCH_ROWS):
            for row in batch.to_pylist():
                counts['rows'] += 1
                item_id = str(row.get('uuid') or '')
                pairs = []
                for slot in row.get('options') or []:
                    active = [(k, str(slot[k])) for k in LETTERS
                              if slot.get(k) is not None and str(slot[k]).strip()]
                    if len(active) > 1:
                        record('multiple_active_keys_in_option_slot', item_id)
                    pairs.extend(active)
                key = row.get('expected_answer')
                letters = [k for k, _ in pairs]
                texts = [text for _, text in pairs]
                if key not in letters:
                    record('expected_answer_not_in_nonempty_option_keys', item_id)
                if len(texts) != len(set(texts)):
                    record('exact_duplicate_option_text_items', item_id)
                if any('|' in text for text in texts):
                    record('items_with_pipe_inside_option_text', item_id)
                if item_id in seen_ids:
                    record('repeated_uuid_after_first_global', item_id)
                seen_ids.add(item_id)
                meta = row.get('template_metadata') or {}
                if meta.get('prompt_type') == 'benchmark':
                    counts['benchmark_prompt_type_rows'] += 1
                if letters == ['A']:
                    record('only_nonempty_option_key_is_A', item_id)
                    if key != 'A':
                        record('only_A_present_but_expected_answer_is_other', item_id)
                turns = (row.get('responses_create_params') or {}).get('input') or []
                prompt = next((str(t['content']) for t in turns if t.get('content')), '')
                if texts and all(text in prompt for text in texts):
                    counts['all_nonempty_option_texts_appear_in_rendered_prompt'] += 1
            del batch
    return {'source_file': source.name, 'sha256': digest_file(source),
            'method': 'Direct Parquet fields; no prompt-stem reconstruction or string separator.',
            'counts': dict(counts), 'example_uuids': examples,
            'limits': ['Validation artifact only; no training or model behavior claims.',
                       'Exact duplicate text is a structural observation, not semantic adjudication.',
                       'Missing option keys do not imply an unanswerable rendered prompt.']}


def main() -> None:
    """Validate local paths and write the independently computed receipt."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    source = args.source.resolve(strict=True)
    if source.suffix != '.parquet' or source.stat().st_size > MAX_SOURCE_BYTES:
        parser.error('Expected a local Parquet file no larger than 100 MiB.')
    output = args.output.resolve()
    if not output.is_relative_to(Path.cwd().resolve() / 'data') or output.suffix != '.json':
        parser.error('Output must be a JSON file under the current workspace data directory.')
    result = inspect_source(source)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    temporary.replace(output)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
