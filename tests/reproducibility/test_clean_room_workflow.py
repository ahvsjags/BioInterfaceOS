import json
from pathlib import Path
from typing import Any, cast

import pytest

from biointerfaceos.clean_room_workflow import CleanRoomError, CleanRoomWorkflow


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def _json(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def test_clean_room_creates_three_agreeing_receipts(tmp_path: Path) -> None:
    workflow = CleanRoomWorkflow(_root(), output_root=tmp_path / "clean-room")
    report = workflow.run(strict=True)
    assert report["independent_runs"] == 3
    assert report["license_safe"] is True
    assert report["network_accessed"] is False
    assert workflow.verify()["result_hash"] == report["result_hash"]
    receipts = [
        _json(tmp_path / "clean-room" / "runs" / f"run_{run_id}" / "receipt.json")
        for run_id in (1, 2, 3)
    ]
    assert len({receipt["package_sha256"] for receipt in receipts}) == 1
    assert len({receipt["result_hash"] for receipt in receipts}) == 1


def test_clean_room_is_one_shot(tmp_path: Path) -> None:
    workflow = CleanRoomWorkflow(_root(), output_root=tmp_path / "clean-room")
    workflow.run(strict=True)
    with pytest.raises(CleanRoomError, match="already executed"):
        workflow.run(strict=True)


def test_clean_room_rejects_forbidden_public_path(tmp_path: Path) -> None:
    workflow = CleanRoomWorkflow(_root(), output_root=tmp_path / "clean-room")
    workflow.FORBIDDEN_PATH_PARTS = (*workflow.FORBIDDEN_PATH_PARTS, "src/")
    with pytest.raises(CleanRoomError, match="forbidden file"):
        workflow._collect_files()


def test_clean_room_rejects_tampered_report(tmp_path: Path) -> None:
    workflow = CleanRoomWorkflow(_root(), output_root=tmp_path / "clean-room")
    workflow.run(strict=True)
    report_path = tmp_path / "clean-room" / "reproduction_report.json"
    report = _json(report_path)
    report["independent_runs"] = 2
    report_path.chmod(0o644)
    report_path.write_text(json.dumps(report), encoding="utf-8")
    with pytest.raises(CleanRoomError, match="status or run count"):
        workflow.verify()


def test_clean_room_excludes_restricted_payload_paths() -> None:
    workflow = CleanRoomWorkflow(_root())
    files = workflow._collect_files()
    names = {path.relative_to(_root()).as_posix() for path in files}
    assert not any(
        "data/locked_test/" in name or "data/raw/" in name or "data/cas/" in name for name in names
    )
