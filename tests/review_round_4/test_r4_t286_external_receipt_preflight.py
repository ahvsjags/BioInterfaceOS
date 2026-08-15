"""Regression tests for the r10.57 external receipt preflight."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from biointerfaceos.r4_t286_external_receipt_preflight import (
    R4T286ExternalReceiptPreflightWorkflow,
)

ROOT = Path(__file__).resolve().parents[2]


def test_t286_preflight_is_bound_to_r1057_and_current_manifest() -> None:
    workflow = R4T286ExternalReceiptPreflightWorkflow(
        bundle_path=ROOT / "missing-t286-external-bundle.json",
        documents_root=ROOT / "missing-t286-external-documents",
        receipt_out=ROOT / "missing-t286-preflight-receipt.json",
    )
    fixed = workflow.FIXED_RELEASE
    assert workflow.PROTOCOL_ID == "bioif-r4-t286-external-gate-handoff-v1.0.0"
    assert fixed["tag"] == "v0.1.3-r10.57"
    assert fixed["commit"] == "3557fac2019e57fd8968cdcf55b106750eafa750"
    assert fixed["source_commit"] == "0d4467a"
    canonical = subprocess.check_output(
        ["git", "show", f"{fixed['tag']}:{fixed['manifest_path']}"],
        cwd=ROOT,
    )
    assert hashlib.sha256(canonical).hexdigest() == fixed["manifest_sha256"]


def test_t286_template_preserves_closed_gate_boundary() -> None:
    template = json.loads(
        (
            ROOT / "docs/data/R4_T286_EXTERNAL_RECEIPT_BUNDLE_TEMPLATE_20260815.json"
        ).read_text(encoding="utf-8")
    )
    assert template["submission_state"] == "TEMPLATE_NOT_EVIDENCE"
    assert template["fixed_release"]["tag"] == "v0.1.3-r10.57"
    assert template["fixed_release"]["commit"] == "3557fac2019e57fd8968cdcf55b106750eafa750"
    assert template["scientific_submission_ready"] is False
