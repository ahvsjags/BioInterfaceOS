"""Versioned structural preflight for external evidence submitted against r10.56."""

from __future__ import annotations

from biointerfaceos.r4_external_receipt_preflight import (
    R4ExternalReceiptPreflightError,
    R4ExternalReceiptPreflightWorkflow,
)


class R4T279ExternalReceiptPreflightError(R4ExternalReceiptPreflightError):
    """Raised when an r10.56 external receipt bundle is structurally invalid."""


class R4T279ExternalReceiptPreflightWorkflow(R4ExternalReceiptPreflightWorkflow):
    """Preflight all four external roles against the immutable r10.56 candidate."""

    PROTOCOL_ID = "bioif-r4-t279-external-gate-handoff-v1.0.0"
    FIXED_RELEASE = {
        "repository": "https://github.com/ahvsjags/BioInterfaceOS",
        "tag": "v0.1.3-r10.56",
        "commit": "2b5642f480576e70e362a11fcfe4757420e93f80",
        "source_commit": "1c312fbda54f24325011a79a3a8f0c433140f1d7",
        "manifest_path": "release/empirical_candidate_v0.1.3-r10.56/release_manifest.json",
        "manifest_sha256": "553febabf2d6595dd52545c6b75035e901c20c8ef07b1cb69df4e332aeb4a56d",
    }
    STATUS = "STRUCTURALLY_COMPLETE_T279_PENDING_IDENTITY_REVIEW"
