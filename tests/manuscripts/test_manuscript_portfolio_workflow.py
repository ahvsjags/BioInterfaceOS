"""Regression tests for the R2 merged manuscript and protocol portfolio audit."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from biointerfaceos.manuscript_portfolio_workflow import (
    ManuscriptPortfolioError,
    ManuscriptPortfolioWorkflow,
)

ROOT = Path(__file__).resolve().parents[2]


def test_portfolio_keeps_r2_manuscripts_protocol_only(tmp_path: Path) -> None:
    workflow = ManuscriptPortfolioWorkflow(ROOT, output_root=tmp_path / "portfolio")

    summary = workflow.run(strict=True)

    assert summary.manuscript_count == 2
    assert summary.protocol_figure_count == 3
    assert summary.legacy_withdrawal_count == 15
    assert summary.status == "BLOCKED_R2_MANUSCRIPTS_PENDING_T123_T124"
    receipt = json.loads(summary.receipt_path.read_text(encoding="utf-8"))
    assert receipt["t140_pair_rescreen_candidate_source_count"] == 2
    assert receipt["t140_pair_rescreen_independent_laboratory_count"] == 2
    assert receipt["t140_pair_rescreen_admissible_target_count"] == 0
    assert workflow.verify() == summary


def test_portfolio_requires_strict_mode(tmp_path: Path) -> None:
    workflow = ManuscriptPortfolioWorkflow(ROOT, output_root=tmp_path / "portfolio")

    with pytest.raises(ManuscriptPortfolioError, match="requires --strict"):
        workflow.run()


def test_portfolio_rejects_a_missing_protocol_boundary(tmp_path: Path) -> None:
    root = tmp_path / "repository"
    required_paths = [
        "docs/manuscripts/R2_MANUSCRIPT_PORTFOLIO.json",
        "docs/manuscripts/R2_PAPER_AB_PROTOCOL_OUTLINE.md",
        "docs/manuscripts/R2_PAPER_C_PROTOCOL_OUTLINE.md",
        "docs/data/R2_INDEPENDENT_EVALUATION_PROTOCOL.json",
        "docs/literature/R2_MANUSCRIPT_COMPARATOR_MAP.json",
        "reports/review_round_2/empirical_provenance/v1.1.0/audit_receipt.json",
        "reports/review_round_2/real_benchmark/v1.1.0/benchmark_receipt.json",
        "reports/review_round_2/submission_figures/v1.2.0/figure_manifest.json",
        "reports/review_round_2/submission_figures/v1.2.0/withdrawal_ledger.json",
        "reports/review_round_2/related_work/v1.1.0/related_work_receipt.json",
        "reports/review_round_2/real_model_compatibility/v1.1.0/compatibility_receipt.json",
        "reports/review_round_2/real_proteomics_result_profile/v1.0.0/result_profile_receipt.json",
        "reports/review_round_2/cc0_target_admission/v1.0.0/target_admission_receipt.json",
        "reports/review_round_2/cc0_target_discovery/v1.0.0/target_discovery_receipt.json",
        "reports/review_round_2/t129_current_target_evidence/v1.3.0/current_target_evidence_receipt.json",
        "reports/review_round_2/pxd017052_source_data/v1.0.0/pxd017052_source_data_receipt.json",
        "reports/review_round_2/independent_evaluation/v1.0.0/readiness_receipt.json",
        "release/manuscripts/paper_a/paper_a.md",
        "release/manuscripts/paper_b/paper_b.md",
        "release/manuscripts/paper_c_prelock/paper_c_prelock.md",
    ]
    for relative in required_paths:
        source = ROOT / relative
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    outline = root / "docs/manuscripts/R2_PAPER_AB_PROTOCOL_OUTLINE.md"
    outline.write_text(
        outline.read_text(encoding="utf-8").replace(
            "T123 found\nzero compatible cross-study targets.", "T123 is pending."
        ),
        encoding="utf-8",
    )

    workflow = ManuscriptPortfolioWorkflow(root, output_root=root / "portfolio")

    with pytest.raises(ManuscriptPortfolioError, match="weakens a protocol boundary"):
        workflow.run(strict=True)


def test_portfolio_rejects_tampered_current_t129_receipt(tmp_path: Path) -> None:
    root = tmp_path / "repository"
    shutil.copytree(ROOT / "docs", root / "docs")
    shutil.copytree(ROOT / "reports/review_round_2", root / "reports/review_round_2")
    shutil.copytree(ROOT / "release/manuscripts", root / "release/manuscripts")
    receipt = root / (
        "reports/review_round_2/t129_current_target_evidence/v1.3.0/"
        "current_target_evidence_receipt.json"
    )
    receipt.chmod(0o600)
    payload = json.loads(receipt.read_text(encoding="utf-8"))
    payload["candidate_source_count"] = 4
    receipt.write_text(json.dumps(payload), encoding="utf-8")
    workflow = ManuscriptPortfolioWorkflow(root, output_root=root / "portfolio")

    with pytest.raises(ManuscriptPortfolioError, match="T123/T124/T129 evidence state"):
        workflow.run(strict=True)


def test_portfolio_rejects_tampered_receipt(tmp_path: Path) -> None:
    output_root = tmp_path / "portfolio"
    workflow = ManuscriptPortfolioWorkflow(ROOT, output_root=output_root)
    workflow.run(strict=True)
    receipt_path = output_root / "portfolio_receipt.json"
    receipt_path.chmod(0o600)
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["scientific_submission_ready"] = True
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")

    with pytest.raises(ManuscriptPortfolioError, match="accounting is invalid"):
        workflow.verify()
