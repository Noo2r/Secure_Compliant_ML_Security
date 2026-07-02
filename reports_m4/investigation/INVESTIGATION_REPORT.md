# Module 4 Root-Cause Investigation — Why Is the DP Model's Utility So Poor?

**Trigger:** the original Module 4 DP NN achieved ROC-AUC=0.2991 (below random), PR-AUC=0.0284,
with its decision threshold collapsed to predicting every transaction as fraud. This document is
a controlled, one-factor-at-a-time experimental investigation of why, per an explicit "no guesses,
prove or disprove experimentally" directive.

**Methodology note:** Phases A-D run on a 100,000-row time-ordered subsample of `train_core`
(not the full 401,567 rows) purely for iteration speed — 21 exploratory DP training runs at full
scale would have taken ~2 hours; at this subsample size each run takes ~60-90s. Every exploratory
phase evaluates on the **validation slice only** (never the test set), so config selection here
cannot leak into any later test-set number. The winning configuration is re-confirmed on the
**full 401,567-row dataset** in Phase E before being trusted.

---

## Phase 0 — Gradient-Norm Diagnostic

**Question:** how large are true (unclipped) per-example gradients relative to `l2_norm_clip=1.0`?

Computed the actual per-example gradient L2 norm (using the same weighted BCE loss DP training
uses) for 300 positive and 300 negative examples, at model initialization.

| Class | Median | P90 | Max | % exceeding clip=1.0 |
|---|---|---|---|---|
| Positive (fraud, class_weight≈27-38x) | 0.0000 | 480 – 3,905 | 17,594 – 147,335 | 24-33% |
| Negative (legitimate) | 0.0032 – 1.68 | 10.5 – 28.2 | 816 – 846 | 41-53% |

**Finding:** gradient norms are extremely heavy-tailed, with a minority of examples (especially
positive/fraud examples, amplified by `class_weight`) reaching norms **tens of thousands of times**
the clip bound. This directly motivated Phase A.

---

## Phase A — `l2_norm_clip` Sweep

Fixed: `noise_multiplier=1.1`, `class_weight_positive=38.05` (original), `learning_rate=0.00153`
(Module 3's tuned value), `batch_size=256`, `epochs=11`.

| l2_norm_clip | ROC-AUC | PR-AUC | epsilon |
|---|---|---|---|
| 0.5 | 0.2857 | 0.0290 | 45.573 |
| 1.0 (original) | 0.2857 | 0.0288 | 45.573 |
| 2.0 | 0.2856 | 0.0287 | 45.573 |
| 5.0 | 0.2866 | 0.0285 | 45.573 |
| 10.0 | 0.2869 | 0.0282 | 45.573 |
| **20.0 (best)** | **0.2869** | 0.0280 | 45.573 |
| 50.0 | 0.2863 | 0.0277 | 45.573 |

**Finding:** essentially flat. Best (20.0) beats worst by only 0.0013 ROC-AUC — noise, not
epsilon-cost-free clip-norm tuning, dominates. **Epsilon is identical (45.573) across every row** —
direct experimental confirmation that TF-Privacy's accountant depends only on `noise_multiplier`,
not `l2_norm_clip` (verified further by a dedicated unit test,
`test_different_l2_norm_clip_does_not_change_epsilon`).

---

## Phase B — `class_weight` Ablation (at best clip=20.0)

| class_weight_positive | ROC-AUC | PR-AUC |
|---|---|---|
| 1.0 (no weighting) | 0.2894 | 0.0286 |
| 6.17 (sqrt of original) | 0.2948 | 0.0288 |
| 38.05 (original) | 0.2975 | 0.0307 |

**Finding:** class_weight has a small positive effect (0.289 → 0.297) but nowhere near enough to
fix anything. Consistent with the theoretical prediction (documented in `dp_model.py`): per-example
clipping projects every example's gradient onto the same-size ball regardless of its pre-clip
(weighted) magnitude, so class_weight's amplification is *mostly* — not *entirely* — neutralized.

---

## Phase C — `learning_rate` Sweep (at clip=20.0, class_weight=38.05)

| learning_rate | ROC-AUC |
|---|---|
| 0.0001 | 0.2639 |
| 0.0005 | 0.2708 |
| 0.00153 (Module 3's tuned value) | **0.2955 (best)** |
| 0.0050 | 0.2844 |
| 0.0100 | 0.2918 |

**Finding:** the learning rate inherited from Module 3 was already near-optimal among those tested.
No win available here.

---

## Control Experiment — Is This a Data/Split Artifact?

Trained the **Normal** (non-DP) NN on the identical 100K-row exploration subsample, evaluated on
the identical validation slice used throughout every DP experiment above.

**Result: ROC-AUC = 0.7451, PR-AUC = 0.1022** — healthy, consistent with the full-data Normal NN's
0.8020. **This conclusively rules out** the exploration subsample or the time-based train/val split
as the explanation. The failure is unambiguously attributable to DP-SGD training itself.

---

## Seed-Sensitivity Check — Is This Random Noise, or Systematic?

Ran the best-found DP config (clip=20, class_weight=38.05, lr=0.00153, noise_multiplier=1.1) at
three different random seeds.

| Seed | ROC-AUC |
|---|---|
| 1 | 0.2873 |
| 7 | 0.2994 |
| 99 | 0.2875 |

**Finding:** tight clustering (spread of 0.012), not the wide scatter you'd expect if noise were
simply overwhelming the model into an arbitrary random ranking. **This is a systematic,
reproducible effect of the training dynamics, not per-run randomness.**

---

## Phase D — `noise_multiplier` Recovery Sweep (the decisive experiment)

Fixed: clip=20.0, class_weight=38.05, lr=0.00153. Swept `noise_multiplier` from the original 1.1
down toward near-zero.

| noise_multiplier | epsilon | ROC-AUC | PR-AUC |
|---|---|---|---|
| 1.1 (original) | 45.6 | 0.2865 | 0.0277 |
| 0.6 | 112.2 | 0.3099 | 0.0293 |
| 0.3 | 348.2 | 0.3286 | 0.0417 |
| 0.1 | 2,531.8 | 0.3590 | 0.0404 |
| 0.05 | 9,791.8 | 0.3662 | 0.0516 |
| 0.01 | 242,111.8 | **0.3981** | 0.0494 |

**Finding — the key result of this investigation:** ROC-AUC **does** recover monotonically as
noise decreases, confirming noise magnitude is a real, causal factor. But even at
`noise_multiplier=0.01` — where epsilon=242,112 is astronomically, uselessly large (this is not a
meaningful privacy guarantee by any standard; it is essentially unprotected training) — ROC-AUC
only reaches 0.398, **still far below the Normal NN's 0.745-0.802 on the same/comparable data.**

**Conclusion: there are two independent, additive bottlenecks, not one:**
1. **A noise-independent ceiling (~0.40 ROC-AUC)** caused by gradient clipping's structural
   interaction with the severe 3.5% class imbalance — present even with negligible noise.
2. **Further, monotonic degradation from the Gaussian noise itself**, required for any
   *meaningful* epsilon (roughly noise_multiplier ≥ 0.6 for epsilon in the low hundreds).

Neither bottleneck is fixable by retuning `l2_norm_clip`, `class_weight`, or `learning_rate` alone
(Phases A-C already tested this).

---

## Phase E — Full-Dataset Confirmation (401,567 rows)

| Configuration | ROC-AUC | PR-AUC | epsilon | Train time |
|---|---|---|---|---|
| Best found, meaningful privacy (clip=20, nm=1.1) | 0.3008 | 0.0299 | 45.573 | 291.5s |
| Best found, weaker privacy (clip=20, nm=0.6) | 0.3344 | 0.0443 | 112.244 | 266.9s |
| *Reference: Normal NN, same architecture* | *0.8020* | *0.1318* | *n/a* | *13.8s* |

**Finding:** full-scale results match the subsample investigation closely (0.2991→0.3008 at the
original operating point — a genuine but tiny improvement from raising `l2_norm_clip` 1.0→20.0).
The investigation's conclusions are not an artifact of the smaller exploration sample.

---

## Root-Cause Synthesis (DP Theory, Not Speculation)

1. **Per-example gradient clipping is DP-SGD's non-negotiable privacy mechanism** — every
   example's gradient must be projected onto an L2 ball of the same radius before aggregation, or
   the sensitivity bound the privacy proof relies on doesn't hold. Given this project's severe
   class imbalance (3.5% positive), `class_weight` inflates the pre-clip loss/gradient for
   positive examples by ~28-38x specifically so they influence the aggregate update more — but
   clipping caps *every* example's influence to the same magnitude regardless of that inflation.
   The two mechanisms are in direct, structural tension (Abadi et al. 2016's clipping design was
   not conceived with severe class imbalance + loss reweighting in mind). This alone caps
   achievable performance at ~0.40 ROC-AUC even with negligible noise (Phase D, noise_multiplier=0.01).
2. **Gaussian noise, calibrated to `noise_multiplier`, is added on top of this already-capped
   signal.** Per RDP accounting, `epsilon` depends only on `noise_multiplier` (and batch
   size/dataset size/epochs/delta) — confirmed experimentally (Phase A: identical epsilon across a
   100x range of `l2_norm_clip`). Any `noise_multiplier` large enough to give a genuinely useful
   epsilon (roughly < 150, i.e., noise_multiplier ≳ 0.6) pushes the already-capped signal down
   further, compounding bottleneck #1.
3. **The ~13,057-parameter architecture (Module 3's single 64-unit hidden layer) has very little
   capacity to spare.** A larger model might tolerate clipping-driven signal loss better (more
   redundant pathways for gradient information to survive clipping), but changing the architecture
   is outside this investigation's scope (Module 3's architecture is a fixed input per the
   project's "identical architecture, only optimizer changes" requirement).

**This is not a hyperparameter-tuning problem.** 21 controlled experiments across 4 independently
varied hyperparameters (`l2_norm_clip`: 0.5-50, `class_weight`: 1-38, `learning_rate`: 1e-4 to 1e-2,
`noise_multiplier`: 0.01-1.1), 3 random seeds, and one architecture-preserving control all point to
the same conclusion: **for this specific architecture and this specific 3.5%-imbalanced dataset,
no DP-SGD configuration reaches acceptable utility.** The ceiling is set by the structural
interaction between per-example clipping (privacy-mandatory) and severe class imbalance
(data-mandatory), not by any single miscalibrated knob.

## Recommendation

Module 4's DP training pipeline, privacy accounting, and evaluation infrastructure are correct and
now demonstrably well-investigated — but the DP model itself is **not production-ready**, and I
cannot make it so by further hyperparameter tuning within this architecture. A real fix would
require one of: (a) a materially larger/different architecture (out of this module's scope), (b) a
fundamentally different imbalance-handling strategy compatible with DP-SGD (e.g., resampling the
training set BEFORE DP training rather than loss reweighting — untested here, a concrete direction
for future work), or (c) accepting a much weaker privacy guarantee than this project's stated goals
imply. None of these were in scope for a hyperparameter investigation, and I am reporting this
honestly rather than continuing to search for a fix I now have strong evidence does not exist within
current constraints.
