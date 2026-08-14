"""Regression tests for the versioned T260 external receipt preflight."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from biointerfaceos.r4_t260_external_receipt_preflight import (
    R4T260ExternalReceiptPreflightWorkflow,
)

ROOT = Path(__file__).resolve().parents[2]


def test_t260_preflight_is_bound_to_current_release_and_protocol() -> None:
    workflow = R4T260ExternalReceiptPreflightWorkflow(
        bundle_path=ROOT / "missing-external-bundle.json",
        documents_root=ROOT / "missing-external-documents",
        receipt_out=ROOT / "missing-preflight-receipt.json",
    )
    fixed = workflow.FIXED_RELEASE
    protocol_path = ROOT / fixed["manifest_path"]
    assert workflow.PROTOCOL_ID == "bioif-r4-t260-external-gate-handoff-v1.0.0"
    assert fixed["tag"] == "v0.1.3-r10.45"
    assert fixed["commit"] == "243f3baf0d85bf62eb41f1698b1211478e81594d"
    assert hashlib.sha256(protocol_path.read_bytes()).hexdigest() == fixed["manifest_sha256"]
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    assert protocol["current_gate_state"] == {
        "protected_lockbox_evaluator_receipt": False,
        "external_scientific_reproduction": False,
        "external_user_adoption": False,
        "doi_archived": False,
        "scientific_submission_ready": False,
    }
