# T054 Sage search evidence

## Result

The server now has a bounded, fixture-backed Sage-style search workflow connected to `biointerfaceos omics search --fixture`. It verifies the frozen T053 mzML input and independent FASTA, records the full search configuration, constructs reverse decoys, computes q-values/FDR, rolls accepted PSMs to peptides and proteins, and checks synthetic spike-in recovery.

The result was 3 PSM candidates: 2 targets and 1 decoy. At the declared 1% target-decoy threshold, 2 target PSMs were accepted, 0 decoys were accepted, estimated FDR was 0.0, and 2 peptides / 2 proteins were reported. Synthetic recovery was 2/2. The input mzML fixture has zero native spectra; therefore this is a toy recovery contract and not a claim about live PRIDE spectra.

## Configuration and provenance

- Engine: Sage-style `fixture-sage-v1`.
- Enzyme: trypsin; missed cleavages: 2.
- Tolerances: 10 ppm precursor and 20 ppm fragment.
- Fixed modification: `Carbamidomethyl[C]`.
- Variable modification: `Oxidation[M]`.
- Database: `uniprot-human-fixture-2026-08`, Homo sapiens, reverse target-decoy with `DECOY_` prefix.
- FASTA SHA-256: `ca365eb053c919982daddca1e046c83bb1f7b0d2ee6270ddf24765a91c68bfed`.
- T053 input SHA-256: `556f2768a34cdbc53e8db91feff6877634b60719f006d67e892d12cba5e7424f`.

## Validation

```text
SAGE_SEARCH_VALID psms=3 accepted_psms=2 peptides=2 proteins=2 target_psms=2 decoy_psms=1 estimated_fdr=0.00000000 recovered_spike_ins=2/2 resumed=0
SAGE_SEARCH_VALID psms=3 accepted_psms=2 peptides=2 proteins=2 target_psms=2 decoy_psms=1 estimated_fdr=0.00000000 recovered_spike_ins=2/2 resumed=1
3 focused Sage tests passed
205 full tests passed
```

The full offline gate passed UV lock/sync, Ruff, formatting, mypy, conversion, PRIDE triage, coverage reporting, Silver and Gold-auto validation, review export, assets, catalog, lockbox, immutable release verification, state validation, compileall, and `git diff --check`.

## Artifacts

- Fixture: `tests/fixtures/omics/search_fixture.json`, SHA-256 `f1c3f7564ee030a21b91485e08a30b4e2580b9be89ed9b7c373e4b001c6bc1fd`.
- FASTA: `tests/fixtures/omics/search/uniprot_human_fixture.fasta`, SHA-256 `ca365eb053c919982daddca1e046c83bb1f7b0d2ee6270ddf24765a91c68bfed`.
- Search manifest: `reports/omics/search/search_manifest.json`, SHA-256 `bc2dc5728330413465d201cfc19f14a2487e5cbe1669b0c0a8de37eb73bfa3e3`.
- Receipt: `reports/omics/search/search_receipt.json`, SHA-256 `70499de81ce4b3d94ef1a7322424abea159d4538f0ffe8c2d55cc86ee9424b688`.
- PSMs: `reports/omics/search/psms.json`, SHA-256 `3ab2668a86fb6242d5aa55e31da5399da9139c2b3b33b1eae0ba823a04368a97`.
- Peptides: `reports/omics/search/peptides.json`, SHA-256 `41dce79c2e7765d8c1e11c938f52760325cf380d1704ea8063add06355dac028`.
- Proteins: `reports/omics/search/proteins.json`, SHA-256 `20b07432f9957a5e9ae3b1ede94d691d45e8231c15838dd3f93be8d14a2d8c62`.
- FDR summary: `reports/omics/search/fdr_summary.json`, SHA-256 `f41822390614be409c0f16a86398de3fa7fec7f0d85be37f14f25978993e6d67`.
- Recovery report: `reports/omics/search/recovery_report.json`, SHA-256 `325664b3a36986548465c0c433e25aa46414748cab1900d8c67adb079dd7aea7`.

The fixture engine is intentionally bounded and offline. It preserves an explicit lower-grade toy result because the converted mzML contains no native spectra and no live Sage/raw-data execution was attempted.
