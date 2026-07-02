# Model Card — Fraud Detection Model

## Purpose and intended use
Binary fraud/not-fraud classification of IEEE-CIS style card transactions, for a regulated financial fraud-detection pipeline (Milestone 2 of the Secure & Compliant ML Security Pipeline project). Intended to score transactions and flag likely fraud for review, not for fully automated adverse action without human review.

## Model type
lightgbm
## Dataset version
`e457d0eb2c3b9e45`

## Training data
Module 2's time-aware, feature-engineered, feature-selected, preprocessed training split. Encrypted/PII columns (Module 1) are never used as features. TransactionID and fairness sensitive attributes (card6, card4, DeviceType) are preserved as non-feature metadata, never as model input.

## Performance (holdout test set)
- PR-AUC: 0.4869
- ROC-AUC: 0.8807
- F1: 0.4923 (at decision threshold 0.5976)
- Precision: 0.5987
- Recall: 0.4181

## Known limitations
- Trained on synthetic-PII-augmented IEEE-CIS data via Module 1's reproduction pipeline, not Yara's original encrypted artifact.
- Fairness analysis (Module 5) not yet performed as of this report.
- Differential privacy training (Module 4) not yet applied to this model version.
- Adversarial robustness (Module 6) not yet assessed.

## Azure ML registration
Not registered (no Azure ML credentials configured).