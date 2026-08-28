# Issue draft

Target: `hendrycks/test` on GitHub (the source) and the Community tab of `cais/mmlu`
on Hugging Face. The Berkeley tarball itself was unreachable on 2026-08-27. The same
counts and strings reproduce in three separately hosted conversions (`cais/mmlu`,
`lighteval/mmlu`, `tasksource/mmlu`), which is strong evidence they originate upstream
rather than in any one conversion.

Drafted 2026-08-27 from `cais/mmlu`, config `all`, split `test`, 14,042 rows, revision
`c30699e8356da336a370243923dbaf21066bb9fe`, `datasets` 4.5.0. Filed 2026-08-27:
https://github.com/hendrycks/test/issues/29 and
https://huggingface.co/datasets/cais/mmlu/discussions/35

---

**Title:** Test split: 78 cross-subject exact overlaps (clinical_knowledge / college_medicine), 27 within-subject duplicates, and three repeated-keyed-option items not identified by MMLU-Redux 2.0 (two labelled `ok`, one unsampled)

## What this reports

A mechanical pass over the full 14,042-row test split. All overlap and duplicate
checks use exact string equality, so they are conservative with respect to
paraphrased, normalised, or semantically equivalent items. Three things:

1. **78 questions appear verbatim in both `clinical_knowledge` and `college_medicine`**
   (same question string, same four options, same answer index). That is 78 of
   `college_medicine`'s 173 rows (45%) and 78 of `clinical_knowledge`'s 265 (29%).
   Within each subject each shared item occurs once, so per-subject accuracy is
   unaffected. In the reference `hendrycks/test` evaluator, overall accuracy is
   `np.mean(np.concatenate(all_cors))` (`evaluate.py`), the mean over all
   test rows, so each of these 78 underlying questions contributes twice to that
   aggregate.
2. **27 rows exactly duplicate an earlier row in the same subject.** All 27 groups are
   pairs. `college_physics` 11 (22 of its 102 rows, 21.6%, are in a pair; 91 distinct
   exact items), `high_school_psychology` 11, `public_relations` 2,
   `elementary_mathematics` 1, `professional_psychology` 1, `us_foreign_policy` 1.
3. **Three items whose keyed answer string appears at two option positions that
   MMLU-Redux 2.0 did not flag.** Two are in Redux 2.0's sample and labelled `ok`
   (`international_law`, `sociology`); one was not sampled (`elementary_mathematics`).
   A fourth, `high_school_macroeconomics`, Redux already labels
   `multiple_correct_answers` and is listed only for completeness.

Prior work, so the scope is clear. The original MMLU-Redux (Gema et al., 2024,
arXiv:2406.04127) manually annotated 100 questions in each of 30 subjects; MMLU-Redux
2.0 extends this to 100 questions in each of all 57 subjects. Its taxonomy has a
`multiple_correct_answers` category, and Appendix I notes for College Physics that
"some questions (approximately 20%) were duplicated". The 21.6% in item 2 closely
matches that figure. `hendrycks/test`
issue #21 (January 2024) reported three repeated answer options in the validation
split, one of them the keyed answer. Neither covers the cross-subject overlap in item
1, the full-split within-subject count in item 2, or the three test-split items in
item 3.

## 1. Cross-subject overlap

All 78 groups are pairs and every pair is `clinical_knowledge` with `college_medicine`;
no other subject pair shares an exact full item under this key (question, four
options, answer index). Two examples, by test-split index:

```
488 (clinical_knowledge) = 1258 (college_medicine)
  "The key attribute in successful marathon running is:"
492 (clinical_knowledge) = 1359 (college_medicine)
  "With an increasing number of sprints the:"
```

The script below prints all 78 index pairs.

## 2. Within-subject exact duplicates

| subject | rows | later copies | rows in a pair | distinct exact items |
|---|---|---|---|---|
| college_physics | 102 | 11 | 22 (21.6%) | 91 |
| high_school_psychology | 545 | 11 | 22 (4.0%) | 534 |
| public_relations | 110 | 2 | 4 (3.6%) | 108 |
| elementary_mathematics | 378 | 1 | 2 (0.5%) | 377 |
| professional_psychology | 612 | 1 | 2 (0.3%) | 611 |
| us_foreign_policy | 100 | 1 | 2 (2.0%) | 99 |
| **total** | | **27** | **54** | |

Not counted, and reported by the script as a check: 51 cases where the same subject
repeats a question stem with a different option set (mostly `astronomy`; option wording
differs, so they are variants, not duplicates), and 0 rows with the same question and
options but a different answer index.

## 3. Items whose keyed answer appears at two option positions

Rows verbatim; `answer` is the 0-based index the dataset keys. Under index- or
letter-based scoring, two identical responses receive different correctness labels
depending only on which of the two positions is selected; under text-matched scoring
the item has three distinct option strings. Redux 2.0 status was checked on 2026-08-27 against
`edinburgh-dawg/mmlu-redux-2.0` by matching on the question string within the subject
config.

```
index 2178, elementary_mathematics   (not in the Redux 2.0 sample)
question: "Subtract. 2,396 – 1,709"
choices:  ["687", "687", "1,493", "1,695"]
answer:   0
```

```
index 6494, international_law   (in the Redux 2.0 sample, labelled ok)
question: "How are the members of the arbitral tribunal appointed?"
choices:  ["All the members of the arbitral tribunal are appointed by the parties",
           "All the members of the arbitral tribunal are appointed by the parties",
           "All the members of the arbitral tribunal are appointed by an impartial third party, such as the president of the ICJ",
           "All the members of the arbitral tribunal are appointed by the parties from a restricted list of arbitrators"]
answer:   0
```

```
index 13601, sociology   (in the Redux 2.0 sample, labelled ok)
question: "Economic aid has largely failed to promote modernization in the developing countries because:"
choices:  ["there are no clearly defined projects into which the money can be directed",
           "the United Nations has refused to call on rich countries to provide it",
           "debt repayments with interest can be greater than the amount of money received",
           "debt repayments with interest can be greater than the amount of money received"]
answer:   2
```

```
index 4021, high_school_macroeconomics   (already flagged by Redux 2.0 as multiple_correct_answers; listed for completeness)
question: "A stronger stock market is likely to cause which of the following changes in the consumption function and aggregate demand? CONSUMPTION FUNCTION     AGGREGATE DEMAND"
choices:  ["Increase     Increase", "No change     No change", "Increase     No change", "Increase     Increase"]
answer:   3
```
(The runs of spaces are non-breaking spaces, U+00A0, in the source; options 0 and 3
are equal as strings.)

Five further items repeat a non-keyed option string and therefore contain only three distinct option strings:
389 (`business_ethics`), 1941 (`electrical_engineering`), 3119 (`high_school_chemistry`),
4835 (`high_school_physics`), 13134 (`public_relations`).

## Suggested fix

If the split stays frozen for comparability with published numbers, publish this list
next to the dataset so evaluators can dedup at load time and decide how to handle the
clinical_knowledge / college_medicine overlap in pooled scores. Otherwise: drop the 27
later copies; for the four items in section 3, correct or deduplicate the option
list and adjust the key if necessary, or remove them; and decide which subject the 78
shared items belong to.

## Reproduce

```python
import collections
from datasets import load_dataset

REV = "c30699e8356da336a370243923dbaf21066bb9fe"
rows = load_dataset("cais/mmlu", "all", split="test", revision=REV)
assert len(rows) == 14042
keyed = lambda r: r["choices"][r["answer"]]

# exact duplicates, with and without subject in the key
by_all = collections.defaultdict(list)
by_sub = collections.defaultdict(list)
for i, r in enumerate(rows):
    by_all[(r["question"], tuple(r["choices"]), r["answer"])].append(i)
    by_sub[(r["subject"], r["question"], tuple(r["choices"]), r["answer"])].append(i)
dups_all = [v for v in by_all.values() if len(v) > 1]
dups_sub = [v for v in by_sub.values() if len(v) > 1]
assert all(len(v) == 2 for v in dups_all)
cross = [v for v in dups_all if len({rows[i]["subject"] for i in v}) > 1]

print("later copies, any subject:", sum(len(v) - 1 for v in dups_all))        # 105
print("within-subject:", sum(len(v) - 1 for v in dups_sub))                  # 27
print("cross-subject pairs:", len(cross),
      collections.Counter(tuple(sorted(rows[i]["subject"] for i in v)) for v in cross))
                                              # 78, all (clinical_knowledge, college_medicine)
per_subject = collections.Counter(rows[v[0]]["subject"] for v in dups_sub)
print("within-subject by subject:", per_subject.most_common())
print("cross-subject index pairs:")
for a, b in sorted(cross):
    print(f"  {a} ({rows[a]['subject']}) = {b} ({rows[b]['subject']})")

# side counts named in the text
stems = collections.defaultdict(set)
answers = collections.defaultdict(set)
for r in rows:
    stems[(r["subject"], r["question"])].add(tuple(r["choices"]))
    answers[(r["question"], tuple(r["choices"]))].add(r["answer"])
print("same subject and stem, different options:", sum(len(v) > 1 for v in stems.values()))   # 51
print("same question and options, different answer:", sum(len(v) > 1 for v in answers.values()))  # 0

double_keyed = [i for i, r in enumerate(rows) if r["choices"].count(keyed(r)) >= 2]
print("keyed answer at two positions:", double_keyed)                        # [2178, 4021, 6494, 13601]
repeated = [i for i, r in enumerate(rows) if len(set(r["choices"])) < 4 and i not in double_keyed]
print("non-keyed repeated option:", repeated)                                 # [389, 1941, 3119, 4835, 13134]
```

Indices are positions in the `all` config's test split at the pinned revision; if the
dataset is revised, match on the strings above.

Cross-check: the 78 shared items, the four items in section 3 (identical option
strings and answer indices), and the 11 College Physics duplicate pairs are also
present in `lighteval/mmlu` and `tasksource/mmlu`.
