# Secure & Compliant ML Security Pipeline

An end-to-end, security- and compliance-first machine learning system for credit-card
fraud detection on the [IEEE-CIS Fraud Detection](https://www.kaggle.com/c/ieee-fraud-detection)
dataset (590,540 transactions, 428 raw columns). Data security, model quality,
differential privacy, algorithmic fairness, secure deployment, regulatory compliance,
and production MLOps are treated as first-class, independently verified requirements
of the pipeline — not bolted on afterward.

This repository is the integration of five team milestones into a single working
codebase.

## Milestones

| # | Milestone | Owner | What it delivers |
|---|---|---|---|
| 1 | Data Security | Yara | AES/Fernet field-level encryption, data classification, lineage tracking, Azure Blob storage — see `reports/` |
| 2 | Model Development & Risk Analysis | Nour Eldin Ahmed | The core ML pipeline: data validation, feature engineering, model training, differential privacy, fairness analysis — see [Module Breakdown](#module-breakdown-milestone-2) below |
| 3 | Secure Deployment | Ali Yasser | FastAPI inference service, JWT auth, rate limiting, Azure Key Vault, AKS/WAF Terraform, penetration testing — see `app/`, `docs/`, `pentest/` |
| 4 | Compliance QA | Farida Elgharbawy | Independent GDPR/HIPAA/ISO 27001 audit of Milestones 1 and 3 — see `compliance/` |
| 5 | MLOps | Youssef Tarek | Evidently-based data drift monitoring, WORM (write-once-read-many) immutable audit storage, CI/CD — see `drift_monitor.py`, `worm_storage.py`, `.github/workflows/` |

## Module breakdown (Milestone 2)

Milestone 2 — the ML engineering core — is itself five modules, each with real,
generated reports under `reports_mN/` and trained artifacts under `artifacts_mN/`:

| Module | Purpose | Key output |
|---|---|---|
| 1 — Data Validation | Independently verifies Milestone 1's encryption and data contract before any model touches the data | 9/9 validation checks pass — `reports_m2/module1_validation_report.json` |
| 2 — Feature Engineering & Selection | 466 candidate features → 150 selected via a 4-method consensus (near-zero-variance, correlation-redundancy, mutual information, embedded RF importance) | `reports_m2/feature_manifest.json` |
| 3 — Model Development | 5-model comparison (Logistic Regression, Random Forest, XGBoost, LightGBM, Neural Network), Optuna-tuned | **LightGBM wins**: holdout PR-AUC 0.4869, ROC-AUC 0.8807 — `reports_m3/model_comparison_leaderboard.csv` |
| 4 — Differential Privacy | DP-SGD training + RDP privacy accounting, plus an 8-phase root-cause investigation into DP's utility cost on this dataset | ε = 45.573 at δ = 1e-5; PR-AUC 0.1646 → 0.0285 under DP — `reports_m4/dp_report.md`, `reports_m4/investigation/` |
| 5 — Fairness Analysis | Bootstrap-CI'd fairness metrics (SPD/DIR/EOD/AOD) across card type, card network, and device type, cross-validated against Fairlearn | 24 findings; card6 (credit vs. debit): DIR = 3.996, EOD = +0.189 — `reports_m5/fairness_report.md` |

## Repository layout

```
src/                    Core ML pipeline (Modules 1-5): config, data, features, models,
                         evaluation, privacy, fairness, tracking, registry, utils
scripts/                Module entrypoints: run_module1.py .. run_module5.py
tests/                  178 tests (pytest) covering Modules 1-5, the deployment API,
                         and the compliance/drift/WORM tooling
data/                   Raw + processed datasets (gitignored — see Local setup)
reports/, reports_m2-5/ Generated reports, metrics, and plots — real outputs, committed
artifacts_m2-5/         Trained pipelines/models (joblib, Keras) — real outputs, committed
mlruns/                 MLflow experiment tracking (gitignored)

app/                    Milestone 3: FastAPI inference service (JWT auth, rate limiting,
                         Key Vault-backed secrets, security headers)
Dockerfile              Milestone 3: hardened, non-root, multi-stage container build
k8s/                    Milestone 3: Kubernetes manifests (namespace, Deployment, NetworkPolicy)
iac/terraform/          Milestone 3: AKS + Key Vault + App Gateway WAF + Defender IaC
docs/                   Milestone 3: security architecture docs, WAF rules
pentest/                Milestone 3: penetration test report

compliance/             Milestone 4: independent compliance audit (certificate, reports,
                         checklist) — kept verbatim/attributed, see note below

drift_monitor.py        Milestone 5: Evidently-based feature drift detection
worm_storage.py         Milestone 5: immutable (WORM) audit-log upload to Azure Blob Storage
.github/workflows/      Milestone 5: CI/CD — drift monitoring + WORM upload on every push

requirements-milestone{2,3,5}.txt   Per-milestone Python dependencies
pytest.ini                          Scopes `pytest` to tests/ (see note below)
```

## Local setup

```bash
git clone https://github.com/Noo2r/Secure_Compliant_ML_Security.git
cd Secure_Compliant_ML_Security
pip install -r requirements-milestone2.txt   # core ML pipeline

# Run the full Milestone 2 pipeline, in order (each depends on the previous module's output)
python scripts/run_module1.py
python scripts/run_module2.py
python scripts/run_module3.py
python scripts/run_module4.py
python scripts/run_module5.py
```

`data/`, `logs/`, and `mlruns/` are gitignored — raw and processed datasets are not
committed. `run_module1.py` will regenerate a secured dataset from the raw IEEE-CIS
CSVs if `data/encrypted/encrypted_dataset.csv` isn't already present.

### Running the tests

```bash
pip install -r requirements-milestone2.txt -r requirements-milestone3.txt -r requirements-milestone5.txt
pytest                 # 178 tests
```

### Running the inference API (Milestone 3)

```bash
pip install -r requirements-milestone3.txt
cp .env.example .env   # local dev only; MODEL_PATH defaults to the real trained LightGBM bundle
uvicorn app.main:app --reload
# POST /api/v1/auth/token, then POST /api/v1/inference/predict with the returned JWT
```

### Running drift monitoring / WORM upload locally (Milestone 5)

```bash
pip install -r requirements-milestone5.txt
python drift_monitor.py --features reports_m2/feature_manifest.json
python worm_storage.py --dry-run   # lists what would be uploaded; no Azure credentials needed
```

## CI/CD

`.github/workflows/mlops-pipeline.yml` runs on every push touching model artifacts or
monitoring code (plus a daily schedule): drift monitoring, then WORM audit-log upload
on `main`. It gracefully falls back to synthetic data / dry-run mode where real data or
Azure credentials aren't available in the runner, and only hard-fails on genuine,
actionable results — see the workflow file for the exact conditions.

## What's real vs. what's a template

Consistent with each milestone's own documentation:
- **Milestone 2** (`src/`, `scripts/`, all `reports_mN/`/`artifacts_mN/`) is fully
  real: every report and model artifact was generated by actually running the pipeline
  against the real dataset, not templated or fabricated.
- **Milestone 3** (`app/`) was run and tested locally against the real trained model;
  the Terraform in `iac/terraform/` is complete and internally consistent but has
  **not** been applied to a real Azure subscription.
- **Milestone 4** (`compliance/`) is kept verbatim and attributed to its author. Some
  of its claims (e.g. "AES-256", validation "across live AKS endpoints") describe an
  intended target state rather than this repository's current, verified state (Module
  1 actually uses Fernet/AES-128; no Azure infrastructure has been provisioned) —
  worth knowing before treating it as a completed compliance sign-off.
- **Milestone 5** (`drift_monitor.py`, `worm_storage.py`) runs for real against the
  real trained model and real feature selection; the WORM upload path is verified via
  `--dry-run` only, since (as with Milestone 3) no Azure Storage account has been
  provisioned yet.

## Tech stack

**ML/Data:** pandas, NumPy, scikit-learn, XGBoost, LightGBM, TensorFlow + TensorFlow
Privacy, Optuna, Fairlearn, MLflow, Azure ML
**Deployment:** FastAPI, Uvicorn, Docker, Kubernetes, Terraform, Azure (AKS, Key Vault,
Application Gateway/WAF, Defender for Cloud)
**MLOps/Compliance:** Evidently, Azure Blob Storage (WORM/immutable storage), GitHub
Actions
**Testing:** pytest (178 tests across all five milestones)
