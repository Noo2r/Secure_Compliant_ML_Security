# Source Inventory

This inventory lists every repository path directly inspected and used as evidence while
writing `Secure_Compliant_ML_Security_Report.md`. Package caches, virtual environments,
`mlruns/` MLflow internals, and gitignored raw data files are excluded as they add no
report-relevant information. "Evidence category" follows: **implementation** (source code),
**result** (generated output/report), **design** (architecture/config, not yet deployed),
**test** (automated test), **claim** (third-party document making a claim to be checked).

| Path | Type | Purpose | Relevant Chapters | Evidence Category | Contradiction / Duplication Notes |
|---|---|---|---|---|---|
| `README.md` | Markdown | Project-wide overview, milestone summary | 1, Appendix A | Implementation | None |
| `reports/` (Milestone 1) | JSON/Markdown | Classification, lineage, access-control, DPIA artifacts | 6 | Result (consumed, not owned by this repo) | CreditCardNumber classification vs. lineage treatment disagreement (Section 6.3) |
| `src/data/validators.py` | Python | 9-check data validation (7 critical, 2 warning), PII-encryption re-verification | 6, 7 | Implementation | None |
| `src/data/secure_data_loader.py` | Python | `DatasetManifest`, dataset-version hashing | 4, 6 | Implementation | None |
| `reports_m2/dataset_manifest.json` | JSON | Dataset dimensions, version hash `e457d0eb2c3b9e45` | 4 | Result | None |
| `reports_m2/feature_manifest.json` | JSON | Selected 150-feature list, numeric/categorical split | 8, Appendix B | Result | None |
| `reports_m2/feature_selection_summary.json` | JSON | Candidate/dropped/selected feature counts per stage | 8 | Result | None |
| `reports_m2/module1_validation_report.json` | JSON | Per-check validation results | 7 | Result | None |
| `src/config/config.yaml` | YAML | Top-level pipeline configuration (project, paths, secure_data, validation, feature_engineering, feature_selection, train_test_split, fairness, azure_ml, mlflow, model_development, dp, etc.) | 3, 5, 12 | Design/Implementation | None |
| `src/features/engineering.py` | Python | Six feature-engineering transformers | 8 | Implementation | None |
| `src/features/selection.py` | Python | `FeatureSelectionComparator`, four-method funnel | 8 | Implementation | None |
| `tests/test_feature_engineering.py` | Python | Feature-engineering unit tests (6) | 8, 22 | Test | None |
| `tests/test_feature_selection.py` | Python | Feature-selection unit tests (7) | 8, 22 | Test | None |
| `src/models/train.py` | Python | Model training for 5 model families | 9 | Implementation | None |
| `src/models/tune.py` | Python | Optuna hyperparameter optimization | 9 | Implementation | None |
| `src/models/model_registry.py` | Python | Model registry logic | 9, 12 | Implementation | None |
| `src/models/inference_bundle.py` | Python | Self-contained inference artifact | 9, 12, 13 | Implementation | None |
| `reports_m3/model_comparison_leaderboard.csv` | CSV | Full leaderboard with metrics and `best_params` per model | 9, Appendix C | Result | Read in full via direct file access; used verbatim |
| `figures/fig9_1-fig9_7` (`reports_m3/`) | PNG | ROC curve, PR curve, confusion matrix, feature importance, lift/gain, learning curve, validation curve | 9 | Result | None |
| `tests/test_comparison.py`, `test_tune.py`, `test_model_registry.py`, `test_model_loader.py`, `test_pipeline_persistence.py`, `test_inference_bundle.py` | Python | Model-pipeline unit tests | 9, 12, 22 | Test | None |
| `src/privacy/dp_model.py` | Python | DP-SGD training with per-example clipping | 10 | Implementation | None |
| `src/privacy/privacy_accountant.py` | Python | RDP accountant, epsilon computation | 10 | Implementation | None |
| `reports_m4/dp_report.md` | Markdown | DP experiment narrative and metrics | 10 | Result | None |
| `reports_m4/investigation/investigation_summary.json` | JSON | 8-phase DP investigation results, noise-multiplier sweep | 10 | Result | None |
| `scripts/run_module4_investigation.py` | Python | Driver script for the DP investigation | 10 | Implementation | None |
| `figures/fig10_1-fig10_3` (`reports_m4/`) | PNG | Normal ROC, DP ROC, privacy-utility curve | 10 | Result | None |
| `tests/test_dp_model.py`, `test_dp_experiment.py`, `test_dp_evaluation.py`, `test_dp_diagnostics.py`, `test_dp_config.py`, `test_dp_persistence.py`, `test_dp_mlflow.py`, `test_dp_report_builder.py`, `test_privacy_accountant.py` | Python | DP unit tests (9 files, 36 tests total) | 10, 22 | Test | None |
| `src/fairness/*.py` | Python | Fairness metric computation, statistical tests, plots, dashboard | 11 | Implementation | None |
| `reports_m5/fairness_metrics.csv` | CSV | card6/card4/DeviceType metric values with CIs | 11 | Result | None |
| `reports_m5/group_metrics.csv` | CSV | Per-group selection rates, TPR, FPR | 11 | Result | None |
| `reports_m5/fairness_summary.json` | JSON | Aggregated fairness summary | 11 | Result | None |
| `reports_m5/bias_findings.md` | Markdown | Narrative bias findings, stated honestly | 11 | Result | None |
| `figures/fig11_1-fig11_2` (`reports_m5/`) | PNG | Fairness dashboard, card6 disparate impact | 11 | Result | None |
| `tests/test_fairness_metrics.py`, `test_fairness_config.py`, `test_bias_detector.py`, `test_fairness_report_builder.py`, `test_fairness_plots.py`, `test_fairness_mlflow.py`, `test_fairlearn_validation.py`, `test_statistical_tests.py`, `test_attribute_analysis.py` | Python | Fairness unit tests (9 files, 45 tests total) | 11, 22 | Test | None |
| `app/api/inference.py` | Python | Prediction endpoint | 13 | Implementation | None |
| `app/api/auth.py` | Python | Authentication endpoint | 13 | Implementation | None |
| `app/core/security.py` | Python | JWT creation/validation | 13 | Implementation | None |
| `app/core/limiter.py` | Python | Rate limiting | 13 | Implementation | None |
| `app/models/schemas.py` | Python | Request/response schemas (rewritten during Milestone 3 integration to match the real feature contract) | 13 | Implementation | None |
| `app/models/model_loader.py` | Python | `ModelService`, loads real LightGBM bundle | 13 | Implementation | None |
| `app/main.py` | Python | FastAPI app entrypoint, health endpoint | 13 | Implementation | None |
| `.env.example` | Text | Environment variable template (no real secrets) | 13, Appendix L | Design | None |
| `Dockerfile` | Dockerfile | Multi-stage hardened container build | 14 | Implementation | None |
| `k8s/*.yaml` | YAML | Namespace, ServiceAccount, Deployment, Service, 3x NetworkPolicy | 14 | Design (dry-run validated) | None |
| `iac/terraform/network/*` | Terraform (HCL) | VNet, subnets, NSGs | 15 | Design (dry-run validated) | None |
| `iac/terraform/aks/*` | Terraform (HCL) | Private AKS cluster, RBAC, Workload Identity | 15 | Design (dry-run validated) | None |
| `iac/terraform/keyvault/*` | Terraform (HCL) | Key Vault, public access disabled, private endpoint | 15 | Design (dry-run validated) | None |
| `iac/terraform/monitoring/*` | Terraform (HCL) | Log Analytics, Defender for Cloud | 15 | Design (dry-run validated) | None |
| `iac/terraform/waf/*` | Terraform (HCL) | Application Gateway WAF_v2, OWASP CRS 3.2 | 15 | Design (dry-run validated) | None |
| `docs/Security_Architecture_Documentation.docx` | DOCX | Security architecture narrative, STRIDE table, Key Vault secrets list | 15, 16, 18 | Claim (third-party document) | Live-AKS/always-on-WAF language describes target state; flagged and reconciled in Chapter 18 |
| `docs/WAF_Rules.md` | Markdown | Custom WAF rule definitions | 15 | Design | None |
| `docs/network_diagram.png` | PNG | Real network diagram (used as Figure 15.2) | 15 | Result | None |
| `pentest/Penetration_Test_Report_Milestone3.docx` | DOCX | 10 test cases (T1-T10, all PASS), 4 findings (F1-F4) | 17 | Claim (third-party document) | Reviewed in full, not independently re-executed |
| `compliance/` (Milestone 4 documents) | DOCX/Markdown | Independent compliance audit of Milestones 1-3 | 18 | Claim (third-party document) | AES-256 claim vs. Fernet/AES-128 implementation; live-AKS claim vs. Terraform-only reality — both reconciled respectfully in Chapter 18 |
| `drift_monitor.py` | Python | Evidently-based drift monitoring, synthetic-data fallback | 19 | Implementation | Path-fixed during Milestone 5 integration (`_GRADPROJ_ROOT` hardcoded absolute path corrected) |
| `reports_m5/drift_report.html`, `drift_summary.csv`, `drift_status.json` | HTML/CSV/JSON | Freshly regenerated drift-monitor output | 19 | Result | Regenerated during this project's engineering work, not the stale copy originally committed |
| `worm_storage.py` | Python | WORM audit-log upload script, `--dry-run` mode | 20 | Implementation | Path-fixed during Milestone 5 integration |
| `.github/workflows/mlops-pipeline.yml` | YAML | CI/CD pipeline: drift-monitor job, WORM-upload job, alert-on-drift job | 19, 20, 21 | Implementation | Two real bugs fixed during integration: `--features` flag mismatch, working-directory path mismatch |
| `requirements-milestone5.txt` | Text | Milestone 5 Python dependencies (evidently, azure-storage-blob) | Appendix L | Design | Renamed from original `requirements.txt` to match per-milestone convention |
| `tests/test_drift_monitor.py` | Python | Drift-status threshold classification unit tests (6) | 19, 22 | Test | Added during Milestone 5 integration |
| `tests/test_worm_storage.py` | Python | `_sha256`, `_blob_name`, `_collect_files` unit tests (8) | 20, 22 | Test | Added during Milestone 5 integration |
| `tests/test_compliance_real.py` | Python | Real PII-encryption and real 401-auth tests (3) | 18, 22 | Test | Added during Milestone 4 integration |
| `tests/` (35 files total) | Python | Complete automated test suite | 22, Appendix E | Test | 178 tests confirmed via `pytest --collect-only -q`, cross-verified 3 independent ways after correcting an initial sub-agent undercount (174) |
| `pytest.ini` | INI | Scopes pytest discovery to `tests/` | 22, Appendix A | Design | Also fixed a `.vscode/settings.json` pytest-scoping bug during earlier verification work (outside report scope) |
| `requirements-milestone2.txt`, `requirements-milestone3.txt` | Text | Per-milestone Python dependencies | Appendix L | Design | None |
| `scripts/run_module1.py` .. `run_module5.py` | Python | Module driver scripts | 5, 7-11, Appendix A, L | Implementation | None |

## Explicitly Not Copied Into the Report

- `mlruns/` (MLflow tracking store, gitignored, machine-local) — referenced narratively in Chapter 12
  but not treated as a citable artifact.
- `data/` (raw and processed datasets, gitignored) — referenced by path only; no raw records reproduced,
  per the master prompt's instruction not to expose sensitive raw data.
- `artifacts_m2/` .. `artifacts_m5/` binary model/pipeline files (joblib, Keras) — existence and role
  referenced in text; binary internals not dumped into the report.
