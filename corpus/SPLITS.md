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
