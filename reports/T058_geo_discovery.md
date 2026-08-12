# T058 GEO/SRA discovery evidence

## Result

The server now runs `biointerfaceos omics geo discover --scope development --fixture` against a versioned GEO/SRA discovery fixture and the frozen query matrix. Four candidates were attempted: `GSE12345` and `SRP000001` were eligible processed-file candidates; `GSE99999` was rejected for controlled/credentialed access; and `GSE54321` was retained as metadata-only because no public processed file, dose, or timepoint was verified.

Each candidate retains accession, source, query ID, response hash, paper-family ID, material, biological system, dose/time, public-file URL/checksum, access state, and evidence locator. Three coverage gaps remain explicit; no restricted or credentialed study entered the eligible set.

## Validation

```text
GEO_DISCOVERY_VALID scope=development candidates=4 eligible=2 restricted_rejected=1 metadata_only=1 coverage_gaps=3 resumed=0
GEO_DISCOVERY_VALID scope=development candidates=4 eligible=2 restricted_rejected=1 metadata_only=1 coverage_gaps=3 resumed=1
3 focused GEO discovery tests passed
217 full tests passed
```

The full offline gate also passed UV lock/sync, Ruff, formatting, mypy, Sage search, LFQ, corona harmonization, PRIDE QC, conversion, PRIDE triage, coverage reporting, Silver and Gold-auto validation, review export, assets, catalog, lockbox, immutable release verification, state validation, compileall, and `git diff --check`.

## Guard results

- Query matrix and upstream T020/T026/T051 report hashes verified.
- Eligible candidates: 2; restricted/credentialed rejects: 1; metadata-only: 1.
- Coverage gaps: 3; no imputation.
- Raw downloads: false; locked payload access: false; live network: false.
- Rejection ledger uses append-only semantics and retains the reasons for both non-eligible candidates.

## Artifacts

- Fixture: `tests/fixtures/omics/geo_discovery_fixture.json`, SHA-256 `82f9b68d4d3b074e8e5a7ff5f89476951d9ef9450bd146e034ef201823c3a38b`.
- Manifest: `reports/omics/geo_discovery/geo_discovery_manifest.json`, SHA-256 `d6682eabc6fff23b44867b4e7cc9ae75cc1f229eb7bef99ba31dc1bf47883739`.
- Receipt: `reports/omics/geo_discovery/geo_discovery_receipt.json`, SHA-256 `31af63c1a2da3c1fe44eb9c8c41f36d3989d860835d1fa3765aa57213dc99138`.
- Candidate registry: `reports/omics/geo_discovery/candidate_registry.json`, SHA-256 `74ae772868d732e320a9f4f317858deefa9f8fba45c7acddc5ce379f37f4539d`.
- Eligibility cards: `reports/omics/geo_discovery/eligibility_cards.json`, SHA-256 `0edc2c99026f01943c9831a732f7dc11a41811d25bab79b1a586d00e421b525b`.
- Query receipt: `reports/omics/geo_discovery/query_receipt.json`, SHA-256 `dda0c21f432022940980665b217dbd1c7ba92620decb611306fd67a44c1d9c9b`.
- Rejection ledger: `reports/omics/geo_discovery/rejection_ledger.json`, SHA-256 `81abbe5c10d91fbb733e12dc3a73eea924b6dd56db6a540b5ef0a6ca339cf3ac`.
- Coverage gaps: `reports/omics/geo_discovery/coverage_gaps.json`, SHA-256 `df1745aed106c6a0747ecf948540c12efd6b4548c857e2d61df6f13fdbdac864`.

This is a fixture-backed discovery result; eligible means metadata and processed-file provenance passed, not that a live matrix was downloaded.
