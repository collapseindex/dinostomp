# CUDA Agent audit

    paper      arXiv:2602.24286, "CUDA Agent: Large-Scale Agentic RL for
               High-Performance CUDA Kernel Generation" (ByteDance Seed / Tsinghua AIR)
    dataset    BytedTsinghua-SIA/CUDA-Agent-Ops-6K, 6,000 rows
    repo       BytedTsinghua-SIA/CUDA-Agent @ 473025c8
    reference  ScalingIntelligence/KernelBench @ 423217d9, levels 1-3 = 250 problems
    run        2026-08-16, 0 API calls, 0 GPU, $0.00

The first audit here whose subject is a **training corpus and an RL reward
instrument** rather than an eval and its scorer. The paper's headline is a speed
claim (100%, 100% and 92% faster rate over `torch.compile` on KernelBench levels
1-3). Nothing below checks a speedup: no released artifact contains one, and
there is no GPU in this audit. What the artifacts do contain is the apparatus
that produced the reward.

**What the repo is not.** `agent_workdir/` is a released example of the agent's
workspace, not a training or evaluation harness. It may not be the harness that
produced the paper's table, and the paper does not say it is. Every statement
about legs 4 below is a statement about the released file.

    python audits/cuda-agent/audit.py --kernelbench ../KernelBench --cuda-agent ../CUDA-Agent

## 1. 352 of the 6,000 training samples are exact duplicates

dinostomp `stomp` fails S1 on the released dataset, and the count survives being
checked without dinostomp's normalisation:

    dinostomp S1 [fail]: 352 duplicated question(s) among 6000
    byte-identical repeats of an earlier row : 352
    same count after lowercase+whitespace    : 352
    distinct code values                     : 5648 of 6000
    largest cluster                          : x2
    dup clusters with conflicting ops labels : 0

Raw-byte and normalised counts agree exactly, so no part of this is an artifact
of lowercasing. Every cluster is exactly ×2 and none carries conflicting labels.

The pipeline that built this set already computes pairwise AST similarity
(Appendix A), and it was pointed only outward, at the evaluation set. A
byte-identical pair inside the training set scores 1.0 on the same tool. Effect
is a sampling weight, not a wrong answer: 5.9% of the corpus is drawn at double
rate during RL.

## 2. The decontamination claim holds at the text level, and the check was controlled

Appendix A: training samples are dropped when maximum AST similarity to any
evaluation program exceeds **0.9**, computed with `PythonASTSimilarity`.

Character-shingle overlap of all 6,000 against all 250, which is a different
instrument than theirs and agrees with it:

    hits: 0 exact / 0 same-question / 0 near-verbatim / 0 suppressed as template siblings

A zero from a check that cannot fire is worth nothing, so three known
contaminants are planted and the check has to find them:

| planted | result |
|---|---|
| a KernelBench problem copied verbatim | FLAGGED, exact, 1.0 |
| the same problem, class renamed and a comment added | FLAGGED, near, 0.921 |
| the same problem, only its tensor dimensions changed | **NOT FLAGGED** |

The third is the caveat that belongs beside the pass. dinostomp exempts pairs
differing only in their numbers (`is_template_sibling`), so a training sample
that is a KernelBench problem at other sizes is invisible here by construction,
at jaccard **0.993**. Zero real rows landed in that exempt category, so the pass
survives its own caveat, but it is a pass about verbatim and cosmetic reuse.

### What neither instrument counts

Their filter is stated in terms of operators ("we exclude operators that exhibit
high similarity to KernelBench test cases") and computed over AST structure. For
kernel generation the thing that transfers from training to test is the kernel
you learned to write for operator X, which survives a total rewrite of the module
around it. Comparing operator signatures instead of source text:

    level1: 53 distinct signatures among 100 problems -> 126 of 6000 rows match one exactly
    level2: 93 distinct signatures among 100 problems ->  41 rows
    level3: 37 distinct signatures among  50 problems ->   7 rows

    ['ConvTranspose2d']         x33 == level1/81_conv_transposed_2D_..._dilated____padded____strided__.py
    ['InstanceNorm2d']          x10 == level1/34_InstanceNorm.py
    ['ConvTranspose2d','clamp'] x14 == level2/2_ConvTranspose2d_BiasAdd_Clamp_Scaling_Clamp_Divide.py

Whether that counts as contamination is theirs to argue, and there is a real
argument that a different shape is a different kernel problem. The point is that
their stated filter cannot participate in the argument: at a 0.9 AST threshold it
was never going to fire on any of these, and their own Figure 7 shows the whole
distribution topping out near 0.6 with the threshold at 0.9, a filter set where
nothing lives.

Also reproduced: the paper's **Table 3 re-derives exactly** from the released
file. All six proportions (3.40 / 83.77 / 7.62 / 2.80 / 1.23 / 1.18 %) match the
`data_source` counts (204 / 5026 / 457 / 168 / 74 / 71) to the row.

## 3. 9.3% of rows declare an operator their own code never uses

`ops` is the provenance label: which torch operators the sample was synthesised
from. For **550 of 5,929** torch-sourced rows, the code does not contain an
operator the label declares.

The extractor is biased against this finding on purpose. It counts every
attribute name in the file as a possible use, so the Tensor-method spelling
`x.tril()` counts, and it drops operators with a syntax form (`add` is written
`+`) rather than calling them absent; 66 further rows differ only on those and
are excluded.

    most frequently declared-but-absent:
    ConvTranspose1d 111, ConvTranspose3d 103, bmm 35, tril 31, diag 30,
    MaxPool1d 24, triu 23, einsum 22

The pattern is dimensionality substitution. `ops6k-0048` declares five operators
and three are wrong:

    ops : ["torch.einsum", "nn.AdaptiveAvgPool3d", "nn.LeakyReLU",
           "nn.Conv3d", "nn.ConvTranspose1d"]
    code: nn.AdaptiveAvgPool2d(...)  nn.Conv3d(...)  nn.LeakyReLU()
          nn.ConvTranspose3d(...)    torch.clamp(...)

`AdaptiveAvgPool3d` → `2d`, `ConvTranspose1d` → `3d`, `einsum` never appears, and
`clamp` appears without being declared. `ops6k-0000` declares `torch.diag` while
its code imports `digamma`.

This does not touch the headline. It means the released dataset's coverage story
is told by a column that disagrees with its own code about one row in eleven,
and anything computed over `ops` inherits that.

## 4. The anti-reward-hacking guard blocks one spelling of the thing it blocks

`utils/verification.py` runs the candidate inside `block_torch_functional()`,
which replaces every public callable in `dir(torch.nn.functional)` with a
raiser. This is the paper's "system-level permission isolation ... to prevent
reward hacking" (§1).

It is an attribute patch on one module object. **11 of 13** routes to a torch
operator survive it:

    BLOCKED  F.relu(x)                    ALLOWED  torch.relu(x)
    BLOCKED  nn.Conv2d(1,1,3)(...)        ALLOWED  x.relu()
                                          ALLOWED  torch.matmul(x, w)
                                          ALLOWED  torch.conv2d(...)
                                          ALLOWED  torch.ops.aten.relu(x)
                                          ALLOWED  torch._C._nn.linear(x, w)
                                          ALLOWED  torch.softmax(x, -1)
                                          ALLOWED  prebound conv2d
                                          ALLOWED  prebound linear
                                          ALLOWED  prebound sdpa
                                          ALLOWED  prebound avg_pool2d

The cheapest bypass costs one import line, because binding the name before the
guard runs means the guard's rebinding never reaches it:

```python
from torch.nn.functional import conv2d      # at the top of model_new.py
...
conv2d(x, w)                                # inside the guard: ALLOWED
```

`conv2d`, `linear`, `scaled_dot_product_attention` and `avg_pool2d` all pass this
way, and those are the expensive operators an agent is being paid to
reimplement.

A correction to this audit's own first reading: prebound `relu` and `max_pool2d`
*do* raise, but not because the guard caught them. Their Python bodies call
`has_torch_function_unary`, itself a public callable in `dir(F)` and therefore
also patched. The guard holds there by collateral damage on a helper, which
lasts exactly as long as torch keeps routing those bodies through a patched
name.

**What this does not show.** That the trained model exploited any of it. No
released artifact records rollout behaviour, and a wholesale fallback to torch's
own `conv2d` would pass verification while earning little on speed. The
realistic shape is partial: implement three operators of a fused task as real
kernels and let the fourth fall through. Verification would not notice.

## 5. Read-only: the performance instrument reports a point estimate

`utils/profiling.py` produces the reward the training loop optimises.

* **5 warmup iterations and 10 timed** (`--iters`, default 10). One mean. No
  median, no variance, no repeats, no seed.
* **The candidate is timed first**, then eager, then `torch.compile` (L112-116).
  GPU clocks drift under sustained load, so a fixed order puts the candidate on
  the coolest clock. Interleaving is free.
* `torch.compile` gets the same 5 warmup iterations as everything else, and it
  is both the baseline most sensitive to warmup and the one the headline is
  stated against.
* The metric is summed CUDA `device_time` over profiler events: kernel time, not
  end-to-end latency. Defensible, and a choice, and launch-overhead differences
  sit outside it.
* Correctness tolerance is `atol=rtol=1e-2` (`verification.py:35`), loose for
  fp32, over 5 draws of `randn` inputs with no seed.

Nothing in this section was measured. There is no GPU in this audit and these
are observations about a file.

## Limits

1. No GPU. Nothing here re-runs KernelBench or checks one speedup number.
2. `agent_workdir` is a released example, not necessarily the paper's harness.
3. Overlap is evidence about the two corpora compared. Finding none is not
   evidence about a training corpus, and dinostomp says so in its own output.
4. Legs 3, 4 and 5 are analysis, not dinostomp checks. Only legs 1 and 2 have a
   negative-tested check behind them.
