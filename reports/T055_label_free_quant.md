# T055 label-free quantification evidence

## Result

The server now quantifies the accepted T054 proteins through a bounded, deterministic LFQ workflow. It validates the T054 search receipt and protein output hashes, requires independent biological replicates, preserves raw and normalized matrices, compares two declared normalization routes, retains missingness and contaminants, and keeps ambiguous protein groups visible.

The fixture has 4 runs: two control and two treated runs, with 2 biological replicates per condition. Two proteins are quantifiable. There are 4 groups: 2 unique quantifiable groups, 1 shared ambiguous group, and 1 contaminant group. One non-contaminant cell is missing and is not imputed.

The primary declared-run-scaling route recovered 2/2 expected ratios: `P0SPIKE1` observed `2.0` versus expected `2.0`, and `P0SPIKE2` observed `1.88235294` versus expected `1.88`. The median-centering comparison output is retained for QC and is not substituted silently for the primary route.

## Validation

```text
LFQ_VALID runs=4 samples=2 proteins=2 groups=4 missing_cells=1 contaminant_groups=1 ratios=2/2 resumed=0
LFQ_VALID runs=4 samples=2 proteins=2 groups=4 missing_cells=1 contaminant_groups=1 ratios=2/2 resumed=1
3 focused LFQ tests passed
208 full tests passed
```

The full offline gate also passed UV lock/sync, Ruff, formatting, mypy, Sage search, conversion, PRIDE triage, coverage reporting, Silver and Gold-auto validation, review export, assets, catalog, lockbox, immutable release verification, state validation, compileall, and `git diff --check`.

## Artifacts

- Fixture: `tests/fixtures/omics/quantification_fixture.json`, SHA-256 `9708e5a8709adaaad6832c24014e64a4331823942722d13d01c5792be26d37b3`.
- Manifest: `reports/omics/quantification/quantification_manifest.json`, SHA-256 `3c3d3e4432ae01768d21be91d193e0a1506c9bc81f8a6ed97d580f6db0176e9a`.
- Receipt: `reports/omics/quantification/quantification_receipt.json`, SHA-256 `35e9ecbf1d76ec4b48aba4bd6fe82dfeb11ab146fb36de7278091b4f9cde78cc`.
- Raw matrix: `reports/omics/quantification/raw_matrix.json`, SHA-256 `e77f2630d32559554a8a3ee0a96954c80e1e985917de7da5b065b2e947366801`.
- Normalized matrix: `reports/omics/quantification/normalized_matrix.json`, SHA-256 `ccd3ffc032776cb0a79ff1789b968fcfff3d884868129d267cfc823a21b6c7b7`.
- Protein groups: `reports/omics/quantification/protein_groups.json`, SHA-256 `44d94dea53dda5277742d66e3cab2e1db414ba98cd3f2aee1816027a4c019726`.
- Missingness: `reports/omics/quantification/missingness_report.json`, SHA-256 `c9c28cbfef3d8b8995698d803fe4973d20d370bf78bd05a3fc5e954fbfede84e`.
- Ratio recovery: `reports/omics/quantification/ratio_recovery.json`, SHA-256 `e85cf01aea21b3fad20404cc152a79ff4654b595ff21786ddf1e17a081c883b3`.

The fixture is intentionally offline and lower-grade: it supports testing the quantification contracts and QC behavior, not live-study biological conclusions.
