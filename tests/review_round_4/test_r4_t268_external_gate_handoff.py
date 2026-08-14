"""Guard the current external-gate contract against stale release bindings."""

import json
from pathlib import Path

ROOT = Path(__file__).parents[2]


def _json(relative_path: str) -> dict:
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


def test_t268_binds_current_release_and_preserves_gate_boundary() -> None:
    protocol = _json("docs/data/R4_T268_EXTERNAL_GATE_HANDOFF_PROTOCOL_20260815.json")
    release = _json("docs/release/R10_52_DOI_DEPOSIT_METADATA.json")

    assert protocol["fixed_release"]["tag"] == "v0.1.3-r10.52"
    assert protocol["fixed_release"]["source_commit"] == "READ_FROM_DEREFERENCED_IMMUTABLE_TAG"
    public_route = protocol["public_redistributable_common_target_route"]
    assert public_route["row_level_maps_committed"] is True
    assert public_route["laboratory_anchor_count"] == 4
    assert public_route["target_count"] == 7
    assert public_route["observation_count"] == 783
    assert protocol["biological_unit_supplement"]["analysis_only"] is True
    assert all(value is False for value in protocol["current_gate_state"].values())

    assert release["release"]["tag"] == "v0.1.3-r10.52"
    assert "manifest_sha256" in release["release"]
    assert "archive_sha256" in release["release"]
    assert release["doi_archived"] is False
    assert release["scientific_submission_ready"] is False


def test_t268_external_packages_and_helper_are_present() -> None:
    lockbox = _json("docs/data/R4_T268_LOCKBOX_WORK_PACKAGE_20260815.json")
    adoption = _json("docs/data/R4_T268_EXTERNAL_USER_ADOPTION_INTAKE_20260815.json")
    helper = ROOT / "scripts/r4_external_reproduction_r10_52.sh"

    assert lockbox["fixed_release"]["tag"] == "v0.1.3-r10.52"
    assert lockbox["non_author_required"] is True
    assert lockbox["current_gate_state"]["independent_validation"] is False
    assert adoption["fixed_release"]["tag"] == "v0.1.3-r10.52"
    assert adoption["minimum_claim_count"] == 2
    assert adoption["current_count"] == 0
    assert helper.exists()
    assert "verify-r4-t250-four-lab-common-target --strict" in helper.read_text(encoding="utf-8")
