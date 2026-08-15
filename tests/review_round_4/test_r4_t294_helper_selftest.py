import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RECEIPT = ROOT / "docs" / "review_round_4" / "R4_T294_KAUST_T293_HELPER_SELFTEST_RECEIPT_20260815.json"


def test_t294_helper_selftest_is_bound_to_fixed_tag_without_closing_external_gates():
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))

    assert receipt["status"] == "KAUST_AUTHOR_CONTROLLED_EXTERNAL_HELPER_SELFTEST_VERIFIED"
    assert receipt["tag"] == "v0.1.3-r10.57"
    assert receipt["checkout_commit"] == "3557fac2019e57fd8968cdcf55b106750eafa750"
    assert receipt["execution_summary"]["scientific_submission_ready"] is False
    assert "not a non-author reproduction" in receipt["claim_boundary"]
    assert receipt["artifact_sha256"]["reproduction_run.log"]
