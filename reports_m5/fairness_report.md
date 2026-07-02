# Module 5 — Fairness Analysis Report

- Model analyzed: **lightgbm** (Module 3's production model)
- Dataset version: `e457d0eb2c3b9e45`

## Executive Summary

Primary fairness attribute: **card6**. 1 of 1 group(s) show a statistically significant selection-rate disparity (95% bootstrap CI excludes zero): ['credit'].
- 'credit' vs. reference 'debit': SPD=+0.0424, DIR=3.996, EOD=+0.1890, AOD=+0.1037.

## Methodology

Group fairness metrics computed on Module 2's held-out test set (never used for training or model selection). Statistical Parity Difference, Disparate Impact Ratio, Equal Opportunity Difference, and Average Odds Difference are each reported with a 95% **stratified bootstrap confidence interval** (1000 resamples, drawn independently within each group to preserve group sizes), so a disparity can be judged statistically meaningful (CI excludes the null value) rather than read off a point estimate alone. Group-membership independence from predicted outcome is additionally tested via chi-square (or Fisher's exact test for 2-group comparisons when Cochran's rule is violated) -- see `statistical_tests.py`'s module docstring for the full decision rule and its assumptions.

## Protected Groups (Proxy Attributes — See Limitations)

| Attribute | Reference Group | Primary | Description |
|---|---|---|---|
| card6 | debit | True | Card funding type (debit vs credit) -- a payment-behavior proxy, not a demographic attribute. |
| card4 | visa | False | Card network (visa/mastercard/discover/amex) -- a payment-behavior proxy. Discover/Amex are small subgroups (~1,100-1,250 rows in the test set); report with reduced-confidence caveats, do not suppress. |
| DeviceType | desktop | False | Device used (desktop/mobile) -- 80.4% missing in the test set (verified, worse than Module 2's 76% full-dataset figure). Excluded from primary analysis; reported only as a documented limitation, consistent with Module 2's original excluded_candidate_attribute decision. |

## Proxy Limitations — Read Before Interpreting Any Result Below

**None of the attributes analyzed below are true demographic attributes.** The IEEE-CIS fraud dataset contains no age, gender, race, or other demographic fields. `card6` (debit vs. credit) and `card4` (card network) are payment-behavior proxies; `DeviceType` is a device-usage proxy with 80%+ missingness in the test set. Any disparity reported here reflects differences in **financial/behavioral patterns across these proxy groups**, not demographic discrimination. Treat findings as inputs to a business/compliance review, not as a demographic bias certification.

## Attribute: card6

Card funding type (debit vs credit) -- a payment-behavior proxy, not a demographic attribute.

### Group-wise Metrics

| Group | n | Selection Rate | TPR (Recall) | FPR | FNR | Precision | F1 | Balanced Acc. | ROC-AUC | PR-AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| Missing | 743 | 0.0310 | 0.4667 | 0.0220 | 0.5333 | 0.3043 | 0.3684 | 0.7223 | 0.9384 | 0.4658 |
| credit | 27,270 | 0.0565 | 0.5247 | 0.0242 | 0.4753 | 0.5996 | 0.5597 | 0.7503 | 0.8880 | 0.5750 |
| debit | 90,095 | 0.0141 | 0.3357 | 0.0058 | 0.6643 | 0.6028 | 0.4312 | 0.6650 | 0.8646 | 0.4193 |

### Fairness Metrics (vs. reference group, with 95% bootstrap CI)

| Group | SPD | SPD 95% CI | DIR | DIR 95% CI | EOD | EOD 95% CI | AOD | AOD 95% CI | Statistically Significant? |
|---|---|---|---|---|---|---|---|---|---|
| credit | +0.0424 | [+0.0395, +0.0453] | 3.996 | [3.701, 4.298] | +0.1890 | [+0.1606, +0.2188] | +0.1037 | [+0.0894, +0.1190] | YES (SPD CI excludes 0) |

### Significance Test: Chi Square
- Statistic: 1603.8908, p-value: 0.000000, alpha: 0.05
- Result: **Statistically significant**
- Cochran's rule satisfied -- chi-square test of independence is valid.

### Fairlearn Cross-Validation

| Metric | Own Value | Fairlearn Value | Abs. Diff. | Within Tolerance |
|---|---|---|---|---|
| statistical_parity_difference (compared as |own_SPD| vs Fairlearn's unsigned max-min difference) | 0.042368 | 0.042368 | 0.00e+00 | True |
| disparate_impact_ratio (compared in Fairlearn's normalized min/max form) | 0.250237 | 0.250237 | 0.00e+00 | True |
| selection_rate[credit] | 0.056509 | 0.056509 | 0.00e+00 | True |
| selection_rate[debit] | 0.014141 | 0.014141 | 0.00e+00 | True |

## Attribute: card4

Card network (visa/mastercard/discover/amex) -- a payment-behavior proxy. Discover/Amex are small subgroups (~1,100-1,250 rows in the test set); report with reduced-confidence caveats, do not suppress.

### Group-wise Metrics

| Group | n | Selection Rate | TPR (Recall) | FPR | FNR | Precision | F1 | Balanced Acc. | ROC-AUC | PR-AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| Missing | 744 | 0.0309 | 0.4667 | 0.0219 | 0.5333 | 0.3043 | 0.3684 | 0.7224 | 0.9378 | 0.4643 |
| american express | 1,126 | 0.0320 | 0.4242 | 0.0201 | 0.5758 | 0.3889 | 0.4058 | 0.7021 | 0.8887 | 0.4773 |
| discover | 1,257 | 0.0716 | 0.3717 | 0.0420 | 0.6283 | 0.4667 | 0.4138 | 0.6649 | 0.7786 | 0.4456 |
| mastercard | 38,355 | 0.0245 | 0.4537 | 0.0103 | 0.5463 | 0.5930 | 0.5140 | 0.7217 | 0.8950 | 0.5185 |
| visa | 76,626 | 0.0228 | 0.4033 | 0.0091 | 0.5967 | 0.6167 | 0.4877 | 0.6971 | 0.8753 | 0.4753 |

### Fairness Metrics (vs. reference group, with 95% bootstrap CI)

| Group | SPD | SPD 95% CI | DIR | DIR 95% CI | EOD | EOD 95% CI | AOD | AOD 95% CI | Statistically Significant? |
|---|---|---|---|---|---|---|---|---|---|
| american express | +0.0092 | [-0.0007, +0.0199] | 1.402 | [0.968, 1.884] | +0.0210 | [-0.1517, +0.2015] | +0.0160 | [-0.0718, +0.1067] | No |
| discover | +0.0488 | [+0.0348, +0.0629] | 3.139 | [2.495, 3.791] | -0.0316 | [-0.1205, +0.0596] | +0.0006 | [-0.0457, +0.0486] | YES (SPD CI excludes 0) |
| mastercard | +0.0017 | [-0.0001, +0.0035] | 1.075 | [0.995, 1.158] | +0.0504 | [+0.0169, +0.0853] | +0.0258 | [+0.0086, +0.0431] | No |

### Significance Test: Chi Square
- Statistic: 131.0804, p-value: 0.000000, alpha: 0.05
- Result: **Statistically significant**
- Cochran's rule satisfied -- chi-square test of independence is valid.

### Fairlearn Cross-Validation

| Metric | Own Value | Fairlearn Value | Abs. Diff. | Within Tolerance |
|---|---|---|---|---|
| statistical_parity_difference (compared as |own_SPD| vs Fairlearn's unsigned max-min difference) | 0.009159 | 0.009159 | 0.00e+00 | True |
| disparate_impact_ratio (compared in Fairlearn's normalized min/max form) | 0.713512 | 0.713512 | 0.00e+00 | True |
| selection_rate[american express] | 0.031972 | 0.031972 | 0.00e+00 | True |
| selection_rate[visa] | 0.022812 | 0.022812 | 0.00e+00 | True |

## Attribute: DeviceType (EXCLUDED FROM PRIMARY ANALYSIS)

Device used (desktop/mobile) -- 80.4% missing in the test set (verified, worse than Module 2's 76% full-dataset figure). Excluded from primary analysis; reported only as a documented limitation, consistent with Module 2's original excluded_candidate_attribute decision.

### Group-wise Metrics

| Group | n | Selection Rate | TPR (Recall) | FPR | FNR | Precision | F1 | Balanced Acc. | ROC-AUC | PR-AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| Missing | 94,936 | 0.0079 | 0.1386 | 0.0052 | 0.8614 | 0.3489 | 0.1984 | 0.5667 | 0.8221 | 0.1863 |
| desktop | 13,620 | 0.0816 | 0.7153 | 0.0266 | 0.2847 | 0.7005 | 0.7079 | 0.8444 | 0.9305 | 0.7507 |
| mobile | 9,552 | 0.1024 | 0.6035 | 0.0377 | 0.3965 | 0.6738 | 0.6367 | 0.7829 | 0.9040 | 0.6753 |

### Fairness Metrics (vs. reference group, with 95% bootstrap CI)

| Group | SPD | SPD 95% CI | DIR | DIR 95% CI | EOD | EOD 95% CI | AOD | AOD 95% CI | Statistically Significant? |
|---|---|---|---|---|---|---|---|---|---|
| mobile | +0.0207 | [+0.0132, +0.0283] | 1.254 | [1.157, 1.361] | -0.1119 | [-0.1512, -0.0715] | -0.0504 | [-0.0699, -0.0297] | YES (SPD CI excludes 0) |

### Significance Test: Chi Square
- Statistic: 5484.6397, p-value: 0.000000, alpha: 0.05
- Result: **Statistically significant**
- Cochran's rule satisfied -- chi-square test of independence is valid.

### Fairlearn Cross-Validation

| Metric | Own Value | Fairlearn Value | Abs. Diff. | Within Tolerance |
|---|---|---|---|---|
| statistical_parity_difference (compared as |own_SPD| vs Fairlearn's unsigned max-min difference) | 0.020742 | 0.020742 | 0.00e+00 | True |
| disparate_impact_ratio (compared in Fairlearn's normalized min/max form) | 0.797413 | 0.797413 | 0.00e+00 | True |
| selection_rate[mobile] | 0.102387 | 0.102387 | 0.00e+00 | True |
| selection_rate[desktop] | 0.081645 | 0.081645 | 0.00e+00 | True |
