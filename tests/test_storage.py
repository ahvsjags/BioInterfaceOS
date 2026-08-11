"""Tests for deterministic storage accounting and safeguards."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from biointerfaceos.storage import (
    BudgetExceededError,
    OutsideStorageRootError,
    RawDataDeletionError,
    StorageConfig,
    StorageConfigError,
    StorageGuard,
    audit_storage,
    write_json_report,
)


def make_config(root: Path, budget: int = 100) -> StorageConfig:
    config = root / "config.yaml"
    config.write_text(f"budget_bytes: {budget}\nroots: [data, reports]\n", encoding="utf-8")
    return StorageConfig.from_yaml(root, config)


def test_audit_counts_files_and_duplicate_hashes_deterministically(tmp_path: Path) -> None:
    (tmp_path / "data").mkdir()
    (tmp_path / "reports").mkdir()
    (tmp_path / "data/a.txt").write_bytes(b"same")
    (tmp_path / "reports/b.txt").write_bytes(b"same")
    config = make_config(tmp_path)

    first = audit_storage(tmp_path, config)
    second = audit_storage(tmp_path, config)

    assert first == second
    assert first.total_bytes == 8
    assert first.total_files == 2
    assert [usage.files for usage in first.roots] == [1, 1]
    assert first.duplicates[0].paths == ("data/a.txt", "reports/b.txt")
    report_path = tmp_path / "audit.json"
    write_json_report(first, report_path)
    assert json.loads(report_path.read_text(encoding="utf-8"))["manifest_sha256"]


def test_quota_and_containment_denials(tmp_path: Path) -> None:
    (tmp_path / "data").mkdir()
    (tmp_path / "reports").mkdir()
    (tmp_path / "data/existing").write_bytes(b"1234")
    guard = StorageGuard(tmp_path, make_config(tmp_path, budget=5))

    with pytest.raises(BudgetExceededError):
        guard.can_write(Path("data/new"), 2)
    with pytest.raises(OutsideStorageRootError):
        guard.can_write(tmp_path / "elsewhere/new", 1)


def test_config_rejects_root_escape(tmp_path: Path) -> None:
    config = tmp_path / "config.yaml"
    config.write_text("budget_bytes: 1\nroots: [../escape]\n", encoding="utf-8")
    with pytest.raises(StorageConfigError):
        StorageConfig.from_yaml(tmp_path, config)


def test_raw_deletion_is_denied(tmp_path: Path) -> None:
    (tmp_path / "data/raw").mkdir(parents=True)
    (tmp_path / "reports").mkdir()
    guard = StorageGuard(tmp_path, make_config(tmp_path))

    with pytest.raises(RawDataDeletionError):
        guard.deny_delete(Path("data/raw/sample.bin"))


def test_exclusions_and_cleanup_dry_run_do_not_mutate(tmp_path: Path) -> None:
    (tmp_path / "data/.git").mkdir(parents=True)
    (tmp_path / "data/__pycache__").mkdir()
    (tmp_path / "data/raw").mkdir()
    (tmp_path / "reports").mkdir()
    (tmp_path / "data/keep.txt").write_bytes(b"keep")
    excluded = [
        tmp_path / "data/.git/object",
        tmp_path / "data/__pycache__/module.pyc",
        tmp_path / "data/download.tmp",
    ]
    for path in excluded:
        path.write_bytes(b"excluded")
    raw_tmp = tmp_path / "data/raw/download.tmp"
    raw_tmp.write_bytes(b"raw")
    config = make_config(tmp_path)

    report = audit_storage(tmp_path, config)
    candidates = StorageGuard(tmp_path, config).dry_run_cleanup()

    assert [entry.path for entry in report.manifest] == ["data/keep.txt"]
    assert tmp_path / "data/download.tmp" in candidates
    assert tmp_path / "data/__pycache__/module.pyc" in candidates
    assert raw_tmp not in candidates
    assert all(path.exists() for path in excluded + [raw_tmp])
