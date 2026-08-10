# References

Where the borrowed parts come from.

This file exists because of one label. The threshold table marks three values
`convention`, defined as "a value the surrounding literature uses, defensible by
citation" — and for a while nothing here cited anything. An appeal to
convention with no reference is an unfalsifiable claim, which is precisely what
this tool exists to object to. Every method the battery borrows and every
threshold that leans on prior art is named below, so a reader can disagree with
the source rather than with an assertion.

Ordinary caveat: a citation licenses a **method**, never a **setting**. Where a
number was chosen rather than derived, the threshold table says `judgment`, and
that is 34 of 43 of them. Nothing here converts a judgment call into a citation.

## Statistical methods the battery uses

| method | used by | source |
|---|---|---|
| Wilson score interval | every reported accuracy | Wilson, E. B. (1927). *Probable inference, the law of succession, and statistical inference.* JASA 22(158), 209–212. |
| KR-20 reliability | `fleet-reliability` (P1) | Kuder, G. F. & Richardson, M. W. (1937). *The theory of the estimation of test reliability.* Psychometrika 2(3), 151–160. |
| Point-biserial item discrimination | `item-discrimination` (P2) | Standard classical test theory; see Crocker, L. & Algina, J. (1986). *Introduction to Classical and Modern Test Theory*, ch. 14, for the rest-score correction used here. |
| Fixed-margins null by swap randomisation | `item-discrimination` (P2) | Connor, E. F. & Simberloff, D. (1979). *The assembly of species communities: chance or competition?* Ecology 60(6), 1132–1140. The 2×2 checkerboard swap is the standard sampler for a binary matrix with both margins held. |
| McNemar's test | `order-stability` (P9), `prompt-stability` (P11) | McNemar, Q. (1947). *Note on the sampling error of the difference between correlated proportions or percentages.* Psychometrika 12(2), 153–157. |
| Paired bootstrap resampling | `ordering-noise` (P6), typed superiority claims | Efron, B. (1979). *Bootstrap methods: another look at the jackknife.* Annals of Statistics 7(1), 1–26. |
| Mutation testing | `witness-coverage` (W1) | DeMillo, R. A., Lipton, R. J. & Sayward, F. G. (1978). *Hints on test data selection: help for the practicing programmer.* Computer 11(4), 34–41. The mutation gauntlet applies this to scorers: a witness suite that no mutant survives is a suite that constrains the scorer. |

### The three `convention` thresholds, and what they lean on

- **`kr20_min = 0.5`** — reliability coefficients are conventionally read against
  Nunnally's bands (Nunnally, J. C. (1978). *Psychometric Theory*, 2nd ed.), where
  0.7 is the usual bar for applied work and lower values are "acceptable for
  early research". 0.5 is deliberately below the textbook bar, because a 0.7 gate
  would skip almost every fleet anyone actually runs. That choice is judgment;
  the *scale* it is read against is the citation.
- **`negative_discrimination = -0.2`** — item analysis conventionally treats a
  negative point-biserial as a candidate key error, with practical screening
  bands around −0.2 to 0 (Crocker & Algina, above; Ebel, R. L. (1954). *Procedures
  for the analysis of classroom tests.* Educational and Psychological Measurement
  14(2), 352–364).
- **`shortcut_z = 3.0`** — three standard deviations against a null is the usual
  bar for calling a surface feature real rather than sampling noise. Convention,
  not derivation; the null it is measured against is analytic and described in
  METHODOLOGY.

## Benchmarks this repository audits

Fetched unmodified by `python benchmarks/fetch.py`, which prints the SHA-256 of
exactly what it downloaded. Nothing is vendored.

| dataset | source | licence |
|---|---|---|
| GSM8K | Cobbe, K. et al. (2021). *Training Verifiers to Solve Math Word Problems.* [arXiv:2110.14168](https://arxiv.org/abs/2110.14168) | MIT |
| MMLU | Hendrycks, D. et al. (2021). *Measuring Massive Multitask Language Understanding.* [arXiv:2009.03300](https://arxiv.org/abs/2009.03300) | MIT |
| TruthfulQA | Lin, S., Hilton, J. & Evans, O. (2022). *TruthfulQA: Measuring How Models Mimic Human Falsehoods.* [arXiv:2109.07958](https://arxiv.org/abs/2109.07958) | Apache-2.0 |
| HellaSwag | Zellers, R. et al. (2019). *HellaSwag: Can a Machine Really Finish Your Sentence?* [arXiv:1905.07830](https://arxiv.org/abs/1905.07830) | MIT |
| ARC (Easy and Challenge) | Clark, P. et al. (2018). *Think you have Solved Question Answering?* [arXiv:1803.05457](https://arxiv.org/abs/1803.05457) | CC-BY-SA-4.0 |
| MMLU-Pro | Wang, Y. et al. (2024). *MMLU-Pro: A More Robust and Challenging Multi-Task Language Understanding Benchmark.* [arXiv:2406.01574](https://arxiv.org/abs/2406.01574) | MIT |
| CommonsenseQA | Talmor, A. et al. (2019). *CommonsenseQA: A Question Answering Challenge Targeting Commonsense Knowledge.* [arXiv:1811.00937](https://arxiv.org/abs/1811.00937) | MIT |
| OpenBookQA | Mihaylov, T. et al. (2018). *Can a Suit of Armor Conduct Electricity?* [arXiv:1809.02789](https://arxiv.org/abs/1809.02789) | Apache-2.0 |
| BoolQ | Clark, C. et al. (2019). *BoolQ: Exploring the Surprising Difficulty of Natural Yes/No Questions.* [arXiv:1905.10044](https://arxiv.org/abs/1905.10044) | CC-BY-SA-3.0 |
| WinoGrande | Sakaguchi, K. et al. (2020). *WinoGrande: An Adversarial Winograd Schema Challenge at Scale.* [arXiv:1907.10641](https://arxiv.org/abs/1907.10641) | CC-BY |
| SciQ | Welbl, J., Liu, N. F. & Gardner, M. (2017). *Crowdsourcing Multiple Choice Science Questions.* [arXiv:1707.06209](https://arxiv.org/abs/1707.06209) | CC-BY-NC-3.0 |
| MedMCQA | Pal, A., Umapathi, L. K. & Sankarasubbu, M. (2022). *MedMCQA: A Large-scale Multi-Subject Multi-Choice Dataset for Medical domain Question Answering.* [arXiv:2203.14371](https://arxiv.org/abs/2203.14371) | MIT |
| ARC-Challenge, as a third-party eval LOG | `open-llm-leaderboard-old/details_Corianas__111m`, file `details_harness\|arc:challenge\|25_2023-07-19T13:48:53.093937.parquet`. A real lm-evaluation-harness details file, fetched by `benchmarks/lm-eval-import/fetch.py`. Harness: Gao, L. et al. (2021). *A framework for few-shot language model evaluation.* Zenodo. Items: Clark et al. 2018, above. | CC-BY-SA-4.0 (items) |
| RACE | Lai, G. et al. (2017). *RACE: Large-scale ReAding Comprehension Dataset From Examinations.* [arXiv:1704.04683](https://arxiv.org/abs/1704.04683) | research use, per the authors |
| MuSR | Sprague, Z. et al. (2024). *MuSR: Testing the Limits of Chain-of-thought with Multistep Soft Reasoning.* [arXiv:2310.16049](https://arxiv.org/abs/2310.16049) | MIT |
| LogiQA | Liu, J. et al. (2020). *LogiQA: A Challenge Dataset for Machine Reading Comprehension with Logical Reasoning.* [arXiv:2007.08124](https://arxiv.org/abs/2007.08124) (the `lucasmccabe/logiqa` copy) | CC-BY-NC-SA-4.0 |
| MATH-500 | Lightman, H. et al. (2023). *Let's Verify Step by Step.* [arXiv:2305.20050](https://arxiv.org/abs/2305.20050), a 500-problem subset of Hendrycks, D. et al. (2021), [arXiv:2103.03874](https://arxiv.org/abs/2103.03874) | MIT |
| DROP | Dua, D. et al. (2019). *DROP: A Reading Comprehension Benchmark Requiring Discrete Reasoning Over Paragraphs.* [arXiv:1903.00161](https://arxiv.org/abs/1903.00161) | CC-BY-SA-4.0 |
| MedQA (USMLE) | Jin, D. et al. (2021). *What Disease does this Patient Have? A Large-scale Open Domain Question Answering Dataset from Medical Exams.* [arXiv:2009.13081](https://arxiv.org/abs/2009.13081), via `GBaker/MedQA-USMLE-4-options` | MIT |
| AQuA-RAT | Ling, W. et al. (2017). *Program Induction by Rationale Generation.* [arXiv:1705.04146](https://arxiv.org/abs/1705.04146) | Apache-2.0 |
| Iranian driving licence test | `ckodser/Iran_Driving_licence_test`. A statutory road-safety question bank, redistributed; no accompanying paper. | see the dataset card |
| iris | Fisher, R. A. (1936). *The use of multiple measurements in taxonomic problems.* Annals of Eugenics 7(2), 179–188. The UCI/scikit-learn lineage this repo pins differs from Fisher's table in two rows: Bezdek, J. C. et al. (1999). *Will the real iris data please stand up?* IEEE Trans. Fuzzy Systems 7(3), 368–369. | public domain |

Findings against these datasets are in [FINDINGS.md](FINDINGS.md), series **F**.
Each one is a defect in a specific artifact and none is a judgement of the work
that produced it: these are the most-scrutinised benchmarks in the field, which
is exactly why finding anything in them is worth publishing.

## Failure modes the battery was built against

The trials are **not** enumerated from the check registry. They are drawn from
described eval-defect classes plus this project's own adversarial reviews, so
that a check and the defect proving it come from different places.

| failure mode | checks aimed at it | source |
|---|---|---|
| Answer leakage and train/test contamination | `answer-leak` (S2), `canary-present` (S8), `canary-regurgitated` (S10), `corpus-overlap` (S11) | Elangovan, A., He, J. & Verspoor, K. (2021). *Memorization vs. generalization: quantifying data leakage in NLP task design.* EACL. |
| Annotation artifacts a model can exploit without the task | `surface-shortcut` (S9), `blind-solvable` (R13), `input-blind` (R15) | Gururangan, S. et al. (2018). *Annotation artifacts in natural language inference data.* NAACL. |
| Shortcut learning generally ("Clever Hans") | the same family | Geirhos, R. et al. (2020). *Shortcut learning in deep neural networks.* Nature Machine Intelligence 2, 665–673. |
| Option-order sensitivity in multiple choice | `order-stability` (P9), `position-bias` (S3) | Pezeshkpour, P. & Hruschka, E. (2024). *Large Language Models Sensitivity to the Order of Options in Multiple-Choice Questions.* NAACL Findings. |
| Prompt-format sensitivity moving rankings | `prompt-stability` (P11), `ranking-stability` (P12) | Sclar, M. et al. (2024). *Quantifying Language Models' Sensitivity to Spurious Features in Prompt Design.* ICLR. |
| Benchmark label errors | `item-discrimination` (P2), `unanimous-wrong` (P5), `conflicting-keys` (S7) | Northcutt, C. G., Athalye, A. & Mueller, J. (2021). *Pervasive label errors in test sets destabilize machine learning benchmarks.* NeurIPS Datasets and Benchmarks. |
| LLM-judge bias: verbosity, position, self-preference | `judge-bias` (J2), `judge-self-preference` (J4) | Zheng, L. et al. (2023). *Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena.* NeurIPS. |
| Reproducibility and under-reported eval conditions | the coverage line, the drift boundary, `engine-drift` (R19) | Reproducibility checklists in the NeurIPS/ML community, and Kapoor, S. & Narayanan, A. (2023). *Leakage and the reproducibility crisis in machine-learning-based science.* Patterns 4(9). |

## What this repository does not borrow

Stated because absence is easy to misread as oversight:

- **No LLM-as-judge for the battery's own verdicts.** Every core check is
  deterministic or a stated statistic. A judge is something dinostomp *audits*
  (J1–J4), never something it *asks*.
- **No learned model anywhere in the checks.** Nothing here needs a GPU and
  nothing needs a network; `stomp` is offline by construction.
- **No claim about construct validity.** Every report carries
  `measures the intended construct: NOT ESTABLISHED BY DINOSTOMP`, and the
  reason is in METHODOLOGY: construct validity is argued, not computed. Messick,
  S. (1995). *Validity of psychological assessment.* American Psychologist 50(9),
  741–749, is the standard statement of what that argument requires, and it is
  not something a linter can supply.
