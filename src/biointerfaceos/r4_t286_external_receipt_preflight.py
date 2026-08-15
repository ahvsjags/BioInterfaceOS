"""T286 structural preflight for receipts submitted against r10.57.

The inherited validator deliberately stops before authenticating identity,
independence, signatures or scientific claims. Those remain editorial gates
that require real third-party records.
"""

from __future__ import annotations

from biointerfaceos.r4_external_receipt_preflight import (
    R4ExternalReceiptPreflightError,
    R4ExternalReceiptPreflightWorkflow,
)


class R4T286ExternalReceiptPreflightError(R4ExternalReceiptPreflightError):
    """Raised when an r10.57 external receipt bundle is structurally invalid."""


class R4T286ExternalReceiptPreflightWorkflow(R4ExternalReceiptPreflightWorkflow):
    """Preflight all four external roles against the immutable r10.57 candidate."""

    PROTOCOL_ID = "bioif-r4-t286-external-gate-handoff-v1.0.0"
    FIXED_RELEASE = {
        "repository": "https://github.com/ahvsjags/BioInterfaceOS",
        "tag": "v0.1.3-r10.57",
        "commit": "3557fac2019e57fd8968cdcf55b106750eafa750",
        "source_commit": "0d4467a",
        "manifest_path": "release/empirical_candidate_v0.1.3-r10.57/release_manifest.json",
        "manifest_sha256": "a3b6b7c90eb4964e8bef0649d04b819e19ff12f7b2a3da31ea510330f1919d0e",
    }
    STATUS = "STRUCTURALLY_COMPLETE_T286_PENDING_IDENTITY_REVIEW"
