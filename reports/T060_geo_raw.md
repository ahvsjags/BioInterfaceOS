# T060 GEO raw RNA-seq evidence

## Result

The server now runs `biointerfaceos omics geo process --mode raw --fixture` for one explicitly public, credential-free, manageable raw-study fixture. The workflow uses a versioned toy reference and a declared paired-end exact-gene counting rule. It recovers the declared counts without downloading live SRA/FASTQ data and keeps unmatched pairs visible in QC.

The study contains four samples with two biological replicates per condition, 18 read pairs, 16 matched pairs, 2 unmatched pairs, and 2 reference genes. Treated/control mean counts for `GENE1` recover a 2.0 ratio; `GENE2` remains 1.0 in the fixture. Raw counts remain study-local and are not merged with the T059 processed matrices.

## Validation

```text
GEO_PROCESS_VALID mode=raw studies_attempted=1 studies_passed=1 excluded_studies=0 genes=2 samples=4 pairs=18 matched_pairs=16 unmatched_pairs=2 resumed=0
GEO_PROCESS_VALID mode=raw studies_attempted=1 studies_passed=1 excluded_studies=0 genes=2 samples=4 pairs=18 matched_pairs=16 unmatched_pairs=2 resumed=1
3 focused GEO raw-processing tests passed
223 full tests passed
```

The offline gate also passed UV lock/sync, Ruff, formatting, mypy, assets, catalog, lockbox self-test, immutable release verification, state validation, compileall, and `git diff --check`.

## Guard results

- The fixture declares `PUBLIC`, `credential_required=false`, and `manageable=true`; the implementation rejects violations before counting.
- Source checksum material and reference checksum material are verified before reads are counted.
- Reference version `toy-ref-v1` and paired-end exact-gene counting are recorded in every study/QC/receipt path.
- Unmatched pairs are retained as explicit QC (`2/18`) rather than silently assigned.
- No live network, credential, locked payload, or raw external payload was accessed. No cross-study batch merge occurred.

## Artifacts

- Implementation commit: `666719b`.
- Fixture: `tests/fixtures/omics/geo_raw_fixture.json`, SHA-256 `100fd9d1c70acb445fe29d525b50126933f1c83819a9caf5110bf08b4f2ffb44`.
- Raw counts: `reports/omics/geo_raw/raw_counts.json`, SHA-256 `d381f4042d52fad2ac63fea05be6877eb60c41174299cb6543207d2d0c2d2755`.
- Sample metadata: `reports/omics/geo_raw/sample_metadata.json`, SHA-256 `b4c446a5cd378d8abae5f5f2fac871e4a075d699d17ef8aca5cb58743ddde683`.
- Within-study QC: `reports/omics/geo_raw/within_study_qc.json`, SHA-256 `c1720e43ec9ba7c0bc239c9cc28b0564a61fc253d73a2aa42ee8f6d61855de4c`.
- Contrast summaries: `reports/omics/geo_raw/contrast_summaries.json`, SHA-256 `1819b47b5a2320d3955a393e4129091f23a44ff366215a67c54c3e5baf971a4d`.
- Processing receipt: `reports/omics/geo_raw/processing_receipt.json`, SHA-256 `d83c419b285f89bc6ce2612e7607ea643aef7cf67be0765bba384a9092b236e6`.
- Processing manifest: `reports/omics/geo_raw/processing_manifest.json`, SHA-256 `db1c87fcc6087701e3cbac6716c8a70cce64b42086ccf63a8a47ea4c52980dcb`.

The first run created deterministic outputs and the second returned `resumed=1` without changing receipt bytes.
