"""Tests for worm_storage.py (Milestone 5, Youssef Tarek).

Covers the pure, deterministic logic -- hashing, blob-name derivation, and
extension-filtered file collection -- none of which need real Azure
credentials or network access (the actual upload path is verified
separately via `python worm_storage.py --dry-run` against this project's
real reports_m4/reports_m5/reports/compliance directories).
"""
from pathlib import Path

from worm_storage import _blob_name, _collect_files, _sha256


def test_sha256_is_deterministic_and_matches_known_content(tmp_path) -> None:
    path = tmp_path / "sample.txt"
    path.write_text("hello world", encoding="utf-8")

    # Known SHA-256 of the literal bytes b"hello world" (verified via hashlib directly).
    assert _sha256(path) == "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"


def test_sha256_differs_for_different_content(tmp_path) -> None:
    a = tmp_path / "a.txt"
    b = tmp_path / "b.txt"
    a.write_text("content A", encoding="utf-8")
    b.write_text("content B", encoding="utf-8")

    assert _sha256(a) != _sha256(b)


def test_blob_name_is_prefixed_and_relative_to_source_root_parent() -> None:
    source_root = Path("/repo/reports_m5")
    local_path = source_root / "drift_report.html"

    blob_name = _blob_name(local_path, source_root)

    assert blob_name.startswith("audit-logs/milestone5/")
    assert blob_name.endswith("reports_m5/drift_report.html")


def test_collect_files_only_returns_uploadable_extensions(tmp_path) -> None:
    (tmp_path / "report.md").write_text("# report", encoding="utf-8")
    (tmp_path / "data.csv").write_text("a,b\n1,2", encoding="utf-8")
    (tmp_path / "model.joblib").write_bytes(b"not uploadable")
    (tmp_path / "notes.txt").write_text("plain text", encoding="utf-8")

    files = _collect_files([tmp_path])
    names = {f.name for f in files}

    assert names == {"report.md", "data.csv", "notes.txt"}


def test_collect_files_skips_nonexistent_directories(tmp_path) -> None:
    missing_dir = tmp_path / "does_not_exist"
    files = _collect_files([missing_dir])
    assert files == []
