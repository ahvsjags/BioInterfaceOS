# T059 GEO processed-data evidence

## Result

The server now runs `biointerfaceos omics geo process --mode processed` against the two T058 eligible public processed-file candidates. Both studies passed provenance, metadata, gene-ID normalization, contrast, and within-study QC checks. Study boundaries remain explicit: no cross-study batch merge or outcome-driven correction was performed.

The run produced two study-level expression objects, eight samples, two normalized genes, four auditable contrasts, and zero missing matrix cells. Both conditions had at least two biological replicates. The exclusion ledger is empty because the fixture's two candidate studies passed all declared gates.

## Validation

```text
GEO_PROCESS_VALID mode=processed studies_attempted=2 studies_passed=2 excluded_studies=0 genes=2 samples=8 contrasts=4 missing_cells=0 resumed=0
GEO_PROCESS_VALID mode=processed studies_attempted=2 studies_passed=2 excluded_studies=0 genes=2 samples=8 contrasts=4 missing_cells=0 resumed=1
3 focused GEO processing tests passed
220 full tests passed
```

The final offline gate also passed UV lock/sync, Ruff, formatting, mypy, assets, catalog, lockbox self-test, immutable release verification, state validation, compileall, and `git diff --check`.

## Guard results

- T058 candidate-registry and eligibility-card hashes were verified before ingestion.
- Public-file checksums matched the eligible registry; no restricted or metadata-only candidate was promoted.
- ENTREZ and ENSEMBL IDs were mapped through `fixture-gene-map-v1` to the shared normalized IDs `GENE1` and `GENE2`.
- Sample metadata retain study accession, sample ID, condition, replicate, material, biological system, dose, and time.
- Four expected treated-versus-control directions passed at the declared minimum absolute log2-CPM delta.
- Raw and normalized values, within-study QC, contrasts, receipt, log, and manifest were preserved. No raw download, locked payload access, or live network request occurred.

## Artifacts

- Implementation commit: `5a55064`.
- Fixture: `tests/fixtures/omics/geo_processing_fixture.json`, SHA-256 `9845cf88fd45c9ce1f46abba8ae67d5f09a252965c68f795d33078960ca2c9c6`.
- Study objects: `reports/omics/geo_processing/study_objects.json`, SHA-256 `481d0b4cc48410d299a0034c1910e6d8071cf780ca73b3d5818c24cab1a5a4fc`.
- Sample metadata: `reports/omics/geo_processing/sample_metadata.json`, SHA-256 `acf1fd4bfc9aa38e00f9a9446d41cdf5dc0bcd2fcaa6fe93960a83d6fc696b2a`.
- Normalized matrices: `reports/omics/geo_processing/normalized_matrices.json`, SHA-256 `37a34626cb6dd14b518e7d0225f5ba8f8ef5f89d9bc01c182742528cd9d361c4`.
- Contrast summaries: `reports/omics/geo_processing/contrast_summaries.json`, SHA-256 `6178e17a2d8f77e673f7dff53709770b0e0b55103152e93b7ec9a37ee02f1725`.
- Within-study QC: `reports/omics/geo_processing/within_study_qc.json`, SHA-256 `9dbe2cb9100ecce537427aefdb2d759a60259235ba4f2b4a31ce96b733233701`.
- Exclusion ledger: `reports/omics/geo_processing/exclusion_ledger.json`, SHA-256 `c821905351d6e3e24ab49d098d1ad2af47a8479c2902c5e3ed350d69ebca251b`.
- Processing receipt: `reports/omics/geo_processing/processing_receipt.json`, SHA-256 `3ec1544e8bc94775f22758a3e4bb6374e6db5938f3d9a8df1bd0c826db85ce2c`.
- Processing manifest: `reports/omics/geo_processing/processing_manifest.json`, SHA-256 `bf076fa48f660af13f1725a483abb6553d78d6a96e4d6f86e30e9bc4220f2bbe`.

The first run created deterministic outputs and the second returned `resumed=1` without changing receipt bytes.
