# Module 3 — Model Development Report

- Dataset version: `e457d0eb2c3b9e45`
- Candidate models compared: ['logistic_regression', 'random_forest', 'xgboost', 'lightgbm', 'neural_network']

## Leaderboard (ranked by holdout PR-AUC)

| model_name          |   cv_pr_auc_mean |   cv_pr_auc_std |   holdout_pr_auc |   holdout_roc_auc |   holdout_f1 |   holdout_precision |   holdout_recall |   holdout_accuracy |   decision_threshold |   recall_at_precision_target |   train_seconds |   n_optuna_trials | best_params                                                                                                                                                                       |
|:--------------------|-----------------:|----------------:|-----------------:|------------------:|-------------:|--------------------:|-----------------:|-------------------:|---------------------:|-----------------------------:|----------------:|------------------:|:----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| lightgbm            |         0.515343 |       0.0151493 |        0.486892  |          0.880695 |     0.492321 |           0.598661  |         0.418061 |           0.970332 |             0.597595 |                     0.151821 |         389.735 |                25 | {'n_estimators': 450, 'num_leaves': 249, 'learning_rate': 0.059438044001557604, 'subsample': 0.9332156289655296, 'colsample_bytree': 0.8294757870022367, 'min_child_samples': 61} |
| xgboost             |         0.495353 |       0.018182  |        0.46044   |          0.85958  |     0.471305 |           0.617964  |         0.380906 |           0.970595 |             0.692903 |                     0.146161 |         206.847 |                25 | {'n_estimators': 450, 'max_depth': 8, 'learning_rate': 0.11953449625158145, 'subsample': 0.7646532535171965, 'colsample_bytree': 0.895083043886893, 'min_child_weight': 1}        |
| random_forest       |         0.428278 |       0.0187875 |        0.436568  |          0.875058 |     0.434578 |           0.49621   |         0.386565 |           0.965388 |             0.685172 |                     0.104577 |         340.634 |                20 | {'n_estimators': 250, 'max_depth': 14, 'min_samples_leaf': 17, 'max_features': 'sqrt'}                                                                                            |
| logistic_regression |         0.15387  |       0.0242762 |        0.108035  |          0.751436 |     0.169844 |           0.173234  |         0.166585 |           0.943967 |             0.763183 |                     0.165108 |         156.604 |                20 | {'C': 1.362756381873745}                                                                                                                                                          |
| neural_network      |         0.114842 |       0.0261554 |        0.0934351 |          0.788279 |     0.162582 |           0.0914074 |         0.734498 |           0.739645 |             0.642428 |                     0.328248 |         734.601 |                 9 | {'n_layers': 1, 'units': 64, 'dropout': 0.2571172192068058, 'learning_rate': 0.0015304852121831463, 'batch_size': 256, 'epochs': 11}                                              |

## Best model selection
**lightgbm** (leaderboard rank 1)

'lightgbm' has the highest holdout PR-AUC (0.4869), with no other model within 1.0% relative tolerance.

## Statistical comparison (top 2 models, paired Wilcoxon over CV folds)

```
{'comparable': True, 'model_a': 'lightgbm', 'model_b': 'xgboost', 'cv_scores_a': [0.4952926353849666, 0.5188317897023251, 0.5319055507540911], 'cv_scores_b': [0.46981216157308336, 0.5106995114268627, 0.5055462677776508], 'wilcoxon_statistic': 0.0, 'p_value': 0.25, 'significant_at_0.05': False}
```

## Per-model operational metrics

| Model | Recall @ Precision target | Precision@K (first configured K) |
|---|---|---|
| logistic_regression | recall=0.1651 at precision=0.1750 (target 0.90, met=False) | k=100, precision=0.0000 |
| random_forest | recall=0.1046 at precision=0.9004 (target 0.90, met=True) | k=100, precision=1.0000 |
| xgboost | recall=0.1462 at precision=0.9000 (target 0.90, met=True) | k=100, precision=1.0000 |
| lightgbm | recall=0.1518 at precision=0.9007 (target 0.90, met=True) | k=100, precision=0.9700 |
| neural_network | recall=0.3282 at precision=0.1106 (target 0.90, met=False) | k=100, precision=0.1000 |