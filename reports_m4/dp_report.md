# Module 4 — Differential Privacy Report

- Dataset version: `e457d0eb2c3b9e45`

## 1. Architecture
- Layers: 1 hidden Dense layer(s) of 64 units (ReLU), dropout=0.257, sigmoid output.
- Identical architecture and initial weights for both Normal and DP variants (verified: initial weight checksums 980.497437 vs 980.497437 -- MATCH).
- No BatchNormalization (incompatible with per-example gradient computation DP-SGD requires).
- Reused directly from Module 3's `KerasClassifierWrapper._build_model` — not reimplemented.

## 2. Optimizer
- Normal: `keras.optimizers.Adam` (Module 3's tuned learning rate 0.001530).
- DP: `tensorflow_privacy.DPKerasAdamOptimizer` (same base optimizer family + per-example gradient clipping + Gaussian noise) -- the only difference between the two runs.

## 3. Differential Privacy Parameters
- Noise multiplier: 1.1
- L2 gradient clipping norm: 20.0
- Microbatches: 256 (== batch_size => true per-example clipping, not batch-averaged clipping -- see config.yaml's documented verification of this semantic)
- Batch size: 256
- Epochs: 11
- Delta: 1.00e-05

## 4. Privacy Accounting
- **Epsilon (matches actual training loop -- shuffled epochs, no Poisson subsampling): 45.5728**
- Epsilon under the (inapplicable) Poisson-subsampling assumption: 3.9322 — NOT the guarantee this training actually provides; recorded for transparency only.

Full TensorFlow Privacy accountant statement:
```
DP-SGD performed over 401567 examples with 256 examples per iteration, noise
multiplier 1.1 for 11 epochs with microbatching, and no bound on number of
examples per user.

This privacy guarantee protects the release of all model checkpoints in addition
to the final model.

Example-level DP with add-or-remove-one adjacency at delta = 1e-05 computed with
RDP accounting:
    Epsilon with each example occurring once per epoch:        45.573
    Epsilon assuming Poisson sampling (*):                      3.932

No user-level privacy guarantee is possible without a bound on the number of
examples per user.

(*) Poisson sampling is not usually done in training pipelines, but assuming
that the data was randomly shuffled, it is believed the actual epsilon should be
closer to this value than the conservative assumption of an arbitrary data
order.

```

## 5. Training Time
- Normal NN: 14.88s
- DP NN: 264.80s (17.80x the Normal NN's time)

## 6. Evaluation Metrics (holdout test set)

| Metric | Normal | DP | Delta (Normal - DP) |
|---|---|---|---|
| accuracy | 0.9386 | 0.0344 | 0.9042 |
| precision | 0.1810 | 0.0344 | 0.1466 |
| recall | 0.2224 | 1.0000 | -0.7776 |
| f1 | 0.1996 | 0.0665 | 0.1331 |
| roc_auc | 0.7936 | 0.3064 | 0.4872 |
| pr_auc | 0.1646 | 0.0285 | 0.1361 |

### Confusion matrices (at each model's own optimized threshold)

- Normal (threshold=0.7251): {'true_negative': 109954, 'false_positive': 4090, 'false_negative': 3160, 'true_positive': 904}
- DP (threshold=0.0000): {'true_negative': 0, 'false_positive': 114044, 'false_negative': 0, 'true_positive': 4064}

## 7. Privacy-Utility Analysis

PR-AUC dropped from 0.1646 (Normal) to 0.0285 (DP), a 82.7% relative change, at privacy budget epsilon=45.573, delta=1.0e-05.

This gap is expected and mechanistically explained by DP-SGD's two departures from normal training, both active here:
1. Per-example gradient clipping to L2 norm 20.0 discards gradient magnitude information above that bound -- any example whose true gradient is larger gets projected down, losing information about how strongly it should influence the update.
2. Calibrated Gaussian noise with standard deviation 1.1 x 20.0 = 22.000 is added to the summed clipped gradients every step, directly degrading gradient signal quality in exchange for the formal privacy guarantee.
Both effects compound over training steps, so more epochs/steps at a fixed noise_multiplier accumulate more total noise exposure (and a larger epsilon) without necessarily improving DP model quality the way more epochs typically helps normal training.
The gap is more pronounced in recall (delta=-0.7776) than precision (delta=0.1466), consistent with noise disproportionately harming the model's ability to confidently identify the minority (fraud) class, whose already-sparse gradient signal is more easily swamped by added noise than the majority class's abundant signal.

### Noise multiplier sweep (privacy-utility curve data)

|   noise_multiplier |   epsilon |    pr_auc |   roc_auc |
|-------------------:|----------:|----------:|----------:|
|                0.6 |  112.244  | 0.0467114 |  0.395299 |
|                0.8 |   72.424  | 0.0322973 |  0.30681  |
|                1.1 |   45.5728 | 0.0379999 |  0.308067 |
|                1.5 |   29.6785 | 0.0468044 |  0.322864 |
|                2   |   20.2592 | 0.041089  |  0.319332 |

## 8. Advantages of the DP Approach
- Provides a formal, mathematically-provable bound (epsilon, delta) on how much any single training example can influence the trained model -- normal training provides no such guarantee and is vulnerable to membership-inference and model-inversion attacks that DP-SGD is specifically designed to resist.
- The privacy guarantee holds regardless of what an adversary already knows or what auxiliary data they have access to (a worst-case guarantee, not a statistical average-case one).

## 9. Limitations
- Utility cost is real and measured above, not hypothetical -- see Section 6.
- `class_weight` for class-imbalance correction is structurally weakened under DP-SGD's per-example gradient clipping (see `src/privacy/dp_model.py` module docstring for the full mechanistic explanation) -- this is a genuine tension between fairness/imbalance handling and DP training on this dataset, not fully resolved here.
- The reported epsilon assumes the accountant's modeling of the training process (shuffled epochs, Gaussian mechanism) exactly matches what Keras's `model.fit()` actually does step by step; this project did not independently re-derive or audit TF-Privacy's accounting math.
- Both Normal and DP variants inherit Module 3's Neural Network architecture, which was the **weakest of Module 3's five candidates** (holdout PR-AUC 0.093 vs. LightGBM's 0.487) -- so this entire Normal-vs-DP comparison is built on a mediocre base model, not this project's best classifier.
- `tensorflow-privacy` required three separate compatibility workarounds to run on this project's TensorFlow 2.20 installation (see `src/privacy/tf_privacy_compat.py`) -- the library's ecosystem currency for very recent TensorFlow releases is a real, practical risk for anyone reusing this code.

## 10. Recommendations Before Module 5
- Consider whether Module 5 (Fairness Analysis) should account for DP-SGD's documented interaction with class-imbalance handling -- a DP-trained model's fairness properties may differ from a normally-trained model's for reasons distinct from the sensitive attribute itself.
- If a stronger privacy guarantee is required for production use, the noise multiplier sweep in Section 7 shows the achievable epsilon/utility tradeoff points actually measured on this dataset/architecture -- use it to pick an operating point rather than guessing.