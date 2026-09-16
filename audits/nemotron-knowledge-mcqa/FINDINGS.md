# NVIDIA Nemotron knowledge MCQA: validation artifact audit

Reviewed 2026-09-15. Dataset: [nvidia/Nemotron-RL-knowledge-mcqa](https://huggingface.co/datasets/nvidia/Nemotron-RL-knowledge-mcqa).

**Scope: structural properties of one public validation artifact, 68,553 rows.**
This audit does not measure training outcomes, model quality, or semantic correctness.
The original sharded dinostomp audit was reviewed against the original Parquet
using a separate, direct-field verifier. The table below reports that verifier's
results, not a new run of dinostomp's full battery.

## Reproduced observations

| Direct observation | Count | Interpretation |
|---|---:|---|
| Expected answer is absent from the nonempty option keys | 608 rows | Structured key/option inconsistency. The rendered prompt may still contain the missing option as text. |
| At least two nonempty options have exactly identical text | 459 rows | Repeated option text, without normalization or semantic adjudication. |
| Only nonempty option key is A | 223 rows | Degenerate structured option list; this alone does not establish the parser's causal mechanism. |
| Only A is present, but expected answer is another key | 173 rows | Subset of the rows above and of the 608 inconsistencies; do not add these counts. |
| Repeated UUID occurrences after the first, across the whole split | 9 | Global identifier reuse; this does not by itself prove all repeated rows are identical. |

The [machine-readable receipt](../../data/exports/nvidia-audit/20260915_structural_verification.json)
includes example UUIDs and the exact source hash. Counts overlap and must not be
summed into a number of defective items. All 68,553 rows carry the `benchmark`
prompt type, but that label alone establishes no downstream use of this split.

## Corrections to the initial audit

The initial local audit used dinostomp v0.62.0 on two converted shards. Its
reports are preliminary evidence, not independent confirmation. Review found:

- **Question/choice contamination.** The inspected shard's `question` contains
  the displayed choices. The original extraction function's docstring says it
  removes the instruction header, but its implementation returns the full first
  content turn. A later, unrecorded conversion strips at least that header.
  Word overlap with this field can reflect the options' own text. The claimed
  41% shortcut and 73 answer leaks are not validated as stem-only effects.
- **Delimiter ambiguity.** Options were joined with `|` and the battery was
  given that same separator. Direct inspection finds 619 rows with `|` inside
  option text. Splitting this representation can change the number and content
  of choices. The original 647 target-not-offered flags are not interchangeable
  with the 608 direct key/option inconsistencies.
- **Different duplicate definitions.** The original 484 duplicate-option flags
  include normalization. The direct verifier counts 459 exact-text cases.
  Neither number substitutes for the other; normalized cases need review.
- **Global identifiers.** The original shards report 6 repeated UUIDs within
  shards. A global pass finds 9 repeated occurrences after the first.
- **Unsupported causal extrapolation.** No RL run or policy was examined.
  Statements that the model is being trained to exploit a shortcut are hypotheses,
  not conclusions from this validation artifact.
- **Replication language.** Adjacent halves processed by the same conversion
  and checks share failure modes. Similar rates do not independently validate
  those methods. The initial reproduction instructions omitted shard generation.

The initial length-bias, numeric-equivalence, whitespace, question/row duplicate,
and instruction-mechanism counts have not been independently re-established here.
The initial overall BROKEN verdict is not presented as the verdict of this review.
No new permanent F-series entries are assigned to unresolved flags.

## Reproduce

Use a local copy of the validation Parquet from the linked dataset. The exact
download revision was not recorded in the original audit, so identity is pinned
to bytes, not inferred from today's upstream `main`:

```text
SHA-256 b2dfb9ee23cfa28162d7f00ae142c7562ea5bbf17e3e7519b0d6a4141aee21a9
```

With PyArrow available (verification used PyArrow 21.0.0), run from the repo root:

```bash
python audits/nemotron-knowledge-mcqa/verify.py /path/to/validation.parquet \
  --output data/exports/nvidia-audit/local-verification.json
```

Compare the emitted hash and counts with the receipt. The script streams batches
of 1,000 rows, retains bounded witness examples, and tracks UUIDs globally.
It makes no network requests or model calls. It does not import the original
extractor, reconstruct option order, split option strings, or infer a question stem.

## Provenance and limits

Original local audit commit: `d7697e4`. The initial draft and reports are preserved
locally with SHA-256 hashes for review; they are not the published findings here.
The downloadable dataset and large derived JSONL files are not vendored.
Public outputs contain aggregate counts and dataset UUIDs, not full question text.

This is a mechanical review by the same project, not external validation or a
claim about NVIDIA's intent. No confidentiality or embargo instruction was found
in the supplied audit files. The findings above concern a publicly accessible
dataset, not an exploit or a private system. Training split behavior, model
performance, and whether the dataset measures its intended construct remain unknown.
