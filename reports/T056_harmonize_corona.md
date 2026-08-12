# T056 protein-corona harmonization evidence

## Result

The server now harmonizes two sanitized project matrices while preserving project-specific scale and batch provenance. It validates T055 receipt/matrix hashes, requires exact species/protein mappings, applies within-sample closure/CLR transforms, emits functional-module sums, and refuses ComBat or outcome leakage.

The fixture produced 2 projects, 4 samples, 2 canonical proteins, and 2 functional modules. One protein cell is missing and remains missing. Project scales `project_relative_abundance_A` and `project_relative_abundance_B` remain attached to their respective rows; numeric values are not treated as directly pooled across projects.

## Validation

```text
HARMONIZE_VALID projects=2 samples=4 proteins=2 modules=2 missing_cells=1 mapping_rows=2 resumed=0
HARMONIZE_VALID projects=2 samples=4 proteins=2 modules=2 missing_cells=1 mapping_rows=2 resumed=1
3 focused harmonization tests passed
211 full tests passed
```

The full offline gate also passed UV lock/sync, Ruff, formatting, mypy, Sage search, LFQ, conversion, PRIDE triage, coverage reporting, Silver and Gold-auto validation, review export, assets, catalog, lockbox, immutable release verification, state validation, compileall, and `git diff --check`.

## Guard results

- Compositional transform: `closure_clr`; composition sums valid.
- Batch correction: `none`; `no_combat=true`.
- Outcome labels used for transform: `false`; `no_outcome_leakage=true`.
- Mapping status: 2 exact rows; no ambiguous mapping was promoted.
- Missingness: 1 explicit cell; no imputation.

## Artifacts

- Fixture: `tests/fixtures/omics/harmonize_corona_fixture.json`, SHA-256 `2a3132a93cc6a648d5bde0cf8a1b6ccd8105e118c505b8e16fe40da556f48c3d`.
- Manifest: `reports/omics/harmonization/harmonization_manifest.json`, SHA-256 `6c30c5c32389da7a04f9b6d160e846899db7dba02e01858999dbbcabde876269`.
- Receipt: `reports/omics/harmonization/harmonization_receipt.json`, SHA-256 `b5ec283bafa299953e58e6a6e25af6351aba9e18ebe9cfacb0d509eda2e1fc14`.
- Project matrix: `reports/omics/harmonization/project_matrix.json`, SHA-256 `ba43e39ad8c32226b0f25c4bda04c192f54040371186612abd485713c721e587`.
- Mapping audit: `reports/omics/harmonization/mapping_audit.json`, SHA-256 `5c9858e17ec7df39faaa9864a7173fa172cde3b269b336c9ea74a9c03ada67de`.
- Module matrix: `reports/omics/harmonization/module_matrix.json`, SHA-256 `898193343321c1220df90f8222c5c50994f75136f88c68a2c7ef595d61f99816`.
- Batch metadata: `reports/omics/harmonization/batch_metadata.json`, SHA-256 `a056d601a9ee9d045030495e14ffc117343d87557c2278ffbbc41d38d9e92fa7`.
- QC: `reports/omics/harmonization/harmonization_qc.json`, SHA-256 `2028edeccdffa5ee0c452f82caf52306c9880431765f415a1dea14bd0cb70a1a`.

This is a sanitized, project-preserving fixture result; it does not claim a live cross-project biological effect.
