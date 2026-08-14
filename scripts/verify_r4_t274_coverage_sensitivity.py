"""Verify the frozen T274 coverage sensitivity audit from a repository checkout."""

from pathlib import Path

from biointerfaceos.r4_t274_coverage_sensitivity import R4T274CoverageSensitivityWorkflow

if __name__ == "__main__":
    report = R4T274CoverageSensitivityWorkflow(Path.cwd()).verify(strict=True)
    print(report["audit_id"])
