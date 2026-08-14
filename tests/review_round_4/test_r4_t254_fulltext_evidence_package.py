"""Contract tests for the stratified full-text paper-derived evidence package."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "docs/data/R4_T254_FULLTEXT_PAPER_DERIVED_EVIDENCE_PACKAGE_20260814.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_t254_package_is_bound_to_current_release_and_external_gates_are_false() -> None:
    package = json.loads(PACKAGE.read_text(encoding="utf-8"))
    release = package["release_binding"]
    assert release["tag"] == "v0.1.3-r10.40"
    assert release["commit"] == "05d8073273c18a68896c0fc93b5fd52634378358"
    assert package["primary_estimand"]["route"] == "T238"
    assert package["external_gate_state"] == {
        "protected_non_author_lockbox": False,
        "no_author_scientific_reproduction": False,
        "external_user_adoption": False,
        "doi_immutable_archive_readback": False,
        "scientific_submission_ready": False,
        "promotion_rule": (
            "No internal paper-derived route, CI run, public issue, agent review or "
            "author-run replay can promote an external predicate."
        ),
    }


def test_t238_accounting_and_protocol_hash_are_exact() -> None:
    package = json.loads(PACKAGE.read_text(encoding="utf-8"))
    assert [row["outer_fold_id"] for row in package["target_availability_matrix"]] == [
        "T238_OUTER_01",
        "T238_OUTER_02",
        "T238_OUTER_03",
        "T238_OUTER_04",
    ]
    assert all(len(row["held_out_available_targets"]) == 7 for row in package["target_availability_matrix"])
    t238 = next(item for item in package["execution_strata"] if item["route"] == "T238")
    protocol = ROOT / t238["protocol_path"]
    report = ROOT / t238["report_path"]
    receipt = ROOT / t238["receipt_path"]
    protocol_value = json.loads(protocol.read_text(encoding="utf-8"))
    report_value = json.loads(report.read_text(encoding="utf-8"))
    assert _sha256(protocol) == t238["protocol_sha256"]
    assert _sha256(report) == t238["report_sha256"]
    assert _sha256(receipt) == t238["receipt_sha256"]
    assert report_value["protocol_sha256"] == t238["protocol_sha256"]
    assert protocol_value["scientific_submission_ready"] is False
    assert report_value["accounting"] == {
        "counting_rule": (
            "fold ledger rows include development and held-out rows repeated by outer fold; "
            "held_out_test_observation_count is the non-repeated test-only total"
        ),
        "development_observation_count": 3061,
        "fold_ledger_row_count": 3844,
        "held_out_test_observation_count": 783,
    }


def test_technical_and_analysis_only_routes_keep_unit_boundaries() -> None:
    package = json.loads(PACKAGE.read_text(encoding="utf-8"))
    sources = {row["source_id"]: row for row in package["source_strata"]}
    assert sources["PMC11328176_MULTICORE"]["resolvable_donor_level_independence"] is False
    assert sources["PMC13106918_RCSI_DCU_SILICA_CORONA"]["resolvable_donor_level_independence"] is False
    t177 = next(item for item in package["execution_strata"] if item["route"] == "T177")
    assert t177["biological_unit_count"] == 1
    t209 = next(item for item in package["execution_strata"] if item["route"] == "T209")
    assert t209["public_release_eligible"] is False
    assert t209["paired_full_minus_composition_patient_equal_mean_spearman"] < 0


def test_screen_only_routes_cannot_be_model_evidence() -> None:
    package = json.loads(PACKAGE.read_text(encoding="utf-8"))
    screen_roles = {row["role"] for row in package["source_strata"] if "SCREEN_ONLY" in row["role"]}
    assert screen_roles == {"T184_SOURCE_SCREEN_ONLY", "T246_SOURCE_SCREEN_ONLY"}
    for row in package["source_strata"]:
        if "SCREEN_ONLY" in row["role"]:
            assert row["claim_level"] == "NONE"
