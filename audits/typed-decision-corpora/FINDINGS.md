# Five public sets as typed decisions: what the audit found

Reviewed 2026-09-23 with dinostomp 0.63.0. Five public datasets were converted
into one shape, a text and a closed set of options with one right or none, to
train and measure a typed decision model, and every converted file was run
through `dinostomp stomp` before anything trained on it. This folder holds the
receipts, a verifier that re-derives the counts from the public releases
without dinostomp, and the ledger entries: [F-053](../../FINDINGS.md#f-053)
CLINC150, [F-054](../../FINDINGS.md#f-054) BANKING77,
[F-055](../../FINDINGS.md#f-055) FEVER, [F-056](../../FINDINGS.md#f-056)
QuALITY, and [N-040](../../FINDINGS.md#n-040) for TruthfulQA, where nothing
was found.

**Scope.** Structural properties of the public releases and of one conversion
of them. Nothing here is about model quality. The conversion is one of many
possible; the framing-independent counts (the verifier's) are about the
releases, and the framing-dependent ones (the receipts') are about this
conversion, and the two are labelled apart below.

## The sets

| set | release | license | shape here | rows built |
| --- | --- | --- | --- | ---: |
| CLINC150 | `clinc/clinc_oos`, config `plus` | CC BY 3.0 | which of ten intents from one domain; `oos` offers ten and no gold | 3,000 + 250 train, 1,000 + 100 held out |
| BANKING77 | the authors' GitHub CSVs (the Hub loader is a retired script) | CC BY 4.0 | which of ten intents | 3,000 train, 1,000 held out |
| FEVER, gold evidence | `copenlu/fever_gold_evidence` | CC BY-SA 3.0 | does the evidence support or refute the claim; `NOT ENOUGH INFO` has no gold | 3,000 + 3,000 train, 1,000 + 1,000 held out |
| TruthfulQA | `truthfulqa/truthful_qa`, config `multiple_choice` | Apache 2.0 | is this answer to the question true, one row per (question, `mc2` choice) | 3,128 train, 2,284 held out, split by question |
| QuALITY | `emozilla/quality` | not stated on the mirror; the origin records a license per article | which of four answers, over an article of about 5,000 tokens | 1,000 held out, audited only |

## What was found, in one table

Framing-independent counts are from `verify.py` over the full public splits.
Framing-dependent counts are from the receipts over the converted files.

| set | finding | count | independent of the framing |
| --- | --- | ---: | --- |
| CLINC150 | the gold intent's name appears whole-word in the message | 3,146 of 15,000 in-scope train rows (21.0%); 603 of 3,000 validation (20.1%); 942 of 4,500 test (20.9%) | yes |
| CLINC150 | answer leak: gold named in the message, no distractor named, ten options from the same domain | 3,107 of 15,249 train; 596 of 3,100 validation | no |
| CLINC150 | the option sharing the most words with the message is the gold one | 1,241 of 1,420 decidable items (87%) with domain-drawn negatives; 788 of 1,099 (72%) with overlap-drawn negatives | no |
| BANKING77 | the gold intent's name appears whole-word in the message | 203 of 10,003 train (2.0%); 65 of 3,080 test (2.1%) | yes |
| BANKING77 | the same message twice after folding hyphens, quotes and case | 21 train, 4 test | yes |
| BANKING77 | most-overlap option is the gold one | 607 of 1,046 (58%) with name-similar negatives; 415 of 896 (46%) with overlap-drawn negatives | no |
| BANKING77 | no-break space inside a message | 2 cells | yes |
| FEVER | a (claim, evidence) pair repeated verbatim | 110 of 228,277 train; 5 of 15,935 valid | yes |
| FEVER | the claim or evidence contains exactly one of the words "supports", "refutes" | 152 train; 12 valid | only for framings that name the options with those verbs |
| QuALITY | the gold option appears verbatim in the article and no distractor does | 35 of 2,086 validation (1.7%) | yes |
| QuALITY | no-break space in the article or question | 20 of 2,086 | yes |
| TruthfulQA | nothing, on 17 data checks over 5,412 rows | 0 | |

## What the conversion did about it

- Rows where the gold option is named in the input and no distractor is were
  dropped. The drop is not neutral: intents with literal names lose rows, and
  the counts above say how many.
- Negatives for the intent sets are the intents whose names share the most
  words with the message, which removed the exact-name leak and brought the
  most-overlap shortcut down without removing it. The residual is a property of
  intent names and is published as a non-gating warning in the receipts.
- Inputs are folded for whitespace, and one row is kept per input after folding
  case, quotes and hyphens.
- TruthfulQA's training half is balanced on the answer (the natural rate is 44%
  true); the held-out half keeps the natural rate.
- QuALITY is held out and audited only until its license is settled.

## Reproduce

```bash
python audits/typed-decision-corpora/verify.py --banking <dir with BANKING77 train.csv and test.csv>
```

Reads the Hugging Face cache; `--fetch` allows downloads. Prints counts and
row indices only. The receipts in `receipts/` are `dinostomp stomp <file>
--json` on each converted file with the `examples` field removed, so they carry
counts and check verdicts and no item text; `verify.json` is the verifier's
output. The converted files themselves are not vendored: each is a seeded,
deterministic function of its public release, and the conversion code is
private to the project that trains on them.

## Limits

One conversion, one seed, one reviewer. The framing-dependent counts change
with the number of options and how negatives are drawn; the framing-independent
ones do not. Whether any of these sets measures its intended construct is not
established by this audit.
