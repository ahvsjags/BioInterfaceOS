"""T260 versioned preflight for external evidence submitted against r10.45.

The inherited structural checks intentionally stop before identity,
independence or scientific-claim acceptance.  This version exists because the
historical R4 preflight is correctly frozen to r10.32 and must not reject a
future receipt merely because the public handoff advanced.
"""

from __future__ import annotations

import hashlib
import subprocess
from collections.abc import Mapping
from pathlib import Path, PurePosixPath

from biointerfaceos.r4_external_receipt_preflight import (
    R4ExternalReceiptPreflightError,
    R4ExternalReceiptPreflightWorkflow,
)


class R4T260ExternalReceiptPreflightError(R4ExternalReceiptPreflightError):
    """Raised when an r10.45 external receipt bundle is structurally invalid."""


class R4T260ExternalReceiptPreflightWorkflow(R4ExternalReceiptPreflightWorkflow):
    """Preflight all four external roles against the r10.45 handoff."""

    PROTOCOL_ID = "bioif-r4-t260-external-gate-handoff-v1.0.0"
    FIXED_RELEASE = {
        "repository": "https://github.com/ahvsjags/BioInterfaceOS",
        "tag": "v0.1.3-r10.45",
        "commit": "243f3baf0d85bf62eb41f1698b1211478e81594d",
        "source_commit": "243f3baf0d85bf62eb41f1698b1211478e81594d",
        "manifest_path": "docs/data/R4_T260_EXTERNAL_GATE_HANDOFF_PROTOCOL_20260814.json",
        "manifest_sha256": "47a30b3c26d14dbecc44d788f71a591563a09837d78e0d737943810e36e31208",
    }
    STATUS = "STRUCTURALLY_COMPLETE_T260_PENDING_IDENTITY_REVIEW"

    def _assert_repository_anchor(self, fixed_release: Mapping[str, str]) -> None:
        """Verify the tag and T260 protocol bytes without old manifest semantics."""

        if self.repository_root is None:
            return
        try:
            actual_commit = subprocess.check_output(
                ["git", "rev-parse", f"{fixed_release['tag']}^{{}}"],
                cwd=self.repository_root,
                text=True,
                stderr=subprocess.STDOUT,
            ).strip()
        except (OSError, subprocess.CalledProcessError) as exc:
            raise R4T260ExternalReceiptPreflightError(
                "repository root cannot resolve the fixed r10.45 release tag"
            ) from exc
        if actual_commit != fixed_release["commit"]:
            raise R4T260ExternalReceiptPreflightError("repository checkout does not resolve to r10.45")
        raw_path = fixed_release["manifest_path"]
        pure = PurePosixPath(raw_path)
        path = (self.repository_root / Path(*pure.parts)).resolve(strict=False)
        if not path.is_relative_to(self.repository_root) or not path.is_file():
            raise R4T260ExternalReceiptPreflightError("T260 protocol is missing from the fixed release")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != fixed_release["manifest_sha256"]:
            raise R4T260ExternalReceiptPreflightError("T260 protocol hash differs from the fixed release")
