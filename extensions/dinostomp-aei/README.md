# dinostomp-aei

Audit an [Anthropic Economic Index](https://www.anthropic.com/economic-index)
release against the contract its own README states.

```bash
pip install -e extensions/dinostomp-aei
dinostomp stomp aei_claude_ai_2026-06-26.csv
```

## Why this is an extension and not a core check

The release is not an eval. It has no questions, no answers and no model, so the
core battery declines it: the dataset audit reports that no column looks like the
input and stops rather than guessing a mapping. That refusal is correct, and it
is also the end of what the core can say.

What the release does have is documentation stating a column schema, a metric
vocabulary with units, a rounding rule, a hierarchy depth per category, half-open
monthly reporting periods, geo-code forms, and a suppression policy. That is an
evidence contract, and an evidence contract is checkable.

## The eleven checks

| id | what it asks | gates |
|---|---|---|
| A1 | the file carries exactly the documented columns | yes |
| A2 | every metric, geo level and category is one the README documents | yes |
| A3 | no value exceeds the documented two decimal places | yes |
| A4 | no value falls outside the range its documented unit permits | yes |
| A5 | no cell is published twice at the same grain | yes |
| A6 | partition families sum to 100 wherever the release declares that they do | yes |
| A7 | no row sits outside its category's documented hierarchy depth | yes |
| A8 | reporting periods tile as half-open calendar months | yes |
| A9 | every geo_id matches the form its geo_level documents | yes |
| A10 | node_name and node_external_id agree one-to-one | no |
| A11 | how much of each `pct` distribution was actually published | no |

## Three rules this extension holds itself to

**Where the README is silent, so is this.** The README lists three `use_case_*`
metrics but never says they sum to 100. A6 therefore does not assert that they
do. It measures whether the DATA holds the sum across essentially every group,
and only then treats an exception as a finding. An invariant a publisher never
claimed, asserted by an auditor and reported as a defect, is a fabricated
finding.

**Documented behaviour is never an alarm.** The README says a missing row means
a cell was not published rather than that it is zero. A11 therefore reports a
number and never warns. A finding guaranteed in advance carries no information;
it teaches the reader to skip the line.

**Integer cents, not floats.** Values are published rounded to two decimals, so
k of them may legitimately miss 100 by k/200. The first version tested that in
floating point and flagged `40.63 + 59.38`, which is 100.01 exactly and sits on
the permitted bound. That would have been a fabricated finding against a real
publisher, produced by an arithmetic bug. See D-050 in the ledger.

## The evidence tax

`negtest.py` runs a conforming miniature release that must stay silent, and ten
planted defects that must each fire their own check. Regenerate the fixtures with
`make_fixtures.py`. The core marks an extension `validated` for *declaring*
trials without running them (D-051), so these are run here and in
`tests/test_aei_extension.py` instead.

```
python extensions/dinostomp-aei/make_fixtures.py
python extensions/dinostomp-aei/negtest.py
```

## What these checks cannot tell you

Nothing here says a published number is correct, that the sample is
representative, or that the O\*NET mapping is sound. They say the release is
internally consistent with its own documentation, which is the precondition for
the harder questions rather than an answer to any of them.

Findings from the 2026-06-26 release are recorded as F-026 and N-018 in
[FINDINGS.md](../../FINDINGS.md).

Apache-2.0.
