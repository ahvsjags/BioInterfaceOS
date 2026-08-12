# T057 PRIDE QC and author concordance evidence

## Result

The server now audits all three development-scope PRIDE fixture projects. PXD000001 passed processed QC with 3/3 replicates per arm, FDR 0.0, and observed-intensity fraction 0.875. It is graded `G3_PROCESSED_FIXTURE` because no raw payload was accessed. PXD000002 failed because raw access is restricted and replicate/sample arms are unresolved. PXD000003 failed as locked metadata-only. Both failures remain in the failure ledger.

Three author claims were evaluated against the processed ratio output: one was concordant, one discrepant beyond tolerance, and one unavailable because its project failed QC. Each claim retains a locator, values, tolerance, status, and reason where applicable.

## Validation

```text
PRIDE_QC_VALID attempted=3 processed_passed=1 failed=2 claims=3 concordant=1 discrepant=1 unavailable=1 resumed=0
PRIDE_QC_VALID attempted=3 processed_passed=1 failed=2 claims=3 concordant=1 discrepant=1 unavailable=1 resumed=1
3 focused PRIDE QC tests passed
214 full tests passed
```

The full offline gate also passed UV lock/sync, Ruff, formatting, mypy, Sage search, LFQ, corona harmonization, conversion, PRIDE triage, coverage reporting, Silver and Gold-auto validation, review export, assets, catalog, lockbox, immutable release verification, state validation, compileall, and `git diff --check`.

## Guard results

- Development projects attempted: 3/3.
- Processed QC passed: 1; failed projects: 2.
- Concordance: 1 concordant, 1 discrepant, 1 unavailable.
- Failure ledger: append-only semantics recorded; restricted/locked projects remain explicit.
- Raw payload accessed: false; locked payload accessed: false; live network: false.
- Raw QC status: `NOT_RUN_NO_DOWNLOAD`; no G4 raw claim was promoted.

## Artifacts

- Fixture: `tests/fixtures/omics/pride_qc_fixture.json`, SHA-256 `f731fb816a7956fcea35b8d4b6816ad660673db19248d3b1d287e577dc2ce983`.
- Manifest: `reports/omics/pride_qc/qc_manifest.json`, SHA-256 `903e148257a318e2536966241b6c6f943c001ba0fa14a6ca799c76d97a74281a`.
- Receipt: `reports/omics/pride_qc/qc_receipt.json`, SHA-256 `564ea9777d64149425fe26729d718b7809b662e145e6676bf786fbba00af1c65`.
- Project QC: `reports/omics/pride_qc/project_qc.json`, SHA-256 `e5557012628afc97a4423ef3c21747539a174837539be297f94261678e3ee96e`.
- Author concordance: `reports/omics/pride_qc/author_concordance.json`, SHA-256 `1988d96773a2398f20fffd8d67bb61e39b475af43849f0325c9a51deaa0ea259`.
- Failure ledger: `reports/omics/pride_qc/failure_ledger.json`, SHA-256 `6c24fee8a18796068b6e3c080bf118d8d406939b7c5174e6a9991c13587de2dd`.
- Evidence grades: `reports/omics/pride_qc/evidence_grades.json`, SHA-256 `0ad1eef01c3f5a0a29acecaf9734fd14657aaafaaa5a9d1661e128aaabf44a39`.

This is a fixture-backed audit and deliberately narrows the raw-omics claim to processed evidence.
