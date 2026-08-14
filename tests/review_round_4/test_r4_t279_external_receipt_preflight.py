"""Regression tests for the versioned T279 external receipt preflight."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from biointerfaceos.r4_t279_external_receipt_preflight import (
    R4T279ExternalReceiptPreflightWorkflow,
)

ROOT = Path(__file__).resolve().parents[2]


def test_t279_preflight_is_bound_to_r1056_and_current_protocol() -> None:
    workflow = R4T279ExternalReceiptPreflightWorkflow(
        bundle_path=ROOT / "missing-t279-external-bundle.json",
        documents_root=ROOT / "missing-t279-external-documents",
        receipt_out=ROOT / "missing-t279-preflight-receipt.json",
    )
    fixed = workflow.FIXED_RELEASE
    assert workflow.PROTOCOL_ID == "bioif-r4-t279-external-gate-handoff-v1.0.0"
    assert fixed["tag"] == "v0.1.3-r10.56"
    assert fixed["commit"] == "2b5642f480576e70e362a11fcfe4757420e93f80"
    manifest = ROOT / fixed["manifest_path"]
    assert hashlib.sha256(manifest.read_bytes()).hexdigest() == fixed["manifest_sha256"]


def test_t279_template_preserves_closed_gate_boundary() -> None:
    template = json.loads(
        (ROOT / "docs/data/R4_T279_EXTERNAL_RECEIPT_BUNDLE_TEMPLATE.json").read_text(
            encoding="utf-8"
        )
    )
    assert template["submission_state"] == "TEMPLATE_NOT_EVIDENCE"
    assert template["fixed_release"]["tag"] == "v0.1.3-r10.56"
    assert template["fixed_release"]["commit"] == "2b5642f480576e70e362a11fcfe4757420e93f80"
    assert template["scientific_submission_ready"] is False

