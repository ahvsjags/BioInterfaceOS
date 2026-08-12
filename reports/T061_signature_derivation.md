# T061 cell and immune response signature evidence

## Result

The server now runs `biointerfaceos omics derive-signatures --fixture` using hash-verified T059 processed expression and T060 raw-count outputs. It derives three signatures across three study objects and twelve samples: two predefined signatures with versioned pathway provenance and one data-driven exploratory factor selected by within-study variance only.

The workflow emits 36 score rows, keeps processed and raw routes auditable, and performs leave-one-study-out stability checks across nine signature/study folds. Eight folds were directionally stable; the one unstable fold remains visible in the stability report rather than being hidden or tuned away.

## Validation

```text
SIGNATURES_VALID studies=3 samples=12 signatures=3 scores=36 stable_folds=8/9 resumed=0 predefined_data_driven_separate=true leakage_passed=true
SIGNATURES_VALID studies=3 samples=12 signatures=3 scores=36 stable_folds=8/9 resumed=1 predefined_data_driven_separate=true leakage_passed=true
3 focused signature tests passed
226 full tests passed
```

The final offline gate also passed UV lock/sync, Ruff, formatting, mypy, assets, catalog, lockbox self-test, immutable release verification, state validation, compileall, and `git diff --check`.

## Guard results

- T059/T060 input artifact hashes are checked before score derivation.
- Predefined signatures retain pathway provenance (`MSigDB-fixture-v1` and `Reactome-fixture-v1`); the data-driven factor is labeled exploratory with separate provenance.
- Data-driven gene selection uses within-study variance and does not use outcome labels. Held-out labels are used only for evaluation.
- Cross-study expression matrices are never batch-merged; comparison is at score/contrast level only.
- No live pathway/network access, raw download, credential, or locked payload access occurred.

## Artifacts

- Implementation commit: `7af5227`.
- Fixture: `tests/fixtures/omics/signature_fixture.json`, SHA-256 `367c991e302faab573027952e3f6d6cf51728f6101d35bfcf82ebd561007261b`.
- Signature registry: `reports/omics/signatures/signature_registry.json`, SHA-256 `9ac758c8282dcf85d19732843e8e656f082fc481d839e72382ac8150aea5ae80`.
- Score matrix: `reports/omics/signatures/signature_scores.json`, SHA-256 `2149be2885cf26bb6d6c92d9a6d175af62bbea03a28880ccd0eeef02d0f01ee0`.
- Stability report: `reports/omics/signatures/stability_report.json`, SHA-256 `9f92b3684f5f767baef9bf86842d4c0fd239af135596e834f6a537c35e465d89`.
- QC report: `reports/omics/signatures/qc_report.json`, SHA-256 `fa4e68a8771dc7db6d2df328231a248874d4eb62a3c15fdaed8e7a4af8b0753f`.
- Leakage audit: `reports/omics/signatures/leakage_audit.json`, SHA-256 `578450384cda9c722e96f48ef3b0d3c350c3c3b893dfbd64a488fcbc55272bdf`.
- Processing receipt: `reports/omics/signatures/processing_receipt.json`, SHA-256 `bd01070a97c681c1104e319ce3b7524186f0017c703bb247ce74208e89a2694e`.

The first run created deterministic outputs and the second returned `resumed=1` without changing receipt bytes.
