"""CUDA Agent (arXiv:2602.24286) audit. No GPU, no API calls, no money.

    paper      https://arxiv.org/abs/2602.24286
    dataset    https://huggingface.co/datasets/BytedTsinghua-SIA/CUDA-Agent-Ops-6K
    repo       https://github.com/BytedTsinghua-SIA/CUDA-Agent  (473025c8)
    reference  https://github.com/ScalingIntelligence/KernelBench (423217d9)

The first audit here whose subject is a TRAINING corpus and an RL reward
instrument rather than an eval and its scorer. The paper's headline is a speed
claim against `torch.compile`; nothing in this file can check a speedup, because
none of the released artifacts contain one. What they do contain is the
apparatus that produced the reward, which is the thing this repo exists to read.

Four legs, in increasing order of how much they need:

  1. DUPLICATES in the released training set        (dataset only)
  2. DECONTAMINATION against KernelBench            (--kernelbench)
  3. `ops` LABEL against each sample's own code     (dataset only)
  4. the anti-reward-hacking GUARD                  (--cuda-agent, needs torch)

Leg 2 carries a positive control, because it is the leg that can come back
clean: three known contaminants are planted and the check has to find them. A
green line from a check that cannot fire is not evidence.

    python audits/cuda-agent/audit.py
    python audits/cuda-agent/audit.py --kernelbench ../KernelBench --cuda-agent ../CUDA-Agent
"""

from __future__ import annotations

import argparse
import ast
import collections
import hashlib
import json
import sys
import urllib.parse
import urllib.request
from contextlib import contextmanager  # noqa: F401 - used by the lifted guard
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "src"))

from dinostomp.lint import lint_dataset  # noqa: E402
from dinostomp.overlap import find_overlap, is_template_sibling, jaccard, shingles  # noqa: E402

ROWS_URL = ("https://datasets-server.huggingface.co/rows"
            "?dataset=BytedTsinghua-SIA%2FCUDA-Agent-Ops-6K&config=default&split=train")
N_ROWS = 6000
PAGE = 100
CACHE = HERE / "data" / "ops6k.jsonl"

# Operators with a syntax form: `torch.add(a, b)` is written `a + b`, so their
# absence from an AST is not evidence the code does not use them. Excluded from
# the mismatch count rather than counted as a miss.
SUGAR = {"add", "sub", "mul", "div", "truediv", "floor_divide", "pow", "matmul",
         "neg", "remainder", "mod", "eq", "ne", "lt", "gt", "le", "ge",
         "logical_and", "logical_or", "logical_not", "bitwise_and", "bitwise_or",
         "bitwise_xor", "invert", "getitem", "index_select", "abs", "round"}
TORCH_ROOTS = {"torch", "nn", "F", "functional"}
NOISE = {"Module", "Parameter", "Tensor", "randn", "rand", "randint", "tensor",
         "zeros", "ones", "empty", "arange", "no_grad", "device", "cuda",
         "float32", "float16", "manual_seed", "Size", "dtype", "nn",
         "functional", "utils", "init"}


def head(title: str) -> None:
    print(f"\n{title}\n{'-' * len(title)}")


# --------------------------------------------------------------------------- data

def load_dataset() -> list[dict]:
    """The released training set, cached after the first run."""
    if CACHE.is_file():
        rows = [json.loads(line) for line in CACHE.read_text(encoding="utf-8").splitlines()
                if line.strip()]
        print(f"dataset: {len(rows)} rows from cache ({CACHE.relative_to(REPO)})")
        return rows
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    while len(rows) < N_ROWS:
        page = urllib.request.urlopen(  # noqa: S310 - pinned https
            f"{ROWS_URL}&offset={len(rows)}&length={PAGE}", timeout=60).read()
        got = json.loads(page).get("rows") or []
        if not got:
            break
        rows.extend({"id": f"ops6k-{r['row_idx']:04d}", "code": r["row"]["code"],
                     "ops": r["row"]["ops"], "data_source": r["row"]["data_source"]}
                    for r in got)
        print(f"  {len(rows)} rows so far")
    CACHE.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
                     encoding="utf-8", newline="\n")
    print(f"dataset: {len(rows)} rows -> {CACHE.relative_to(REPO)}")
    return rows


def kernelbench_items(root: Path) -> list[dict]:
    """The 250 evaluation problems, levels 1-3, as an overlap reference."""
    items = []
    for level in ("level1", "level2", "level3"):
        for f in sorted((root / "KernelBench" / level).glob("*.py")):
            items.append({"id": f"{level}/{f.name}",
                          "input": f.read_text(encoding="utf-8")})
    return items


# ------------------------------------------------------------------- operator sets

def ops_used(src: str) -> frozenset[str]:
    """Every name this module could be calling an operator by. PERMISSIVE.

    Used to prove an operator ABSENT, so it counts every attribute in the file
    (`x.tril()` counts) and every torch import. Over-counting uses makes a
    "declared but never used" finding harder to get, which is the direction an
    audit should err in.
    """
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return frozenset()
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and (node.module or "").split(".")[0] == "torch":
            for a in node.names:
                found.add(a.name)
                found.add(a.asname or a.name)
        elif isinstance(node, ast.Attribute):
            found.add(node.attr)
        elif isinstance(node, ast.Name):
            found.add(node.id)
    return frozenset(found) - NOISE


def ops_signature(src: str) -> frozenset[str]:
    """The torch operators this module calls. STRICT, and the opposite bet.

    `ops_used` counts every attribute in the file so that calling an operator
    absent is hard. That is useless for asking "are these two the same problem",
    where `self.batch_norm` and `shape` are not operators and their presence
    makes every file unique. So this counts only names that are unambiguously
    torch: imported from a torch module, or an attribute of torch / nn / F.
    """
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return frozenset()
    found: set[str] = set()
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and (node.module or "").split(".")[0] == "torch":
            for a in node.names:
                imported.add(a.asname or a.name)
                found.add(a.name)
        elif isinstance(node, ast.Attribute):
            base = node.value
            root = (base.id if isinstance(base, ast.Name) else
                    base.attr if isinstance(base, ast.Attribute) else None)
            if root in TORCH_ROOTS:
                found.add(node.attr)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
                and node.func.id in imported:
            found.add(node.func.id)
    return frozenset(found) - NOISE


def ops_declared(label) -> frozenset[str]:
    if isinstance(label, str):
        try:
            label = ast.literal_eval(label)
        except (ValueError, SyntaxError):
            label = [label]
    if isinstance(label, str):
        label = [label]
    return frozenset(str(x).split(".")[-1] for x in label) - NOISE


# ------------------------------------------------------------------------- the legs

def leg_duplicates(rows: list[dict]) -> None:
    head("1. duplicates in the released training set")
    report, issues, _ = lint_dataset(CACHE, field_overrides={"input": "code", "target": "ops",
                                                            "id": "id"})
    if report is None:
        print(f"  cannot stomp: {issues[0].message if issues else '?'}")
        return
    s1 = next(f for f in report["findings"] if f["id"] == "S1")
    print(f"  dinostomp S1 [{s1['level']}]: {s1['detail']}")

    # Independent of dinostomp's normalisation: a dedupe finding that exists
    # only after lowercasing is a finding about lowercasing.
    raw = collections.Counter(r["code"] for r in rows)
    dups = {k: v for k, v in raw.items() if v > 1}
    norm = collections.Counter(" ".join(r["code"].lower().split()) for r in rows)
    ndups = sum(v - 1 for v in norm.values() if v > 1)
    labels = collections.defaultdict(set)
    for r in rows:
        labels[r["code"]].add(str(r["ops"]))
    print(f"  byte-identical repeats of an earlier row : {sum(v - 1 for v in dups.values())}")
    print(f"  same count after lowercase+whitespace    : {ndups}")
    print(f"  distinct code values                     : {len(raw)} of {len(rows)}")
    print(f"  largest cluster                          : x{max(dups.values()) if dups else 0}")
    print(f"  dup clusters with conflicting ops labels : "
          f"{sum(1 for k, v in labels.items() if raw[k] > 1 and len(v) > 1)}")


def leg_decontamination(rows: list[dict], kb_root: Path | None) -> None:
    head("2. decontamination against KernelBench")
    if kb_root is None or not (kb_root / "KernelBench").is_dir():
        print("  skipped: pass --kernelbench <path to a KernelBench clone>")
        print("    git clone https://github.com/ScalingIntelligence/KernelBench")
        return
    refs = kernelbench_items(kb_root)
    items = [{"id": r["id"], "input": r["code"]} for r in rows]
    hits, stats = find_overlap(items, {"kernelbench": refs})
    print(f"  {len(refs)} reference problems, {len(items)} training samples")
    print(f"  hits: {stats['exact']} exact / {stats['stem_only']} same-question / "
          f"{stats['near']} near-verbatim / {stats['template_siblings']} suppressed as "
          f"template siblings")

    # POSITIVE CONTROL. The paper's threshold is AST similarity 0.9; this check
    # is character shingles. Either way a zero means nothing until the check is
    # shown to fire on contamination it was handed.
    picks = [refs[0], refs[len(refs) // 2], refs[-1]]
    renamed = (picks[1]["input"].replace("class Model(", "class FusedOp(")
               .replace("import torch", "# synthesised operator task\nimport torch", 1))
    retuned = picks[2]["input"]
    for a, b in ((" 4096", " 2048"), ("128", "256"), ("16", "32"), ("1024", "512")):
        retuned = retuned.replace(a, b)
    planted = items + [{"id": "seeded-verbatim", "input": picks[0]["input"]},
                       {"id": "seeded-renamed", "input": renamed},
                       {"id": "seeded-retuned", "input": retuned}]
    found = {h["id"]: h for h in find_overlap(planted, {"kernelbench": refs})[0]}
    print("  positive control:")
    for sid in ("seeded-verbatim", "seeded-renamed", "seeded-retuned"):
        h = found.get(sid)
        verdict = f"FLAGGED {h['kind']} sim={h['similarity']}" if h else "NOT FLAGGED"
        print(f"    {sid:18s} {verdict}")
    a, b = picks[2]["input"], retuned
    print(f"    the retuned case is jaccard {jaccard(shingles(a), shingles(b)):.3f} from its "
          f"original and template_sibling={is_template_sibling(a, b)}, which is the "
          f"exemption that hides it")

    # Neither instrument counts this as contamination, and it is the similarity
    # the paper's own filter is stated in terms of ("operators that exhibit high
    # similarity to KernelBench test cases"). For kernel generation the thing
    # that transfers is the kernel you learned to write for operator X, which
    # survives a total rewrite of the module around it.
    print("  operator-set overlap (neither their AST threshold nor S11 counts this):")
    sigs = {r["id"]: ops_signature(r["code"]) for r in rows}
    for level in ("level1", "level2", "level3"):
        by_sig = {ops_signature(r["input"]): r["id"] for r in refs
                  if r["id"].startswith(level) and ops_signature(r["input"])}
        exact = [i for i, s in sigs.items() if s and s in by_sig]
        print(f"    {level}: {len(by_sig)} distinct signatures among the problems "
              f"-> {len(exact)} of {len(rows)} training rows match one exactly")
        for sig, n in collections.Counter(tuple(sorted(sigs[i])) for i in exact).most_common(3):
            print(f"      {list(sig)} x{n} == {by_sig[frozenset(sig)]}")


def leg_labels(rows: list[dict]) -> None:
    head("3. the `ops` label against each sample's own code")
    torch_rows = [r for r in rows if str(r["data_source"]).startswith("torch")]
    missing, sugar_only = [], 0
    absent = collections.Counter()
    for r in torch_rows:
        declared, used = ops_declared(r["ops"]), ops_used(r["code"])
        gone = (declared - used) - SUGAR
        if gone:
            missing.append((r["id"], sorted(gone), sorted(declared)))
            absent.update(gone)
        elif declared - used:
            sugar_only += 1
    pct = 100 * len(missing) / len(torch_rows) if torch_rows else 0
    print(f"  torch-sourced rows                                  : {len(torch_rows)}")
    print(f"  declaring an operator absent from their own code    : {len(missing)} ({pct:.1f}%)")
    print(f"  excluded because the operator has a syntax form     : {sugar_only}")
    print(f"  most frequently declared-but-absent                 : {absent.most_common(8)}")
    for rid, gone, declared in missing[:4]:
        print(f"    {rid}: absent {gone}  declared {declared}")


def leg_guard(cuda_agent: Path | None) -> None:
    head("4. the anti-reward-hacking guard")
    if cuda_agent is None:
        print("  skipped: pass --cuda-agent <path to a CUDA-Agent clone>")
        print("    git clone https://github.com/BytedTsinghua-SIA/CUDA-Agent")
        return
    verify = cuda_agent / "agent_workdir" / "utils" / "verification.py"
    if not verify.is_file():
        print(f"  skipped: no {verify}")
        return
    try:
        import torch
        import torch.nn as nn
        import torch.nn.functional as F
    except ImportError:
        print("  skipped: torch is not installed (CPU-only is enough for this leg)")
        return

    # verification.py imports model_new at module scope, which needs the compiled
    # CUDA extension, so it cannot be imported. Lift the guard out by AST: what
    # runs below is their source, verbatim.
    src = verify.read_text(encoding="utf-8")
    fn = next(n for n in ast.parse(src).body
              if isinstance(n, ast.FunctionDef) and n.name == "block_torch_functional")
    ns = {"contextmanager": contextmanager, "F": F, "torch": torch}
    exec(compile(ast.Module(body=[fn], type_ignores=[]), str(verify), "exec"), ns)  # noqa: S102
    guard = ns["block_torch_functional"]
    print(f"  guard lifted verbatim from verification.py lines {fn.lineno}-{fn.end_lineno}")

    # Bound BEFORE the guard, exactly as a line at the top of model_new.py would
    # be. The guard rebinds module attributes, which never reaches a bound name.
    from torch.nn.functional import avg_pool2d, conv2d, linear  # noqa: E402
    from torch.nn.functional import scaled_dot_product_attention as sdpa  # noqa: E402

    x, w, a, m = torch.randn(1, 1, 8, 8), torch.randn(1, 1, 3, 3), torch.randn(4, 8), torch.randn(8, 8)
    cases = [
        ("F.relu(x)", lambda: F.relu(a)),
        ("torch.relu(x)", lambda: torch.relu(a)),
        ("x.relu()", lambda: a.relu()),
        ("torch.matmul(x, w)", lambda: torch.matmul(a, m)),
        ("torch.conv2d(...)", lambda: torch.conv2d(x, w)),
        ("nn.Conv2d(1,1,3)(...)", lambda: nn.Conv2d(1, 1, 3)(x)),
        ("torch.ops.aten.relu(x)", lambda: torch.ops.aten.relu(a)),
        ("torch._C._nn.linear(x, w)", lambda: torch._C._nn.linear(a, m)),
        ("torch.softmax(x, -1)", lambda: torch.softmax(a, -1)),
        ("prebound conv2d", lambda: conv2d(x, w)),
        ("prebound linear", lambda: linear(a, m)),
        ("prebound sdpa", lambda: sdpa(a.unsqueeze(0), a.unsqueeze(0), a.unsqueeze(0))),
        ("prebound avg_pool2d", lambda: avg_pool2d(x, 2)),
    ]
    allowed = []
    with guard():
        for name, fn_ in cases:
            try:
                fn_()
                allowed.append(name)
                verdict = "ALLOWED"
            except RuntimeError as exc:
                verdict = ("BLOCKED" if "is not allowed in this context" in str(exc)
                           else f"ERROR {exc}")
            except Exception as exc:  # noqa: BLE001 - reporting, not handling
                verdict = f"ERROR {type(exc).__name__}"
            print(f"    {verdict:8s} {name}")
    print(f"  {len(allowed)} of {len(cases)} routes to a torch operator survive the guard")
    print(f"  the guard restores what it patched: F.relu is real again -> "
          f"{F.relu is torch.nn.functional.relu}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--kernelbench", type=Path, help="a KernelBench clone (leg 2)")
    ap.add_argument("--cuda-agent", type=Path, help="a CUDA-Agent clone (leg 4)")
    args = ap.parse_args()

    rows = load_dataset()
    digest = hashlib.sha256(CACHE.read_bytes()).hexdigest()
    print(f"  sha256 of the cached rows: {digest}")
    leg_duplicates(rows)
    leg_decontamination(rows, args.kernelbench)
    leg_labels(rows)
    leg_guard(args.cuda_agent)
    print("\nNothing here re-runs KernelBench or checks a speedup: no GPU is involved, "
          "and\nthe released workdir may not be the harness that produced the paper's table.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
