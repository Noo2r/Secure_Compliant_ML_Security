# Module 2 — Feature Engineering & Selection Report

## 1. Upstream dataset (Module 1)
- Dataset version: `e457d0eb2c3b9e45` (mode: load_existing)
- Rows: 590,540
- Encrypted/PII columns excluded before engineering: ['CustomerName', 'Email', 'PhoneNumber', 'Address', 'NationalID', 'CreditCardNumber']

## 2. Pre-engineering profile (see eda_profile_report.md for full detail)
- ML-ready columns analyzed: 422
- Numeric: 384, Categorical: 29, ID-like: 6
- Columns with >5% missing: 310
- Redundant (|corr|>0.95) column pairs found: 572

## 3. Engineered features

| Feature | Justification |
|---|---|
| transaction_hour | Fraud rate ~3x higher at 07:00-09:00 (reference clock) than daily baseline (EDA). |
| transaction_day_of_week | Captures weekly seasonality in transaction/fraud volume. |
| TransactionAmt_log | Corrects heavy right-skew (median 68 vs max ~31,937) for linear/NN model stability. |
| TransactionAmt_decimal | Standard fraud-analytics feature; modest empirical association only (51.7% vs 52.9% zero-cents by class) -- retained as a candidate, final inclusion decided by feature selection. |
| email_domain_match | Fraud rate 9.65% (domains match) vs 2.21% (domains differ) -- one of the strongest engineered signals found (EDA). |
| P_emaildomain_grouped | Per-domain fraud rate ranges 0.7%-9.4%; grouping to top domains preserves signal while capping cardinality. |
| R_emaildomain_grouped | Same rationale as P_emaildomain_grouped, recipient side. |
| card1_txn_count | Classic velocity feature; EDA showed only weak/non-monotonic signal alone -- retained as a selection candidate. |
| card1_amt_mean | Per-card historical spending baseline for deviation scoring. |
| card1_amt_std | Per-card spending variability for deviation scoring. |
| card1_amt_zscore | How unusual this transaction's amount is relative to this card's own history. |
| P_emaildomain_was_missing | Missingness itself is predictive (e.g. DeviceType missing correlates with ~4x lower fraud rate); flags one indicator per unique missingness pattern to avoid ~100+ near-duplicate columns. |
| R_emaildomain_was_missing | Missingness itself is predictive (e.g. DeviceType missing correlates with ~4x lower fraud rate); flags one indicator per unique missingness pattern to avoid ~100+ near-duplicate columns. |
| D2_was_missing | Missingness itself is predictive (e.g. DeviceType missing correlates with ~4x lower fraud rate); flags one indicator per unique missingness pattern to avoid ~100+ near-duplicate columns. |
| D3_was_missing | Missingness itself is predictive (e.g. DeviceType missing correlates with ~4x lower fraud rate); flags one indicator per unique missingness pattern to avoid ~100+ near-duplicate columns. |
| D4_was_missing | Missingness itself is predictive (e.g. DeviceType missing correlates with ~4x lower fraud rate); flags one indicator per unique missingness pattern to avoid ~100+ near-duplicate columns. |
| D5_was_missing | Missingness itself is predictive (e.g. DeviceType missing correlates with ~4x lower fraud rate); flags one indicator per unique missingness pattern to avoid ~100+ near-duplicate columns. |
| D6_was_missing | Missingness itself is predictive (e.g. DeviceType missing correlates with ~4x lower fraud rate); flags one indicator per unique missingness pattern to avoid ~100+ near-duplicate columns. |
| D8_was_missing | Missingness itself is predictive (e.g. DeviceType missing correlates with ~4x lower fraud rate); flags one indicator per unique missingness pattern to avoid ~100+ near-duplicate columns. |
| D10_was_missing | Missingness itself is predictive (e.g. DeviceType missing correlates with ~4x lower fraud rate); flags one indicator per unique missingness pattern to avoid ~100+ near-duplicate columns. |
| D11_was_missing | Missingness itself is predictive (e.g. DeviceType missing correlates with ~4x lower fraud rate); flags one indicator per unique missingness pattern to avoid ~100+ near-duplicate columns. |
| D12_was_missing | Missingness itself is predictive (e.g. DeviceType missing correlates with ~4x lower fraud rate); flags one indicator per unique missingness pattern to avoid ~100+ near-duplicate columns. |
| D13_was_missing | Missingness itself is predictive (e.g. DeviceType missing correlates with ~4x lower fraud rate); flags one indicator per unique missingness pattern to avoid ~100+ near-duplicate columns. |
| D14_was_missing | Missingness itself is predictive (e.g. DeviceType missing correlates with ~4x lower fraud rate); flags one indicator per unique missingness pattern to avoid ~100+ near-duplicate columns. |
| D15_was_missing | Missingness itself is predictive (e.g. DeviceType missing correlates with ~4x lower fraud rate); flags one indicator per unique missingness pattern to avoid ~100+ near-duplicate columns. |
| V12_was_missing | Missingness itself is predictive (e.g. DeviceType missing correlates with ~4x lower fraud rate); flags one indicator per unique missingness pattern to avoid ~100+ near-duplicate columns. |
| V35_was_missing | Missingness itself is predictive (e.g. DeviceType missing correlates with ~4x lower fraud rate); flags one indicator per unique missingness pattern to avoid ~100+ near-duplicate columns. |
| V53_was_missing | Missingness itself is predictive (e.g. DeviceType missing correlates with ~4x lower fraud rate); flags one indicator per unique missingness pattern to avoid ~100+ near-duplicate columns. |
| V75_was_missing | Missingness itself is predictive (e.g. DeviceType missing correlates with ~4x lower fraud rate); flags one indicator per unique missingness pattern to avoid ~100+ near-duplicate columns. |
| V138_was_missing | Missingness itself is predictive (e.g. DeviceType missing correlates with ~4x lower fraud rate); flags one indicator per unique missingness pattern to avoid ~100+ near-duplicate columns. |
| V167_was_missing | Missingness itself is predictive (e.g. DeviceType missing correlates with ~4x lower fraud rate); flags one indicator per unique missingness pattern to avoid ~100+ near-duplicate columns. |
| V169_was_missing | Missingness itself is predictive (e.g. DeviceType missing correlates with ~4x lower fraud rate); flags one indicator per unique missingness pattern to avoid ~100+ near-duplicate columns. |
| V217_was_missing | Missingness itself is predictive (e.g. DeviceType missing correlates with ~4x lower fraud rate); flags one indicator per unique missingness pattern to avoid ~100+ near-duplicate columns. |
| V220_was_missing | Missingness itself is predictive (e.g. DeviceType missing correlates with ~4x lower fraud rate); flags one indicator per unique missingness pattern to avoid ~100+ near-duplicate columns. |
| V322_was_missing | Missingness itself is predictive (e.g. DeviceType missing correlates with ~4x lower fraud rate); flags one indicator per unique missingness pattern to avoid ~100+ near-duplicate columns. |
| id_01_was_missing | Missingness itself is predictive (e.g. DeviceType missing correlates with ~4x lower fraud rate); flags one indicator per unique missingness pattern to avoid ~100+ near-duplicate columns. |
| id_02_was_missing | Missingness itself is predictive (e.g. DeviceType missing correlates with ~4x lower fraud rate); flags one indicator per unique missingness pattern to avoid ~100+ near-duplicate columns. |
| id_03_was_missing | Missingness itself is predictive (e.g. DeviceType missing correlates with ~4x lower fraud rate); flags one indicator per unique missingness pattern to avoid ~100+ near-duplicate columns. |
| id_05_was_missing | Missingness itself is predictive (e.g. DeviceType missing correlates with ~4x lower fraud rate); flags one indicator per unique missingness pattern to avoid ~100+ near-duplicate columns. |
| id_11_was_missing | Missingness itself is predictive (e.g. DeviceType missing correlates with ~4x lower fraud rate); flags one indicator per unique missingness pattern to avoid ~100+ near-duplicate columns. |
| id_13_was_missing | Missingness itself is predictive (e.g. DeviceType missing correlates with ~4x lower fraud rate); flags one indicator per unique missingness pattern to avoid ~100+ near-duplicate columns. |
| id_14_was_missing | Missingness itself is predictive (e.g. DeviceType missing correlates with ~4x lower fraud rate); flags one indicator per unique missingness pattern to avoid ~100+ near-duplicate columns. |
| id_16_was_missing | Missingness itself is predictive (e.g. DeviceType missing correlates with ~4x lower fraud rate); flags one indicator per unique missingness pattern to avoid ~100+ near-duplicate columns. |
| id_17_was_missing | Missingness itself is predictive (e.g. DeviceType missing correlates with ~4x lower fraud rate); flags one indicator per unique missingness pattern to avoid ~100+ near-duplicate columns. |
| id_19_was_missing | Missingness itself is predictive (e.g. DeviceType missing correlates with ~4x lower fraud rate); flags one indicator per unique missingness pattern to avoid ~100+ near-duplicate columns. |
| id_20_was_missing | Missingness itself is predictive (e.g. DeviceType missing correlates with ~4x lower fraud rate); flags one indicator per unique missingness pattern to avoid ~100+ near-duplicate columns. |
| id_32_was_missing | Missingness itself is predictive (e.g. DeviceType missing correlates with ~4x lower fraud rate); flags one indicator per unique missingness pattern to avoid ~100+ near-duplicate columns. |
| id_34_was_missing | Missingness itself is predictive (e.g. DeviceType missing correlates with ~4x lower fraud rate); flags one indicator per unique missingness pattern to avoid ~100+ near-duplicate columns. |
| DeviceType_was_missing | Missingness itself is predictive (e.g. DeviceType missing correlates with ~4x lower fraud rate); flags one indicator per unique missingness pattern to avoid ~100+ near-duplicate columns. |

## 4. Feature selection method comparison

Consensus of mutual information + embedded Random Forest importance over 343 candidates surviving near-zero-variance (14 dropped) and correlation-redundancy (109 dropped) filters. Top 150 by averaged normalized rank retained. RFE excluded as computationally infeasible at this dimensionality and redundant with the embedded method already used.

- Candidates considered: 466
- Dropped (near-zero variance): 14
- Dropped (correlation redundancy): 109
- Final selected features: 150

### Removed features (with reason)

| Feature | Reason |
|---|---|
| C1 | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| C10 | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| C11 | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| C12 | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| C14 | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| C4 | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| C6 | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| C7 | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| C8 | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| D1 | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| D12 | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| D12_was_missing | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| D6 | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| DeviceType_was_missing | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| M1 | Near-zero variance (>99.9% single value) |
| R_emaildomain_was_missing | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| V1 | Near-zero variance (>99.9% single value) |
| V100 | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| V107 | Near-zero variance (>99.9% single value) |
| V11 | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| V12_was_missing | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| V135 | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| V137 | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| V138_was_missing | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| V14 | Near-zero variance (>99.9% single value) |
| V144 | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| V145 | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| V148 | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| V149 | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| V15 | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| V151 | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| V153 | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| V159 | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| V16 | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| V163 | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| V165 | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| V167_was_missing | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| V169_was_missing | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| V17 | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| V180 | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| V190 | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| V192 | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| V196 | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| V203 | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| V206 | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| V214 | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| V215 | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| V216 | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| V22 | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| V220_was_missing | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| V221 | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| V224 | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| V229 | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| V240 | Near-zero variance (>99.9% single value) |
| V241 | Near-zero variance (>99.9% single value) |
| V242 | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| V248 | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| V250 | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| V253 | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| V255 | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| V266 | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| V269 | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| V27 | Near-zero variance (>99.9% single value) |
| V272 | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| V276 | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| V28 | Near-zero variance (>99.9% single value) |
| V291 | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| V292 | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| V295 | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| V298 | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| V30 | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| V302 | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| V305 | Near-zero variance (>99.9% single value) |
| V31 | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| V311 | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| V319 | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| V32 | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| V321 | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| V322_was_missing | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| V33 | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| V331 | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| V333 | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| V334 | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| V336 | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| V337 | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| V339 | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| V35_was_missing | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| V41 | Near-zero variance (>99.9% single value) |
| V42 | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| V49 | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| V50 | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| V51 | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| V57 | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| V58 | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| V59 | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| V64 | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| V65 | Near-zero variance (>99.9% single value) |
| V68 | Near-zero variance (>99.9% single value) |
| V70 | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| V71 | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| V72 | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| V73 | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| V75_was_missing | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| V80 | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| V84 | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| V88 | Near-zero variance (>99.9% single value) |
| V89 | Near-zero variance (>99.9% single value) |
| V91 | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| V92 | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| V94 | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| V96 | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| V99 | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| email_domain_match | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| id_01_was_missing | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| id_02_was_missing | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| id_05_was_missing | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| id_11_was_missing | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| id_17_was_missing | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| id_19_was_missing | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| id_20_was_missing | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| id_32_was_missing | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| id_34_was_missing | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |
| transaction_hour | Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature) |

### Top 20 selected features by consensus rank (MI + embedded importance)

| Feature | MI score | MI rank | Importance score | Importance rank |
|---|---|---|---|---|
| V201 | 0.02834 | 1 | 0.01389 | 16 |
| V199 | 0.02756 | 2 | 0.00812 | 37 |
| V200 | 0.02668 | 3 | 0.00680 | 47 |
| V243 | 0.02632 | 4 | 0.00866 | 35 |
| V245 | 0.02618 | 5 | 0.00035 | 250 |
| V258 | 0.02590 | 6 | 0.01330 | 18 |
| V189 | 0.02574 | 7 | 0.00323 | 85 |
| V257 | 0.02540 | 8 | 0.01311 | 19 |
| V259 | 0.02510 | 9 | 0.00078 | 187 |
| V244 | 0.02471 | 10 | 0.00359 | 81 |
| V45 | 0.02387 | 11 | 0.00499 | 60 |
| V246 | 0.02293 | 12 | 0.01338 | 17 |
| V170 | 0.02222 | 13 | 0.00557 | 53 |
| V251 | 0.02210 | 14 | 0.00042 | 233 |
| card1_amt_mean | 0.02188 | 15 | 0.01113 | 23 |
| V86 | 0.02161 | 16 | 0.00256 | 106 |
| V188 | 0.02130 | 17 | 0.00102 | 165 |
| V176 | 0.02080 | 18 | 0.00026 | 266 |
| V186 | 0.02080 | 19 | 0.00015 | 292 |
| card1_amt_std | 0.02047 | 20 | 0.00796 | 40 |

## 5. Train/test split
- Strategy: time_aware
- Train rows: 472,432 (fraud rate 0.0351)
- Test rows: 118,108 (fraud rate 0.0344)
- Train time range: (86400.0, 12192842.0)
- Test time range: (12192900.0, 15811131.0)

## 6. Metadata columns (preserved, non-feature)

These columns are present in the processed train/test CSVs for traceability, auditing, explainability, and fairness slicing. They are extracted BEFORE feature selection/preprocessing and never pass through imputation, scaling, encoding, or selection -- **they must never be included in the X passed to model.fit()/predict()**.

| Column | Role |
|---|---|
| TransactionID | Row identifier (traceability/audit) |
| card6 | Fairness sensitive/proxy attribute |
| card4 | Fairness sensitive/proxy attribute |
| DeviceType | Fairness sensitive/proxy attribute |

## 7. Persisted inference artifacts (joblib)

Every fitted stage is persisted so Module 3+ (and later deployment) can apply the identical transformation to new data without refitting on this dataset again.

| Artifact | Contents |
|---|---|
| `C:\Users\LOQ\OneDrive - Arab Academy for Science and Technology\DEPI Grad Project\Secure-Compliant-ML-Security--main\Secure-Compliant-ML-Security--main\artifacts_m2\engineering_pipeline.joblib` | Fitted feature-engineering Pipeline (time/amount features, email grouping, frequency encoders, card velocity stats, missing-indicator patterns) |
| `C:\Users\LOQ\OneDrive - Arab Academy for Science and Technology\DEPI Grad Project\Secure-Compliant-ML-Security--main\Secure-Compliant-ML-Security--main\artifacts_m2\column_selector.joblib` | Fitted `SelectedColumnsTransformer` embodying the feature-selection decision |
| `C:\Users\LOQ\OneDrive - Arab Academy for Science and Technology\DEPI Grad Project\Secure-Compliant-ML-Security--main\Secure-Compliant-ML-Security--main\artifacts_m2\preprocessing_pipeline.joblib` | Fitted `ColumnTransformer` (imputers, `RobustScaler`, `OneHotEncoder`) |
| `C:\Users\LOQ\OneDrive - Arab Academy for Science and Technology\DEPI Grad Project\Secure-Compliant-ML-Security--main\Secure-Compliant-ML-Security--main\artifacts_m2\full_inference_pipeline.joblib` | Single composed Pipeline chaining all three stages above -- the one artifact Module 3/deployment should load for end-to-end raw-to-model-ready transformation |
| `C:\Users\LOQ\OneDrive - Arab Academy for Science and Technology\DEPI Grad Project\Secure-Compliant-ML-Security--main\Secure-Compliant-ML-Security--main\artifacts_m2\feature_selector.joblib` | The `FeatureSelectionComparator` configuration used (thresholds, sample size, seed) for exact reproducibility |