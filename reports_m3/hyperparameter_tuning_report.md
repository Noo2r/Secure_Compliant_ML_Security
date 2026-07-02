# Module 3 — Hyperparameter Tuning Report

## logistic_regression
- Trials completed: 20
- Tuning wall-clock: 135.6s
- Best CV PR-AUC: 0.1539 (fold scores: [0.124, 0.1542, 0.1834])
- Best hyperparameters: `{'C': 1.362756381873745}`

## random_forest
- Trials completed: 20
- Tuning wall-clock: 292.7s
- Best CV PR-AUC: 0.4283 (fold scores: [0.4018, 0.4433, 0.4398])
- Best hyperparameters: `{'n_estimators': 250, 'max_depth': 14, 'min_samples_leaf': 17, 'max_features': 'sqrt'}`

## xgboost
- Trials completed: 25
- Tuning wall-clock: 191.9s
- Best CV PR-AUC: 0.4954 (fold scores: [0.4698, 0.5107, 0.5055])
- Best hyperparameters: `{'n_estimators': 450, 'max_depth': 8, 'learning_rate': 0.11953449625158145, 'subsample': 0.7646532535171965, 'colsample_bytree': 0.895083043886893, 'min_child_weight': 1}`

## lightgbm
- Trials completed: 25
- Tuning wall-clock: 372.0s
- Best CV PR-AUC: 0.5153 (fold scores: [0.4953, 0.5188, 0.5319])
- Best hyperparameters: `{'n_estimators': 450, 'num_leaves': 249, 'learning_rate': 0.059438044001557604, 'subsample': 0.9332156289655296, 'colsample_bytree': 0.8294757870022367, 'min_child_samples': 61}`

## neural_network
- Trials completed: 9
- Tuning wall-clock: 703.4s
- Best CV PR-AUC: 0.1148 (fold scores: [0.0804, 0.1437, 0.1205])
- Best hyperparameters: `{'n_layers': 1, 'units': 64, 'dropout': 0.2571172192068058, 'learning_rate': 0.0015304852121831463, 'batch_size': 256, 'epochs': 11}`
