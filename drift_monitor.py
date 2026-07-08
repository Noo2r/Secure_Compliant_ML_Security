"""
Milestone 5 — Production Drift Monitor
IEEE-CIS Fraud Detection Pipeline

Detects feature distribution shifts between the training baseline and a current
production batch using Evidently AI. When the processed train/test CSVs are not
available on the local machine, a realistic synthetic dataset is generated from
the project's known statistics (feature list from reports_m2/feature_selection_comparison.csv,
fraud rate ~3.5%, ~400K train rows / ~100K test rows).

Generates:
  - reports_m5/drift_report.html   : Full Evidently visual report
  - reports_m5/drift_summary.csv   : Per-feature drift flags
  - reports_m5/drift_status.json   : Pass/fail status for CI/CD

Usage (from F:\\My Files\\Milestone 5 Implementation):
    python drift_monitor.py
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
# This script lives at the repo root, so its own directory IS the project
# root -- no machine-specific absolute path needed.
_GRADPROJ_ROOT   = Path(__file__).resolve().parent
_SCRIPT_DIR      = Path(__file__).resolve().parent

DEFAULT_REFERENCE_CSV    = _GRADPROJ_ROOT / "data" / "processed" / "train.csv"
DEFAULT_CURRENT_CSV      = _GRADPROJ_ROOT / "data" / "processed" / "test.csv"
DEFAULT_FEATURE_MANIFEST = _GRADPROJ_ROOT / "reports_m2" / "feature_manifest.json"
DEFAULT_FEATURE_SEL_CSV  = _GRADPROJ_ROOT / "reports_m2" / "feature_selection_comparison.csv"
DEFAULT_OUTPUT_DIR       = _SCRIPT_DIR / "reports_m5"

DRIFT_SHARE_WARNING_THRESHOLD  = 0.10
DRIFT_SHARE_CRITICAL_THRESHOLD = 0.20

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("drift_monitor")

# ---------------------------------------------------------------------------
# Evidently imports
# ---------------------------------------------------------------------------
try:
    from evidently.report import Report
    from evidently.metric_preset import DataDriftPreset, TargetDriftPreset
    from evidently import ColumnMapping
except ImportError as exc:
    logger.critical(
        "Evidently is not installed or wrong version.\n"
        "Run: pip install 'evidently==0.4.33'\nError: %s", exc
    )
    sys.exit(1)


# ---------------------------------------------------------------------------
# Feature list: real Module 2 selection when available, else a synthetic-data
# fallback
# ---------------------------------------------------------------------------
#
# The original hardcoded guess below only overlapped 3 of the ~150 features
# Module 2 actually selected for the real trained model (verified by running
# this script against the real processed CSVs: "Features checked: 3", a
# meaningless drift_share computed from 3 columns). Real feature names differ
# in specific, non-obvious ways -- e.g. this project's real time features are
# `transaction_hour`/`transaction_day_of_week`, not `hour_of_day`/`day_of_week`;
# there's no single `missing_count` (there are per-column `*_was_missing`
# indicators instead); `P_emaildomain_grouped` was never selected (only
# `R_emaildomain_grouped` was); and only a handful of the guessed V-numbers
# match the real selection. Fixed below by loading the real, already-
# committed `reports_m2/feature_manifest.json` (which already splits into
# `numeric_features`/`categorical_features`) when it's available, matching
# the exact set the model was actually trained and evaluated on. The
# hardcoded list is kept as a fallback for the synthetic-data path (when the
# manifest genuinely isn't available yet, e.g. infra bring-up before Module 2
# has run), same resilience intent as the original.
_FALLBACK_FEATURES_NUM = [
    "TransactionAmt", "card1", "card2", "card3", "card5",
    "addr1", "addr2", "dist1",
    "C1", "C2", "C4", "C5", "C6", "C7", "C8", "C9", "C10", "C11", "C12", "C13", "C14",
    "D1", "D2", "D3", "D4", "D10", "D15",
    "V29", "V69", "V70", "V76", "V82", "V83", "V130", "V131",
    "V199", "V200", "V201", "V202", "V203",
    "V243", "V244", "V245", "V246", "V247",
    "V280", "V281", "V282", "V283", "V284",
    "V317", "V318", "V319", "V320",
    "card1_txn_count", "card1_amt_mean", "card1_amt_std",
    "TransactionAmt_log", "TransactionAmt_decimal",
    "hour_of_day", "day_of_week",
    "missing_count",
]

_FALLBACK_FEATURES_CAT = [
    "ProductCD", "card4", "card6",
    "P_emaildomain_grouped", "R_emaildomain_grouped",
    "M4", "M6",
]


def _load_selected_features(manifest_path: Path) -> tuple[list[str], list[str], bool]:
    """Loads the real Module 2 selected-feature lists from feature_manifest.json.

    Returns (numeric_features, categorical_features, used_real_manifest).
    Falls back to the hardcoded synthetic-data feature lists (with a logged
    warning) if the manifest isn't present.
    """
    if manifest_path.exists():
        with open(manifest_path, "r", encoding="utf-8") as fh:
            manifest = json.load(fh)
        numeric = manifest.get("numeric_features", [])
        categorical = manifest.get("categorical_features", [])
        logger.info(
            "Loaded real feature selection from %s: %d numeric + %d categorical features",
            manifest_path, len(numeric), len(categorical),
        )
        return numeric, categorical, True

    logger.warning(
        "Feature manifest not found at %s -- falling back to the hardcoded "
        "synthetic-data feature list (%d numeric + %d categorical). Run Module 2 "
        "first for real feature-level drift monitoring.",
        manifest_path, len(_FALLBACK_FEATURES_NUM), len(_FALLBACK_FEATURES_CAT),
    )
    return _FALLBACK_FEATURES_NUM, _FALLBACK_FEATURES_CAT, False

_TARGET_COL = "isFraud"

# Realistic distribution parameters from the IEEE-CIS dataset
_FRAUD_RATE_REF  = 0.035   # ~3.5% in training set
_FRAUD_RATE_CURR = 0.036   # ~3.6% in test set (slight natural variation)


def _generate_synthetic_dataset(
    n_rows: int,
    fraud_rate: float,
    rng: np.random.Generator,
    drift: bool = False,
) -> pd.DataFrame:
    """
    Generate a realistic synthetic IEEE-CIS-like dataset.

    Parameters
    ----------
    n_rows    : number of rows
    fraud_rate: fraction of rows with isFraud=1
    rng       : numpy random generator (for reproducibility)
    drift     : if True, apply mild distribution shift to some features
                (simulates what production drift looks like)
    """
    fraud_labels = (rng.random(n_rows) < fraud_rate).astype(int)
    data: dict = {_TARGET_COL: fraud_labels}

    drift_scale = 1.15 if drift else 1.0   # 15% scale shift on numeric features

    # --- Numeric features ---
    for feat in _FALLBACK_FEATURES_NUM:
        if "TransactionAmt" in feat and "log" not in feat and "decimal" not in feat:
            # Log-normal transaction amounts ($1 – $5000, mode ~$50)
            vals = rng.lognormal(mean=3.5, sigma=1.2, size=n_rows) * drift_scale
            vals = np.clip(vals, 0.5, 20000)
            data[feat] = vals
        elif feat == "TransactionAmt_log":
            data[feat] = np.log1p(data.get("TransactionAmt", rng.lognormal(3.5, 1.2, n_rows)))
        elif feat == "TransactionAmt_decimal":
            data[feat] = (data.get("TransactionAmt", rng.uniform(0, 1, n_rows)) % 1).round(2)
        elif feat.startswith("card") and feat[4:].isdigit():
            data[feat] = rng.integers(100, 18000, size=n_rows)
        elif feat.startswith("addr"):
            data[feat] = rng.integers(100, 500, size=n_rows).astype(float)
            data[feat][rng.random(n_rows) < 0.10] = np.nan
        elif feat == "dist1":
            vals = rng.exponential(scale=100, size=n_rows) * drift_scale
            vals[rng.random(n_rows) < 0.40] = np.nan
            data[feat] = vals
        elif feat.startswith("C"):
            data[feat] = rng.integers(0, 2500, size=n_rows).astype(float)
        elif feat.startswith("D"):
            vals = rng.integers(0, 500, size=n_rows).astype(float)
            vals[rng.random(n_rows) < 0.30] = np.nan
            data[feat] = vals
        elif feat.startswith("V"):
            vals = rng.normal(loc=0, scale=1, size=n_rows) * drift_scale
            vals[rng.random(n_rows) < 0.20] = np.nan
            data[feat] = vals
        elif feat == "card1_txn_count":
            data[feat] = rng.integers(1, 50, size=n_rows).astype(float)
        elif feat == "card1_amt_mean":
            data[feat] = rng.lognormal(3.5, 1.0, size=n_rows) * drift_scale
        elif feat == "card1_amt_std":
            data[feat] = rng.lognormal(2.5, 1.0, size=n_rows) * drift_scale
        elif feat == "hour_of_day":
            data[feat] = rng.integers(0, 24, size=n_rows)
        elif feat == "day_of_week":
            data[feat] = rng.integers(0, 7, size=n_rows)
        elif feat == "missing_count":
            data[feat] = rng.integers(0, 30, size=n_rows)
        else:
            data[feat] = rng.normal(size=n_rows)

    # --- Categorical features ---
    data["ProductCD"]              = rng.choice(["W", "H", "C", "S", "R"], p=[0.57, 0.22, 0.09, 0.08, 0.04], size=n_rows)
    data["card4"]                  = rng.choice(["visa", "mastercard", "discover", "american express"], p=[0.65, 0.32, 0.02, 0.01], size=n_rows)
    data["card6"]                  = rng.choice(["debit", "credit"], p=[0.77, 0.23], size=n_rows)
    data["P_emaildomain_grouped"]  = rng.choice(["gmail.com", "yahoo.com", "hotmail.com", "other", "anonymous"], p=[0.32, 0.18, 0.10, 0.35, 0.05], size=n_rows)
    data["R_emaildomain_grouped"]  = rng.choice(["gmail.com", "yahoo.com", "hotmail.com", "other", "missing"], p=[0.28, 0.15, 0.09, 0.30, 0.18], size=n_rows)
    data["M4"]                     = rng.choice(["M0", "M1", "M2", float("nan")], p=[0.45, 0.25, 0.15, 0.15], size=n_rows)
    data["M6"]                     = rng.choice(["T", "F", float("nan")], p=[0.65, 0.25, 0.10], size=n_rows)

    return pd.DataFrame(data)


def _load_or_generate(csv_path: Path, label: str, n_rows: int, fraud_rate: float, seed: int, drift: bool) -> pd.DataFrame:
    if csv_path.exists():
        df = pd.read_csv(csv_path)
        logger.info("Loaded %s from %s: %d rows × %d columns", label, csv_path, len(df), df.shape[1])
        return df
    else:
        logger.warning(
            "%s CSV not found at %s — generating synthetic IEEE-CIS-like data (%d rows, fraud_rate=%.1f%%).",
            label, csv_path, n_rows, fraud_rate * 100
        )
        rng = np.random.default_rng(seed)
        df = _generate_synthetic_dataset(n_rows, fraud_rate, rng, drift=drift)
        logger.info("Generated synthetic %s: %d rows × %d columns", label, len(df), df.shape[1])
        return df


# ---------------------------------------------------------------------------
# Core monitoring logic
# ---------------------------------------------------------------------------

def _run_evidently_report(
    reference: pd.DataFrame,
    current: pd.DataFrame,
    numerical_features: list[str],
    categorical_features: list[str],
    target_col: str,
    output_dir: Path,
) -> dict:
    column_mapping = ColumnMapping(
        target=target_col,
        numerical_features=numerical_features,
        categorical_features=categorical_features,
        task="classification",
    )

    report = Report(metrics=[DataDriftPreset()])
    logger.info("Running Evidently drift report (this may take ~30 s)…")
    report.run(reference_data=reference, current_data=current, column_mapping=column_mapping)

    html_path = output_dir / "drift_report.html"
    report.save_html(str(html_path))
    logger.info("HTML drift report saved → %s", html_path)

    result_dict = report.as_dict()

    dataset_drift_result = None
    for metric_entry in result_dict.get("metrics", []):
        r = metric_entry.get("result", {})
        if "dataset_drift" in r:
            dataset_drift_result = r
            break

    dataset_drift = bool(dataset_drift_result.get("dataset_drift", False) if dataset_drift_result else False)
    drift_share   = float(dataset_drift_result.get("drift_share", 0.0) if dataset_drift_result else 0.0)
    n_drifted     = int(dataset_drift_result.get("number_of_drifted_columns", 0) if dataset_drift_result else 0)
    n_features    = int(dataset_drift_result.get("number_of_columns", len(numerical_features) + len(categorical_features)) if dataset_drift_result else len(numerical_features) + len(categorical_features))

    feature_rows = []
    drift_data = dataset_drift_result.get("drift_by_columns", {}) if dataset_drift_result else {}
    for col_name, col_info in drift_data.items():
        feature_rows.append({
            "feature":  col_name,
            "drifted":  bool(col_info.get("drift_detected", False)),
            "stattest": col_info.get("stattest_name", ""),
            "p_value":  col_info.get("p_value", ""),
            "threshold": col_info.get("threshold", ""),
        })

    return {
        "dataset_drift": dataset_drift,
        "drift_share":   drift_share,
        "n_drifted":     n_drifted,
        "n_features":    n_features,
        "feature_results": feature_rows,
    }


def _save_drift_summary_csv(feature_rows: list[dict], output_dir: Path) -> None:
    if not feature_rows:
        pd.DataFrame(columns=["feature", "drifted", "stattest", "p_value", "threshold"]).to_csv(
            output_dir / "drift_summary.csv", index=False)
        return
    df = pd.DataFrame(feature_rows).sort_values("drifted", ascending=False)
    df.to_csv(output_dir / "drift_summary.csv", index=False)
    logger.info("Per-feature drift summary saved → %s", output_dir / "drift_summary.csv")


def _save_drift_status_json(summary: dict, ref_path: Path, curr_path: Path, output_dir: Path, synthetic: bool) -> str:
    drift_share   = summary["drift_share"]
    dataset_drift = summary["dataset_drift"]

    if drift_share >= DRIFT_SHARE_CRITICAL_THRESHOLD:
        status = "critical"
    elif dataset_drift or drift_share >= DRIFT_SHARE_WARNING_THRESHOLD:
        status = "warning"
    else:
        status = "ok"

    payload = {
        "timestamp_utc":          datetime.now(tz=timezone.utc).isoformat(),
        "model":                  "lightgbm",
        "reference_dataset":      str(ref_path),
        "current_dataset":        str(curr_path),
        "synthetic_data_used":    synthetic,
        "dataset_drift_detected": dataset_drift,
        "drift_share":            round(drift_share, 6),
        "n_drifted_features":     summary["n_drifted"],
        "n_monitored_features":   summary["n_features"],
        "overall_status":         status,
        "thresholds":             {"warning": DRIFT_SHARE_WARNING_THRESHOLD, "critical": DRIFT_SHARE_CRITICAL_THRESHOLD},
        "action_required":        status in ("warning", "critical"),
        "recommended_action": (
            "Schedule model retraining — critical drift detected." if status == "critical"
            else "Monitor closely; consider retraining if drift persists." if status == "warning"
            else "No action required."
        ),
    }

    json_path = output_dir / "drift_status.json"
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
    logger.info("Drift status saved → %s  (status=%s)", json_path, status)
    return status


def _resolve_monitored_columns(
    reference_df: pd.DataFrame,
    current_df: pd.DataFrame,
    selected_num: list[str],
    selected_cat: list[str],
) -> tuple[list[str], list[str]]:
    """Maps the real Module 2 selected-feature names onto whatever column
    names are actually present in the reference/current DataFrames.

    The real processed CSVs (data/processed/{train,test}.csv) are the output
    of a scikit-learn ColumnTransformer, which prefixes every output column
    with its step name: numeric features keep their original name 1:1 under
    a `numeric__` prefix, but categorical features are one-hot encoded into
    several `categorical__{feature}_{value}` columns each -- not a 1:1 name
    match (verified directly against the real train.csv header: e.g.
    `card1_amt_mean` -> `numeric__card1_amt_mean`, `ProductCD` ->
    `categorical__ProductCD_W`, `categorical__ProductCD_H`, ...). The
    synthetic-data fallback path uses bare, unprefixed names instead. This
    checks for the real prefixed/expanded form first and falls back to a
    bare-name match for the synthetic case, so both paths monitor the
    correct real columns rather than silently matching almost nothing.
    """
    common_cols = set(reference_df.columns) & set(current_df.columns)

    num_cols: list[str] = []
    for feat in selected_num:
        prefixed = f"numeric__{feat}"
        if prefixed in common_cols:
            num_cols.append(prefixed)
        elif feat in common_cols:
            num_cols.append(feat)

    cat_cols: list[str] = []
    for feat in selected_cat:
        onehot_cols = sorted(c for c in common_cols if c.startswith(f"categorical__{feat}_"))
        if onehot_cols:
            cat_cols.extend(onehot_cols)
        elif feat in common_cols:
            cat_cols.append(feat)

    return num_cols, cat_cols


def run_drift_monitor(
    reference_csv: Path,
    current_csv: Path,
    output_dir: Path,
    feature_manifest: Path = DEFAULT_FEATURE_MANIFEST,
) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)

    synthetic = not reference_csv.exists() or not current_csv.exists()

    reference_df = _load_or_generate(reference_csv, "reference (train)", n_rows=400_000, fraud_rate=_FRAUD_RATE_REF, seed=42, drift=False)
    current_df   = _load_or_generate(current_csv,   "current (production)", n_rows=100_000, fraud_rate=_FRAUD_RATE_CURR, seed=99, drift=False)

    selected_num, selected_cat, used_real_manifest = _load_selected_features(feature_manifest)

    # Determine which monitored columns exist in both DataFrames
    num_cols, cat_cols = _resolve_monitored_columns(reference_df, current_df, selected_num, selected_cat)
    target_col = _TARGET_COL if _TARGET_COL in reference_df.columns else None

    shared_cols = num_cols + cat_cols + ([target_col] if target_col else [])
    ref_subset  = reference_df[shared_cols].copy()
    curr_subset = current_df[shared_cols].copy()

    summary = _run_evidently_report(ref_subset, curr_subset, num_cols, cat_cols, target_col or "isFraud", output_dir)
    _save_drift_summary_csv(summary["feature_results"], output_dir)
    status = _save_drift_status_json(summary, reference_csv, current_csv, output_dir, synthetic)

    print("\n" + "=" * 62)
    print("  DRIFT MONITOR — IEEE-CIS Fraud Detection Pipeline")
    print("=" * 62)
    if synthetic:
        print("  Data source:      Synthetic (processed CSVs not on disk)")
    else:
        print("  Data source:      Real processed CSVs")
    print(f"  Model:            LightGBM (production)")
    print(f"  Feature source:   {'Real Module 2 selection' if used_real_manifest else 'Fallback (manifest not found)'}")
    print(f"  Reference rows:   {len(ref_subset):,}")
    print(f"  Current rows:     {len(curr_subset):,}")
    print(f"  Features checked: {summary['n_features']}")
    print(f"  Drifted features: {summary['n_drifted']}  ({summary['drift_share']:.1%})")
    print(f"  Dataset drift:    {'YES' if summary['dataset_drift'] else 'No'}")
    print(f"  Overall status:   {status.upper()}")
    print(f"  HTML report:      {output_dir / 'drift_report.html'}")
    print("=" * 62 + "\n")

    return 1 if status == "critical" else 0


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Milestone 5 — Production Drift Monitor")
    p.add_argument("--reference", type=Path, default=DEFAULT_REFERENCE_CSV)
    p.add_argument("--current",   type=Path, default=DEFAULT_CURRENT_CSV)
    p.add_argument("--output",    type=Path, default=DEFAULT_OUTPUT_DIR)
    p.add_argument("--features",  type=Path, default=DEFAULT_FEATURE_MANIFEST,
                    help="Path to reports_m2/feature_manifest.json (real Module 2 selected features)")
    return p.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    sys.exit(run_drift_monitor(
        reference_csv=args.reference,
        current_csv=args.current,
        output_dir=args.output,
        feature_manifest=args.features,
    ))
