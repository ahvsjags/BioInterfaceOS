from pathlib import Path

from biointerfaceos.r4_pxd017052_nsclc_biological_ood import R4PXD017052NSCLCBOODWorkflow


def test_pxd017052_nsclc_biological_ood_receipt_is_reproducible() -> None:
    root = Path(__file__).resolve().parents[2]
    summary = R4PXD017052NSCLCBOODWorkflow(
        root,
        root / "data/raw",
        root / "data/raw/r3_uniprot_sequence_features",
        root / "data/raw/r4_candidate_pxd017052_nsclc",
    ).verify()
    assert summary.development_observation_count == 2724
    assert summary.external_observation_count == 17026
    assert summary.external_shared_canonical_protein_count == 34
    assert summary.external_measurement_batch_count == 666
    assert summary.biological_unit_count == 141
    assert summary.model_count == 3
