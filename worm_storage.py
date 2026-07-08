"""
Milestone 5 — WORM (Write-Once Read-Many) Audit Storage
IEEE-CIS Fraud Detection Pipeline

Uploads compliance and fairness audit reports to Azure Blob Storage with an
immutability policy (time-based retention, 365 days) and a legal hold tag set.
This satisfies GDPR Article 5(e) / HIPAA §164.316 requirements for tamper-proof
audit trails; once locked, no party (including storage account owners) can
delete or modify the blobs during the retention window.

What gets uploaded
------------------
All files in reports_m5/, reports_m4/, and reports/ matching the configured
extensions (.md, .csv, .json, .html) are uploaded.  The CI/CD workflow calls
this script after a successful drift-monitoring run.

Azure prerequisites
-------------------
1. A storage account with versioning + immutable blob storage enabled.
2. A container with a time-based retention policy already created (Azure Portal
   → Storage account → Data management → Immutable blob storage).
3. The following environment variables set (injected as GitHub Actions secrets):
       AZURE_STORAGE_ACCOUNT_NAME    e.g. "fraudauditstore"
       AZURE_STORAGE_CONTAINER_NAME  e.g. "worm-audit-logs"
       AZURE_STORAGE_CONNECTION_STRING  (or use DefaultAzureCredential instead)
4. Optionally: AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET for
   service-principal-based auth via DefaultAzureCredential.

Usage
-----
    python worm_storage.py [--dry-run]

    --dry-run : list files that would be uploaded without actually uploading.

Install deps
------------
    pip install azure-storage-blob azure-identity
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("worm_storage")

# ---------------------------------------------------------------------------
# Project root paths.
# ---------------------------------------------------------------------------
# This script lives at the repo root, so its own directory IS the project
# root -- no machine-specific absolute path needed.
_GRADPROJ_ROOT = Path(__file__).resolve().parent

# Directories whose audit files we upload to WORM storage.
#
# NOTE: originally this listed `reports_m4` under the assumption it held
# Milestone 4 (Compliance QA, Farida)'s audit reports -- but in this repo's
# actual layout, `reports_m4/` is Module 4 (Differential Privacy)'s output
# directory (a different thing, using this project's internal Module-N
# numbering rather than the team's Milestone-N numbering). Farida's real
# compliance deliverables live at `compliance/` -- corrected below. Both
# `reports_m4` (DP privacy-accounting reports, also genuinely compliance-
# relevant under GDPR Article 25) and `compliance/` are included.
AUDIT_SOURCE_DIRS: list[Path] = [
    _GRADPROJ_ROOT / "reports_m5",
    _GRADPROJ_ROOT / "reports_m4",
    _GRADPROJ_ROOT / "compliance",
    _GRADPROJ_ROOT / "reports",     # Milestone 1 security reports (Yara's deliverables)
]

UPLOADABLE_EXTENSIONS: set[str] = {".md", ".csv", ".json", ".html", ".txt", ".docx", ".xlsx"}

# Legal-hold metadata tags applied to every blob.  Azure enforces at least one
# tag for the legal hold to be valid; these tags document the regulatory basis.
LEGAL_HOLD_TAGS: dict[str, str] = {
    "project":     "fraud-detection-ml",
    "milestone":   "milestone5",
    "compliance":  "gdpr-hipaa-iso27001",
    "hold_type":   "worm-audit",
    "uploaded_by": "mlops-pipeline",
}

# Retention in days.  Must match the policy configured on the Azure container.
RETENTION_DAYS = 365

# Blob name prefix inside the container (acts as a folder).
BLOB_PREFIX = "audit-logs/milestone5"

_DEFAULT_CONTAINER_NAME = "worm-audit-logs"


def _resolve_container_name(raw_env_value: str | None) -> str:
    """Resolves AZURE_STORAGE_CONTAINER_NAME, falling back to the default
    whether the env var is absent OR present-but-empty.

    `os.environ.get(key, default)` only applies `default` when `key` is
    absent -- but CI environments (e.g. a GitHub Actions `env:` block mapping
    an unset secret) commonly set the variable present with an empty string,
    which silently defeats a plain `.get(key, default)` call and produces a
    confusing "not set" error even though a sensible default was intended.
    """
    return (raw_env_value or _DEFAULT_CONTAINER_NAME).strip()


def _require_env(name: str) -> str:
    val = os.environ.get(name, "").strip()
    if not val:
        raise EnvironmentError(
            f"Required environment variable '{name}' is not set. "
            "Set it via GitHub Actions secrets or your local shell before running."
        )
    return val


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _collect_files(source_dirs: list[Path]) -> list[Path]:
    """Return all uploadable files under the configured source directories."""
    files: list[Path] = []
    for directory in source_dirs:
        if not directory.exists():
            logger.warning("Source directory does not exist — skipping: %s", directory)
            continue
        for path in sorted(directory.rglob("*")):
            if path.is_file() and path.suffix.lower() in UPLOADABLE_EXTENSIONS:
                files.append(path)
    return files


def _blob_name(local_path: Path, source_root: Path) -> str:
    """
    Derive the blob name from the local path relative to its source root.
    Example:
        local_path  = reports_m5/drift_report.html
        source_root = reports_m5/
        blob_name   = audit-logs/milestone5/reports_m5/drift_report.html
    """
    try:
        rel = local_path.relative_to(source_root.parent)
    except ValueError:
        rel = local_path.name
    # Normalise Windows separators to forward slashes for blob names.
    return f"{BLOB_PREFIX}/{str(rel).replace(chr(92), '/')}"


def _upload_file(
    blob_service_client,
    container_name: str,
    local_path: Path,
    source_root: Path,
    run_timestamp: str,
    dry_run: bool,
) -> dict:
    """Upload a single file and return a manifest row."""
    blob_name = _blob_name(local_path, source_root)
    file_hash = _sha256(local_path)
    file_size = local_path.stat().st_size

    metadata = {
        "source_file":       local_path.name,
        "sha256":            file_hash,
        "upload_timestamp":  run_timestamp,
        "retention_days":    str(RETENTION_DAYS),
        **{f"tag_{k}": v for k, v in LEGAL_HOLD_TAGS.items()},
    }

    if dry_run:
        logger.info("[DRY-RUN] Would upload: %s → %s (%d bytes)", local_path.name, blob_name, file_size)
    else:
        try:
            blob_client = blob_service_client.get_blob_client(
                container=container_name, blob=blob_name
            )
            with open(local_path, "rb") as data:
                blob_client.upload_blob(
                    data,
                    overwrite=True,
                    metadata=metadata,
                    tags=LEGAL_HOLD_TAGS,
                )
            logger.info("Uploaded: %s → %s (%d bytes, SHA-256: %s…)",
                        local_path.name, blob_name, file_size, file_hash[:16])
        except Exception as exc:
            logger.error("Failed to upload %s: %s", local_path.name, exc)
            raise

    return {
        "blob_name":         blob_name,
        "source_file":       str(local_path),
        "file_size_bytes":   file_size,
        "sha256":            file_hash,
        "upload_timestamp":  run_timestamp,
        "dry_run":           dry_run,
    }


def run_worm_upload(dry_run: bool = False) -> int:
    """
    Main upload routine.

    Returns
    -------
    0 — all files uploaded (or dry-run listed) successfully.
    1 — one or more uploads failed.
    """
    # ---- Import Azure SDK -------------------------------------------------
    try:
        from azure.storage.blob import BlobServiceClient
        from azure.identity import DefaultAzureCredential
    except ImportError:
        logger.critical(
            "Azure SDK not installed. Run: pip install azure-storage-blob azure-identity"
        )
        return 1

    # ---- Resolve credentials ----------------------------------------------
    connection_string = os.environ.get("AZURE_STORAGE_CONNECTION_STRING", "").strip()
    account_name      = os.environ.get("AZURE_STORAGE_ACCOUNT_NAME", "").strip()
    container_name    = _resolve_container_name(os.environ.get("AZURE_STORAGE_CONTAINER_NAME"))

    if not container_name:
        logger.error("AZURE_STORAGE_CONTAINER_NAME is not set.")
        return 1

    if dry_run:
        blob_service_client = None
        logger.info("DRY-RUN mode — no blobs will be uploaded.")
    elif connection_string:
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        logger.info("Using connection string for Azure authentication.")
    elif account_name:
        credential = DefaultAzureCredential()
        blob_service_client = BlobServiceClient(
            account_url=f"https://{account_name}.blob.core.windows.net",
            credential=credential,
        )
        logger.info("Using DefaultAzureCredential for account '%s'.", account_name)
    else:
        logger.error(
            "No Azure credentials found. Set AZURE_STORAGE_CONNECTION_STRING "
            "or AZURE_STORAGE_ACCOUNT_NAME + DefaultAzureCredential env vars."
        )
        return 1

    # ---- Collect files ----------------------------------------------------
    files = _collect_files(AUDIT_SOURCE_DIRS)
    if not files:
        logger.warning("No uploadable files found in %s", AUDIT_SOURCE_DIRS)
        return 0

    logger.info("Found %d files to upload.", len(files))

    # ---- Upload -----------------------------------------------------------
    run_timestamp = datetime.now(tz=timezone.utc).isoformat()
    manifest_rows: list[dict] = []
    failed: list[Path] = []

    for local_path in files:
        # Determine which source root this file belongs to.
        source_root = next(
            (d for d in AUDIT_SOURCE_DIRS if str(local_path).startswith(str(d))),
            local_path.parent,
        )
        try:
            row = _upload_file(
                blob_service_client, container_name, local_path, source_root,
                run_timestamp, dry_run,
            )
            manifest_rows.append(row)
        except Exception:
            failed.append(local_path)

    # ---- Write upload manifest locally ------------------------------------
    manifest_path = _GRADPROJ_ROOT / "reports_m5" / "worm_upload_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_payload = {
        "upload_timestamp_utc": run_timestamp,
        "dry_run": dry_run,
        "container": container_name,
        "blob_prefix": BLOB_PREFIX,
        "retention_days": RETENTION_DAYS,
        "legal_hold_tags": LEGAL_HOLD_TAGS,
        "total_files": len(files),
        "uploaded": len(manifest_rows),
        "failed": len(failed),
        "files": manifest_rows,
    }
    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(manifest_payload, fh, indent=2)
    logger.info("Upload manifest written → %s", manifest_path)

    # ---- Summary ----------------------------------------------------------
    print("\n" + "=" * 60)
    print("  WORM STORAGE UPLOAD — IEEE-CIS Fraud Detection Pipeline")
    print("=" * 60)
    print(f"  Container:       {container_name}")
    print(f"  Blob prefix:     {BLOB_PREFIX}")
    print(f"  Retention:       {RETENTION_DAYS} days (immutable)")
    print(f"  Files uploaded:  {len(manifest_rows)}")
    print(f"  Files failed:    {len(failed)}")
    print(f"  Dry-run:         {dry_run}")
    print(f"  Manifest:        {manifest_path}")
    print("=" * 60 + "\n")

    if failed:
        logger.error("Failed files: %s", [str(f) for f in failed])
        return 1
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Milestone 5 — WORM Audit Storage Uploader")
    parser.add_argument(
        "--dry-run", action="store_true",
        help="List files that would be uploaded without actually uploading."
    )
    args = parser.parse_args()
    sys.exit(run_worm_upload(dry_run=args.dry_run))
