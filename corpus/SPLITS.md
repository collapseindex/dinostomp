# dinocorpus splits

Every split ever released, and the commitment that makes its score checkable
later. **A score is only meaningful with a split id attached.** "92% on
dinocorpus" means nothing; "92% on dinocorpus `dev-v1`" means something.

## The rules

**Splits are archived, never replaced.** A rotating benchmark that quietly
overwrites itself makes every published number unverifiable, which is the exact
failure this repository exists to complain about. When a new split is released
the old one stays downloadable at its tag, and its scores stay valid as
statements about it.

**A withheld split publishes its instances and a commitment to its labels.**
`labels_sha256` in the split's `MANIFEST.json` is the SHA-256 of the labels
file, published at release time, before any submission is scored. When the split
is revealed anyone can hash the labels and check they are the ones committed to.
Without that, a scorekeeper holding unpublished labels can quietly change one
after seeing a submission, and a benchmark whose author can edit the answer key
after seeing the answers is not a benchmark.

**Held-back classes are counted, never named.** `n_held_back_classes_present`
says how many defect classes in the split are absent from the public taxonomy.
Knowing they exist is what stops a submitter reading `taxonomy.py`, writing one
checker per class, and calling the result a detector. Knowing WHICH would undo
it.

**A revealed split moves to `dev`.** Once labels are published a split can be
tuned against and its scores stop measuring generalisation. It is still useful
for development, and it is no longer evidence.

## Registry

| split | released | instances | status | labels_sha256 | notes |
|---|---|---:|---|---|---|
| `dev-v1` | 2026-08-10 | 204 | **public** | `021a18f2265b7801...` | labels ship; tune against this freely |
| `heldout-2026-08` | 2026-08-10 | 400 | **withheld** | `357ce1610cf93b8d...` | labels not published; 100 clean, 162 blind-spot |
| `heldout-2026-08b` | 2026-08-11 | 800 | **withheld** | `83a11a9a78b072fd...` | labels not published; 200 clean, 316 blind-spot |
| `heldout-assets-2026-08` | 2026-08-11 | 252 | **spent** | `ef589b3aee30c7e9...` | image-backed; found D-053 and was developed against; scores not reported |
| `heldout-assets-2026-08b` | 2026-08-11 | 252 | **withheld** | `acf88203a1b36dec...` | image-backed, post-fix; 63 clean, 81 blind-spot; **all 21 classes planted** |

The full commitment for each split is in its own `MANIFEST.json`. Every row was
written before any submission was scored against it.

`heldout-2026-08b` exists to answer one question and was scored exactly once,
with no tuning between generation and scoring. The false-alarm rate on `dev`
(15.7%, 8 of 51) sat 2.2 standard deviations above the rate on `heldout-2026-08`
(5.0%, 5 of 100), and the write-up said a third split would settle it while also
claiming the corpus scales by generation. Those two sentences cannot both stand,
and generating a split is one command.

**Its labels stay withheld.** The score and the commitment are published, which
is what makes the result checkable by someone else. Publishing the labels would
move the split to `dev` under the rule above, spending a held-out split to
re-answer a question that is now answered.

**A fourth status: `spent`.** `heldout-assets-2026-08` was scored once, blind,
against its commitment, and returned 99.1% on the covered arm. That single miss
was [D-053](../FINDINGS.md#d-053), a hole in a gating check. We fixed the tool
because of it, which means the split was developed against, which means its
post-fix 100% is not a held-out number. The rule two sections up says a split
that can be tuned against stops measuring generalisation, and a bug found by a
split and repaired because of it is tuning by any reading that matters.

So the split is retired rather than re-reported. `heldout-assets-2026-08b` is a
fresh split generated after the fix, committed, and scored once: it returns the
same 100%, and that figure is worth something because nothing was developed
against it. Regenerating cost one command. The alternative was a headline number
whose provenance needed a paragraph of explanation, which is the shape of every
result this project exists to complain about.

The image-backed splits work like this. Every instance
carries six PNGs, clean instances included, and that symmetry is the point: four
defect classes describe things that happen to files rather than to text, and if
only defective instances had images then the four checks that read them would
never meet clean data. Their recall would be unfalsifiable, since a check firing
on every image-bearing instance would score 100% with nothing able to contradict
it. With this split the corpus plants **all 21 declared classes** for the first
time; `classes_declared_not_yet_planted` is empty.

One dependency caveat that belongs on the split rather than in a footnote: S15
decodes pixels and needs the `[vision]` extra. Without it that check skips, and
`near-duplicate-asset` scores as a miss for a reason that has nothing to do with
detection. A submitter reporting a number on this split should say whether the
extra was installed.

**Nine of the 189 defective instances announce themselves to `ls`.** The
`label-in-path` defect *is* a directory named after the answer, so an instance
carrying it necessarily contains `images/alpha/` or `images/beta/`. Exactly 9
instances have such a directory and all 9 are that class, so nothing beyond the
defect leaks, but it does mean 4.8% of the defective arm can be labelled by
listing files rather than by detecting anything. That is unavoidable for this
class and it is stated here so no one has to discover it: a submission that
scored well *only* on `label-in-path` has demonstrated `find`, not detection.

`heldout-2026-08` carries **0 held-back classes**, because `holdback.py` does
not exist yet. That is stated rather than implied: until it does, the
taxonomy-overfitting defence is documented and not armed, and a submitter who
writes one checker per published class can still score well on this split.

## Releasing a withheld split

```bash
export DINOCORPUS_NONCE="$(python -c 'import secrets;print(secrets.token_hex(32))')"
python corpus/generate.py --split heldout-2026-09 -n 400
```

Then, in order, and the order matters:

1. **Record the nonce** somewhere durable. A split that cannot be regenerated
   cannot be revealed, and an unrevealable split is a number nobody can check.
2. **Commit the instances and the MANIFEST.** Not `labels.WITHHELD.jsonl`; it is
   gitignored, and the gitignore rule is the only thing between it and a push.
3. **Add the row to the registry above**, with the commitment, BEFORE scoring
   anything. A commitment published after the first submission commits to
   nothing.
4. Tag the release so the split is fetchable at a fixed point forever.

## What rotation does and does not defend

Rotation is nearly free here, which is a real advantage over hand-annotated
benchmarks: refreshing those costs an annotation budget every time, which is why
they do not rotate. But it defends against exactly one thing.

**Instance memorisation.** Rotation is the right answer, and it matters for the
model task, where a solver can memorise instances it has seen.

**Taxonomy overfitting.** Rotation does nothing. A rule-based detector cannot
memorise an instance; it is written against the class. Somebody who reads
`taxonomy.py` and writes twenty-one checkers scores well on every rotation
forever. **Held-back classes are the defence against that one**, and they are
the reason a new split is worth generating even when nothing else changed.
