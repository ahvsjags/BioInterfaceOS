"""Contract tests for the r10.56 external evidence handoff."""

import json
from pathlib import Path

ROOT = Path(__file__).parents[2]


def test_t279_binds_r1055_and_keeps_external_gates_closed() -> None:
    protocol = json.loads(
        (ROOT / "docs/data/R4_T279_EXTERNAL_GATE_HANDOFF_PROTOCOL_20260815.json").read_text(
            encoding="utf-8"
        )
    )
    fixed = protocol["fixed_release"]
    assert fixed["tag"] == "v0.1.3-r10.56"
    assert fixed["manifest"].endswith("r10.56/release_manifest.json")
    assert fixed["clean_room_helper"] == "scripts/r4_external_reproduction_r10_54.sh"
    assert fixed["receipt_preflight_command"].startswith(
        "uv run biointerfaceos data preflight-r4-t279-external-receipts"
    )
    assert protocol["public_redistributable_common_target_route"]["fit_observation_count_after_t277"] == 671
    assert protocol["public_redistributable_common_target_route"]["collapsed_technical_replicate_group_count"] == 112
    assert all(value is False for value in protocol["current_gate_state"].values())


def test_t279_clean_room_helper_is_fixed_to_r1056() -> None:
    helper = ROOT / "scripts/r4_external_reproduction_r10_54.sh"
    text = helper.read_text(encoding="utf-8")
    assert 'expected_tag="v0.1.3-r10.56"' in text
    assert "verify-r4-t250-four-lab-common-target --strict" in text


def test_t279_lockbox_and_adoption_intakes_bind_the_same_tag() -> None:
    lockbox = json.loads(
        (ROOT / "docs/data/R4_T279_LOCKBOX_WORK_PACKAGE_20260815.json").read_text(
            encoding="utf-8"
        )
    )
    adoption = json.loads(
        (ROOT / "docs/data/R4_T279_EXTERNAL_USER_ADOPTION_INTAKE_20260815.json").read_text(
            encoding="utf-8"
        )
    )
    assert lockbox["fixed_release"]["tag"] == "v0.1.3-r10.56"
    assert adoption["fixed_release"]["tag"] == "v0.1.3-r10.56"
    assert lockbox["fixed_release"]["tag_target_commit"] == "2b5642f480576e70e362a11fcfe4757420e93f80"
    assert adoption["fixed_release"]["tag_target_commit"] == "2b5642f480576e70e362a11fcfe4757420e93f80"
    assert lockbox["current_gate_state"]["independent_validation"] is False
    assert adoption["current_count"] == 0
