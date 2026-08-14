"""Verify the frozen T275 T250 replicate-sensitivity audit."""

from pathlib import Path

from biointerfaceos.r4_t275_t250_replicate_sensitivity import R4T275T250ReplicateSensitivityWorkflow

if __name__ == "__main__":
    report = R4T275T250ReplicateSensitivityWorkflow(Path.cwd()).verify(strict=True)
    print(report["audit_id"])
