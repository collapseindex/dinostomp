# Writing an eval, or having a model write one

This document is addressed to whoever is holding the keyboard, which is
increasingly not a human. The spec format exists to be **written by an LLM and
corrected against machine-readable errors**, and this is the contract for doing
that.

If you are a model reading this repo to build an eval: everything you need is
here and in [src/dinostomp/schemas/](src/dinostomp/schemas/). You do not need to
read [METHODOLOGY.md](METHODOLOGY.md) to author. You need it to understand why
the linter is unhappy with you.

## The loop

Write, validate, read the issues, fix, repeat. The validator never raises and
never guesses; it returns every problem at once, each with a JSON path and a
sentence.

```python
from dinostomp import load_spec

spec, issues = load_spec("my-eval/eval.yaml")
for issue in issues:
    print(issue.check, issue.loc, issue.message)
```

```
schema $.name: 'My Eval' does not match '^[a-z0-9][a-z0-9_-]{0,63}$'
schema $.question: 'Short.' is too short
schema $.run: 'seed' is a required property
schema $.run: 'budget_usd' is a required property
schema $.scorer.witnesses: [{...}] is too short
schema $.scorer.witnesses: [{...}] does not contain items matching the given schema
schema $.version: 1 is not of type 'string'
```

Every line is actionable without reading prose: the path says where, the message
says what. `dinostomp validate <spec>` does the same from a shell and exits `2`
when anything is wrong, which is the form to use in an agent loop.

Two failure modes this format is built to prevent, and both show up above:

- **`run.seed` and `run.budget_usd` are required.** There is no unseeded run and
  no uncapped run. A model that omits them gets an error, not a default.
- **A scorer needs at least one witness it must REJECT.** `witnesses` is too
  short at one entry, and "does not contain items matching the given schema"
  means there is no `expect: fail` case. A scorer that cannot fail is not a
  scorer, and this is the rule with no off switch.

## The smallest legal spec

```yaml
name: capital-cities                    # lowercase slug
version: 0.1.0                          # semver STRING, quoted or unquoted but not a number
question: "Does the model name the capital city, bare, with no sentence around it?"

entitled_claims:
  - "Exact-match accuracy with a 95% interval on these 30 capital-city items."

data: {path: items.jsonl, format: jsonl}

models:
  - {provider: dry, model: dry-strong}   # offline, deterministic, free

scorer:
  kind: exact
  witnesses:
    - {output: "Paris", target: "Paris", expect: pass}
    - {output: "The capital is Paris", target: "Paris", expect: fail, why: "no credit for wrappers"}
    - {output: "Par", target: "Paris", expect: fail, why: "no credit for truncation"}
    - {output: "not Paris", target: "Paris", expect: fail, why: "a denied mention is not a mention"}

run: {n: 30, seed: 42, budget_usd: 0}
```

Items are one JSON object per line:

```jsonl
{"_canary": "dinostomp canary DO NOT TRAIN capital-cities-2026"}
{"id": "fr", "input": "What is the capital of France?", "target": "Paris"}
{"id": "jp", "input": "What is the capital of Japan?", "target": "Tokyo"}
```

The `_canary` line is skipped by the loader, covered by the data hash, and is
how you find out later whether your items ended up in someone's training set.
`dinostomp new <dir>` scaffolds one with a fresh uuid.

## Fields you will get wrong

These are the ones the linter argues with most, and the reasoning behind each,
because a rule you understand is a rule you stop tripping over.

| field | rule | why |
|---|---|---|
| `question` | one sentence, 10 to 300 chars | an eval that cannot state its question in a sentence is measuring more than one thing |
| `entitled_claims` | prose, human-read | anything not listed is an overclaim by definition |
| `claims` | typed, machine-checked | the spec picks its OWN evidentiary bar, which is why failing it gates |
| `scorer.witnesses` | ≥1 pass, ≥1 fail | the non-negotiable one |
| `run.seed` | required | there is no unseeded run |
| `run.budget_usd` | required, even at 0 | so the field is never an afterthought |
| `price_in` / `price_out` | per model, in the spec | a rate on a command line vanishes; a rate in the spec is inside `spec_sha256` |
| paths | relative, inside the pod | traversal is refused unless declared under `mounts`, which is what gets it hashed |

## Writing witnesses, which is the part that stalls

The witness gate is where authoring most often stops, human or model. Two moves:

**Ask the tool.** `dinostomp suggest-witnesses <spec>` proposes cases derived
from your own data and from named scoring-bug classes, and writes nothing.

**Then edit them.** The command reports what YOUR witnesses catch separately
from what the suggestions catch, and says so out loud when the suggestions are
carrying the suite. That split exists because accepting generated witnesses
wholesale fits them to the mutation gauntlet, which turns the gauntlet from an
independent test into the thing they were optimised against. Every suggestion
encodes a decision only the author can make: is case part of your contract? Is
a wrapped answer correct? The tool proposes; it does not decide.

One class worth naming, because it is the mistake this project made itself
while writing the GSM8K benchmark pod: a numeric scorer handed `""` or
`"one hundred"` returns **`uncheckable`**, not `fail`. It has not judged the
answer wrong; it has not judged it. Witnesses may `expect: uncheckable`, and
doing so is what kills the mutant that silently upgrades unparseable output
into a pass.

## Typed claims: say what you intend to prove

Prose in `entitled_claims` is read by humans. `claims` are compiled into
evidence requirements and gated by `claim-evidence` (C1):

```yaml
claims:
  - {type: accuracy, model: dry-alpha, min: 0.80, confidence: 0.95}
  - {type: superiority, better: dry-alpha, worse: dry-charlie, min_effect: 0.20, confidence: 0.95}
```

An accuracy claim requires the interval's **lower** bound to clear the minimum.
A superiority claim requires a seeded paired bootstrap to clear `min_effect`.
`dinostomp plan <spec>` tells you whether a superiority claim is even provable
at your `n` **before** any money moves, and authoring nonsense (a model that
does not exist, a model beating itself) dies at load time.

## Evaluating an agent, not a completion

An examinee does not have to be a hosted model. Point a spec at pod-local Python
and it mounts on the same rail as everything else: same budget cap, same ledger,
same witness gate, same drift boundary, same battery.

There are two rails, and choosing between them is the only real decision here.

**`python` — the agent writes its own trace.**

```yaml
models:
  - {provider: python, model: agent-a, entrypoint: agent.py:run}
trajectory:
  required_tools: [retrieve]
  forbidden_tools: [shell]
  max_steps: 6
```

```python
# agent.py.  ctx carries model, seed and params.
def run(item, ctx):
    hits = retrieve(item["input"])
    return {"output": answer(hits),
            "trajectory": [{"tool": "retrieve", "args": {"q": item["input"]},
                            "result": hits[0], "ok": True}]}
```

Simple, and honest about its limit: that trajectory is TESTIMONY. T1-T6 read it,
so they verify the record, not the execution, and an agent that leaves a call
out of its own trace cannot be caught by reading the trace.

**`mediated` — the harness holds the tools.**

```yaml
tools:                                    # required by this rail
  retrieve: tools.py:retrieve
  shell: tools.py:shell
models:
  - {provider: mediated, model: agent-a, entrypoint: agent.py:answer}
trajectory:
  forbidden_tools: [shell]                # DENIED at the call, not audited after
  max_steps: 6
isolation: {mode: subprocess, timeout_s: 60}    # optional; default is inprocess
```

```python
# agent.py.  THREE arguments, and the signature is how you tell the rails apart.
def answer(item, tools, ctx):
    hit = tools.retrieve(key=item["topic"])      # recorded by the harness
    return extract(hit)
```

Things that catch people out on this rail:

- **You cannot return a `trajectory`.** Doing so stops the run rather than being
  ignored, because steps the harness never saw would be unverifiable evidence in
  a record that claims to be a log.
- **A denied tool RAISES.** `tools.shell(...)` raises `ToolDenied` rather than
  returning empty, so an agent cannot mistake a refusal for a miss. Catch it if
  you want the agent to recover; the attempt is recorded either way.
- **A forbidden tool must still be listed in `tools`.** The harness can only
  enforce policy about tools it holds, and a `forbidden_tools` entry naming
  something the harness never offers is refused at load time as a line that does
  nothing.
- **`tools` and `mediated` require each other.** Either alone is refused.

### The ablation probe: is the answer actually using the evidence?

Only this rail can withhold a tool result, which is what makes the interesting
question askable:

```bash
dinostomp run examples/mediated/eval.yaml --probe ablate
```

Every tool RESULT is replaced by a marker; the calls, the items and the policy
are unchanged. **T7** compares the two runs. An answer that comes out identical
did not causally depend on its evidence, which is a different and much stronger
statement than **T4**'s "the answer appears somewhere in the retrieved text".

Write your agent to be DETERMINISTIC if you want T7 to mean anything, or use
`repeats`. A nondeterministic agent differs between the two arms by chance,
which makes T7 understate ungroundedness rather than overstate it.

### Should I turn on `isolation: subprocess`?

Use it when the agent is not yours, or when it is yours and you would rather it
could not read your API keys by accident. It runs the agent in a child process
with a credential-stripped environment, no tool code, a denied `socket` module
and an enforced timeout, at a cost of roughly 130ms per item.

Do not use it as a security boundary. It is containment, not confinement: the
filesystem is not confined and the network denial is defeatable. SECURITY.md has
the table of what it stops and the two escapes that still work.

## The loop, end to end

```bash
dinostomp new my-eval                    # scaffold
# ...write items.jsonl and edit eval.yaml...
dinostomp validate my-eval/eval.yaml     # exits 2 while anything is wrong
dinostomp stomp    my-eval/items.jsonl   # audit the DATA before spending anything
dinostomp suggest-witnesses my-eval/eval.yaml
dinostomp plan     my-eval/eval.yaml     # power and worst-case cost
dinostomp run      my-eval/eval.yaml
dinostomp stomp    my-eval/eval.yaml
dinostomp report   my-eval/eval.yaml     # STOMP.md + STOMP.json + badge
```

Note the third line. Auditing your items before you write a scorer is free,
takes a second, and catches the class of defect that is most expensive to
discover after you have paid for a run.

## Schemas

The five JSON Schemas in [src/dinostomp/schemas/](src/dinostomp/schemas/) are
the contract, and they are the authoritative answer to any question this
document leaves open:

| file | what it describes |
|---|---|
| `eval.schema.json` | the spec you are writing |
| `items.schema.json` | one dataset item after field mapping |
| `record.schema.json` | one run record |
| `manifest.schema.json` | a run's provenance sidecar |
| `report.schema.json` | what `stomp --json` emits |

They are also the interface for anything that wants to consume dinostomp's
output or produce evidence it can read, and that is now explicit rather than
implied: every check declares which fields it consumes, a check whose fields are
missing skips naming them, and `dinostomp import` brings another harness's log
in as conforming evidence with no privileges. If you are writing a producer,
`dinostomp evidence <spec>` tells you exactly which checks your output unlocks.
See "The evidence contract" in [METHODOLOGY.md](METHODOLOGY.md).
