---
name: dinocorpus submission
about: Have your detector scored on a dinocorpus split
title: "[corpus] <your tool> on <split id>"
labels: corpus-submission
---

<!--
Run your detector over a split's instances and attach the submission JSON.
Format and scoring rules: corpus/README.md#submitting-a-detector

Scoring is one command and the result is published in corpus/LEADERBOARD.md
whatever it says, including if it is worse than dinostomp's. That is the point
of the thing.
-->

**Detector**  <!-- name and version, exactly as you want it published -->

**Split**  <!-- e.g. dev, heldout-2026-08. A score without a split id means nothing. -->

**How it was run**  <!-- the command, so somebody else can reproduce the number -->

```
```

**Submission JSON**  <!-- attach the file, or paste it if it is small -->

**Anything the score will not show**
<!--
Optional and genuinely wanted. If your tool is aimed at a scope this split does
not cover, or a class it deliberately ignores, say so: it goes in the row's
notes rather than being silently counted as a miss.
-->

---

<!--
Two things this repository promises you:

1. Your number is published as measured, not as negotiated.
2. If the corpus turns out to be wrong (a mislabelled instance, a planter that
   plants nothing, a class whose expected check cannot fire on that shape) it
   goes in FINDINGS.md as a defect in the corpus. Three of those are already
   there: D-045.
-->
