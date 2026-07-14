# Evidence Register

This register lists every significant project-specific claim made in
`Secure_Compliant_ML_Security_Report.md`, the repository evidence it is based on, its
verification status, and the report section in which it is used. Verification-status
labels follow the taxonomy defined in Chapter 1 of the report: **Implemented and
experimentally verified**, **Locally tested**, **Unit tested**, **Dry-run verified**,
**Designed but not deployed**, **Documented target state**, **Partially implemented**,
**Not independently verified**, **Recommended future work**.

| Claim ID | Claim | Repository Evidence | Verification Status | Report Section |
|---|---|---|---|---|
| C001 | The raw IEEE-CIS dataset has 590,540 transaction rows | `reports_m2/dataset_manifest.json` | Implemented and experimentally verified | 4.2 |
| C002 | The target class (`isFraud`) is heavily imbalanced | `reports_m2/dataset_manifest.json`; class-rate figures | Implemented and experimentally verified | 4.3 |
| C003 | PR-AUC is the primary evaluation metric because of class imbalance | `reports_m3/model_comparison_leaderboard.csv`; Chapter 2.2 methodology discussion | Documented (methodological justification) | 4.4 |
| C004 | Sensitive fields are encrypted using Fernet (AES-128-CBC + HMAC authentication), not AES-256 | `src/data/validators.py::_check_pii_columns_encrypted` | Implemented and experimentally verified | 6.2 |
| C005 | CreditCardNumber's classification label and its lineage treatment disagree across Milestone 1 artifacts | `reports/` classification and lineage reports (Milestone 1, consumed not owned) | Documented target state / discrepancy noted | 6.3 |
| C006 | Protected storage (Azure Blob Storage) for encrypted data is a target architecture, not a live deployment | `reports/` architecture description; no Azure credentials present in repository | Documented target state | 6.6 |
| C007 | Module 1 (data validation) runs 9 checks (7 critical, 2 warning) against the real dataset, all passing | `src/data/validators.py`; `reports_m2/module1_validation_report.json` | Implemented and experimentally verified | 7.x |
| C008 | PII-encryption is independently re-verified rather than trusted from the Milestone 1 classification report | `src/data/validators.py::_check_pii_columns_encrypted`; `tests/test_validators.py` | Implemented and experimentally verified | 7.x |
| C009 | Feature engineering produces 466 candidate features from raw transaction/identity columns with no test-fold leakage | `src/features/engineering.py`; `tests/test_feature_engineering.py` | Implemented and experimentally verified | 8.2-8.3 |
| C010 | A single strongest engineered signal is `email_domain_match` (9.65% fraud rate vs 2.21%) | `src/features/engineering.py` (EmailDomainGrouper); EDA output referenced in report text | Implemented and experimentally verified | 8.3 |
| C011 | The four-method feature-selection funnel reduces 466 candidates to 150 selected features (135 numeric + 15 categorical) | `src/features/selection.py`; `reports_m2/feature_selection_summary.json`; `reports_m2/feature_manifest.json` | Implemented and experimentally verified | 8.4-8.5 |
| C012 | Recursive Feature Elimination was deliberately excluded as computationally infeasible at this dimensionality | `src/features/selection.py` design notes; report text | Documented (design decision) | 8.5 |
| C013 | Five model families were trained and compared with hyperparameter tuning | `src/models/train.py`; `src/models/tune.py`; `reports_m3/model_comparison_leaderboard.csv` | Implemented and experimentally verified | 9.x |
| C014 | LightGBM was selected as the best model with ROC-AUC 0.8807 and PR-AUC 0.4869 on the real holdout set | `reports_m3/model_comparison_leaderboard.csv`; `figures/fig9_1_roc_curve.png`; `figures/fig9_2_pr_curve.png` | Implemented and experimentally verified | 9.x |
| C015 | The winning model's exact hyperparameters (n_estimators=450, num_leaves=249, etc.) are as stated | `reports_m3/model_comparison_leaderboard.csv` (`best_params` field, read verbatim) | Implemented and experimentally verified | Appendix C |
| C016 | The inference bundle persists model + preprocessing pipeline as a single reusable artifact | `src/models/inference_bundle.py`; `tests/test_inference_bundle.py`; `tests/test_pipeline_persistence.py` | Implemented and experimentally verified | 9.x, 12.x |
| C017 | DP-SGD training uses verified per-example gradient clipping | `src/privacy/dp_model.py`; `tests/test_dp_model.py` | Implemented and experimentally verified | 10.x |
| C018 | The authoritative privacy budget (epsilon) is computed via an RDP accountant | `src/privacy/privacy_accountant.py`; `tests/test_privacy_accountant.py`; `reports_m4/dp_report.md` | Implemented and experimentally verified | 10.x |
| C019 | Differential privacy caused a significant, honestly-reported reduction in model utility (not hidden or minimized) | `reports_m4/investigation/investigation_summary.json`; `figures/fig10_1`-`fig10_3` | Implemented and experimentally verified | 10.x |
| C020 | An 8-phase root-cause investigation was conducted into the DP utility loss, including a noise-multiplier recovery sweep | `reports_m4/investigation/investigation_summary.json`; `scripts/run_module4_investigation.py`; `figures/fig10_3_privacy_utility.png` | Implemented and experimentally verified | 10.6-10.9 |
| C021 | Architectural/resampling improvements to reduce DP utility loss are recommended but not implemented | `reports_m4/investigation/investigation_summary.json` Section on recommendations | Recommended future work | 10.9, Chapter 25 |
| C022 | The dataset contains no genuine demographic field; fairness analysis uses card6/card4/DeviceType as proxy attributes only | `src/fairness/*.py`; report text (explicit framing, never called "demographic bias") | Documented (methodological framing) | 11.1 |
| C023 | card6 (debit vs. credit) fairness metrics: DIR=3.996 (95% CI 3.701-4.298), EOD=0.1890 (95% CI 0.1606-0.2188), both statistically significant | `reports_m5/fairness_metrics.csv`; `reports_m5/group_metrics.csv` | Implemented and experimentally verified | 11.3 |
| C024 | Fairness disparities are reported honestly, including unfavorable findings, not hidden | `reports_m5/bias_findings.md`; report text | Implemented and experimentally verified | 11.x |
| C025 | Every core fairness metric implementation was independently cross-validated against Fairlearn with a difference of exactly 0.0 | `tests/test_fairlearn_validation.py` | Implemented and experimentally verified | 11.2 |
| C026 | Bootstrap confidence intervals use 1,000 stratified resamples per protected-attribute group | `src/fairness/statistical_tests.py`; `tests/test_statistical_tests.py` | Implemented and experimentally verified | 11.2 |
| C027 | The FastAPI inference service is authenticated via JWT and was exercised end-to-end with the real LightGBM bundle (not a placeholder scorer) | `app/api/inference.py`; `app/core/security.py`; real request/response captured during this project's engineering work | Locally tested | 13.x, Appendix D |
| C028 | Rate limiting applies a stricter limit to the authentication endpoint than the inference endpoint | `app/core/limiter.py`; `app/api/auth.py` | Locally tested | 13.x |
| C029 | The FastAPI service has never been deployed to a live, externally-reachable server | Absence of any live-deployment evidence in the repository | Documented (negative claim, explicitly stated) | 13.x, 15.6 |
| C030 | The Docker image uses a hardened multi-stage build | `Dockerfile` | Locally tested (build succeeds) | 14.x |
| C031 | The Docker image has not been scanned for vulnerabilities | Absence of container-scanning step in `.github/workflows/` | Not independently verified / gap noted | 14.x, 21.7 |
| C032 | Kubernetes manifests (Namespace, ServiceAccount, Deployment, Service, 3x NetworkPolicy) validate successfully but were never applied to a live cluster | `k8s/*.yaml`; `kubectl apply --dry-run=client -f k8s/` executed during this project's engineering work | Designed but not deployed / Dry-run verified | 14.x, Table 14.1 |
| C033 | Terraform network, AKS, Key Vault, monitoring, and WAF modules validate successfully but have never been applied to a live Azure subscription | `iac/terraform/**`; `terraform init -backend=false && terraform validate` executed during this project's engineering work | Designed but not deployed / Dry-run verified | 15.x, Tables 15.1-15.6 |
| C034 | No live AKS cluster, live WAF blocking, live Key Vault secret retrieval, or production scalability/availability is claimed | Absence of any live-Azure evidence in the repository; explicit report statement | Documented (negative claim, explicitly stated) | 15.6 |
| C035 | The Security Architecture Documentation's live-AKS and always-on WAF language describes target state, not current-verified state | `docs/Security_Architecture_Documentation.docx` (reviewed in full) vs. Terraform/K8s dry-run-only evidence | Documented target state / discrepancy noted respectfully | 15.x, 18.x |
| C036 | The penetration test report documents 10 test cases (T1-T10), all PASS, and 4 findings (F1-F4) | `pentest/Penetration_Test_Report_Milestone3.docx` (reviewed in full, not re-executed) | Locally tested (per source document) / Not independently re-verified | 17.x |
| C037 | The STRIDE threat table and Key Vault secrets inventory in the security documentation were extracted and reviewed verbatim | `docs/Security_Architecture_Documentation.docx` | Documented (source reviewed) | 16.x, Table 16.1 |
| C038 | The Milestone 4 compliance audit identifies documentation inconsistencies (AES-256 vs. Fernet/AES-128; live-AKS claims vs. Terraform-only reality) that this report resolves in favor of directly-verified repository evidence | `compliance/` documents (Milestone 4) vs. `src/data/validators.py`, `iac/terraform/**` | Documented / Not independently verified (third-party document reviewed, not re-executed) | 18.x |
| C039 | No formal legal compliance certification (GDPR/HIPAA/ISO 27001) is claimed by this project | Absence of any certification artifact; explicit report statement | Documented (negative claim, explicitly stated) | 18.x |
| C040 | Compliance inconsistencies are framed as documentation/verification gaps, not attributed to individual team-member fault | Report text (explicit framing per master-prompt instruction) | Documented (editorial framing) | 18.x |
| C041 | Drift monitoring (Evidently-based) was executed against real `data/processed/{train,test}.csv` and produced a fresh drift status | `drift_monitor.py`; `reports_m5/drift_report.html`; `reports_m5/drift_summary.csv`; `reports_m5/drift_status.json` (regenerated during this project's engineering work, not a stale copy) | Implemented and experimentally verified | 19.x |
| C042 | The WORM audit-log upload script was verified only via `--dry-run`; no live Azure Blob Storage upload has ever occurred | `worm_storage.py`; `tests/test_worm_storage.py`; absence of Azure Storage credentials in the repository | Dry-run verified | 20.x |
| C043 | Six Azure Storage/identity secrets are required for a real WORM upload and none are configured in this repository | `.github/workflows/mlops-pipeline.yml` secret references; absence of configured secrets | Documented (negative claim, explicitly stated) | 21.5 |
| C044 | Two real bugs (a `--features` flag mismatch and a working-directory path mismatch) were found and fixed in the original CI/CD workflow during integration | `.github/workflows/mlops-pipeline.yml` (as fixed); comparison against the pre-integration version of the workflow | Implemented and experimentally verified | 21.x |
| C045 | The CI/CD pipeline's fail-pipeline gate triggers only on critical findings combined with real (non-synthetic) data | `.github/workflows/mlops-pipeline.yml` | Implemented and experimentally verified | 21.x |
| C046 | The automated test suite contains exactly 178 tests across 35 files, all passing | `tests/` (35 files); `pytest --collect-only -q` output, cross-verified against 2 prior independent pytest runs and 1 VS Code Test Explorer run | Implemented and experimentally verified | 22.x, Appendix E |
| C047 | An initial sub-agent-produced test count (174, from static grep analysis) undercounted by missing 3 test files entirely, and was corrected by direct pytest execution | `tests/test_statistical_tests.py`, `tests/test_threshold.py`, `tests/test_tune.py` (the 3 missed files); `pytest --collect-only -q` | Implemented and experimentally verified (methodology self-audit) | 22.1 |
| C048 | Testing is unit/integration-level only; no live end-to-end test exists against deployed infrastructure, because no infrastructure is deployed | Absence of any live-infrastructure test in `tests/`; consistent with C032-C034 | Documented (scope limitation, explicitly stated) | 22.x |
| C049 | Every functional requirement (FR-1 through FR-15) maps to at least one implementing file and, where applicable, a test file | Table 3.1; cross-referenced against `src/`, `app/`, `tests/` | Documented (derived directly from repository inspection) | 3.1, Appendix F |
| C050 | The STRIDE and ML/supply-chain threat tables are an analytical exercise conducted for this report, not a certified third-party red-team assessment | Report text (explicit scope statement); Tables 16.1-16.2 | Documented (explicitly scoped) | 16.x |

## Notes on Evidence Quality

- Claims C001-C028, C041, C044-C049 are backed by artifacts generated or executed directly during this
  project's engineering work (this repository's own code, tests, and generated reports) and carry the
  highest confidence.
- Claims C036-C038 are backed by third-party documents (penetration test report, compliance audit,
  security architecture documentation) produced by other project team members; these were read in full
  and are reported faithfully, but their internal findings were not independently re-executed by the
  author of this report.
- Claims C029, C034, C042, C043, C048 are deliberately negative claims (stating what has *not* been
  done) included to prevent over-claiming, per the master prompt's explicit accuracy requirements.
