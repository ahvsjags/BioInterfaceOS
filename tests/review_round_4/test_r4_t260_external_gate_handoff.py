"""Regression tests for the current external-gate handoff contract."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_t260_handoff_is_current_and_explicitly_open() -> None:
    protocol_path = ROOT / "docs/data/R4_T260_EXTERNAL_GATE_HANDOFF_PROTOCOL_20260814.json"
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    assert protocol["status"] == "HANDOFF_OPEN_NO_EXTERNAL_RECEIPTS"
    assert protocol["public_release"]["tag"] == "v0.1.3-r10.45"
    assert protocol["public_release"]["doi_status"] == "PENDING_NOT_ARCHIVED"
    assert protocol["no_author_reproduction"]["required_count"] == 1
    assert protocol["external_adoption"]["required_count"] == 2
    assert protocol["protected_lockbox"]["required_count"] == 1
    assert protocol["no_author_reproduction"]["expected_source_sha256"] == (
        "99e472edbb71902f9631e8798fd60b5f1898b1e676affd3fd9376b5302c40008"
    )
    assert all(value is False for value in protocol["current_gate_state"].values())

    helper = (ROOT / "scripts/r4_external_reproduction_r10_45.sh").read_text(encoding="utf-8")
    assert 'expected_tag="v0.1.3-r10.45"' in helper
    assert 'git clone --branch "$expected_tag"' in helper
    assert "curl --fail --location --retry 3" in helper
    assert "uv run biointerfaceos data verify-r4-t258-source-unit-endpoint-license --strict" in helper
    assert "external_receipt_submission_note.txt" in helper

    for relative_path in (
        "docs/external/INDEPENDENT_REPRODUCTION_AND_USER_HANDOFF_R10_45.md",
        "docs/external/LOCKBOX_EVALUATOR_WORK_PACKAGE_R10_45.md",
        "docs/external/EXTERNAL_USER_TASK_CATALOG_R10_45.md",
        "docs/review_round_4/R4_T260_EXTERNAL_GATE_HANDOFF_STATUS_20260814.md",
    ):
        assert (ROOT / relative_path).is_file()
