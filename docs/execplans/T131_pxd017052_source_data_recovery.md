# T131: PXD017052 CC-BY source-data recovery and mapping audit

## Purpose

Assess the most information-rich unadmitted route without confusing a public
article description with a verified data table.  The CC-BY Nature
Communications article [10.1038/s41467-020-17033-7](https://doi.org/10.1038/s41467-020-17033-7)
links its protein-corona analyses to PRIDE `PXD017052`, reports three
characterized SPIONs (`SP-003`, `SP-007`, `SP-011`) and three assay replicates,
and has a CC-BY NCBI OA record.  T131 must determine whether the released XLSX
assets actually join those particle properties and quantitative protein results
to declared PRIDE source units.

## Audited evidence and result

| Evidence | Verified fact | Limitation |
| --- | --- | --- |
| Nature Communications article | CC BY 4.0; Supplementary Table 1 records numeric DLS size, PDI and zeta potential for SP-003, SP-007 and SP-011. The rendered source page was visually checked. | The table records particle attributes, not a PRIDE file-to-particle crosswalk. |
| Four direct publisher assets | Supplementary Information, supplementary-file description, Supplementary Data 1 and Source Data were downloaded through normal HTTPS routes to protected raw storage. Each has matching byte count, SHA-256 and MD5/ETag evidence. | Raw source files are deliberately not committed and are not copied into the public package. |
| Supplementary Data 1 and PRIDE `PXD017052` | All nine `Intensity` and `LFQ intensity` headers exactly match the basenames of the nine raw files listed under `txt3NP.zip` in the official PRIDE README. | The result-to-raw join does not name SP-003, SP-007 or SP-011. |
| Source Data Figure 3A | The workbook publishes three particle-labelled triplets, with assay replicates 1--3 for SP-003-001, SP-007-002 and SP-011-001. | It does not include any of the nine PRIDE raw/result IDs, so grouping/order cannot bridge the two tables. |

The strict audit receipt is
`VERIFIED_PUBLIC_ASSETS_INCOMPLETE_SOURCE_UNIT_TO_PARTICLE_MAP`: it verifies
the publisher assets, material records and all nine result-to-raw joins, while
recording zero explicit raw-to-particle joins. The source is not admitted.

## Completed recovery and audit procedure

1. The following original publisher files were downloaded without renaming to
   ignored raw storage and verified before parsing:

   - `41467_2020_17033_MOESM1_ESM.pdf`
   - `41467_2020_17033_MOESM2_ESM.docx`
   - `41467_2020_17033_MOESM3_ESM.xlsx`
   - `41467_2020_17033_MOESM12_ESM.xlsx`

2. The audit records byte count, SHA-256, local MD5 and publisher ETag, then
   checks the `Sheet1`, `Figure 3A`, and `Figure 2 DLS` workbook schemas.
3. The audit evaluates each required join without filling gaps:

   ```text
   PRIDE result/raw unit -> source-defined quantitative protein-corona column: VERIFIED
   SP-003/SP-007/SP-011 -> numeric size/charge/material fields: VERIFIED
   PRIDE result/raw unit -> SP-003/SP-007/SP-011: MISSING EXPLICIT CROSSWALK
   ```

4. Keep all CC-BY-derived fields segregated from the T129 CC0-only cohort. A
   separate CC-BY candidate cohort was not created because the unit map is
   incomplete. An explicit amendment would still be required after a complete
   crosswalk is supplied; it cannot substitute for a second laboratory and a
   shared endpoint.

## Acceptance and non-goals

T131 completes a provenance audit: official checksums, workbook schema,
result-to-raw coverage, particle-property records, licence class and a
no-inference decision are recorded. It does **not** establish the missing
raw-to-particle map, fit a model, convert the three replicates into an
independent validation set, or clear T123--T128.

If a future asset supplies the crosswalk, issue a new versioned audit. Do not
infer it from file order, value patterns or replicate order; do not query
authors on behalf of the user or copy article labels into a public CC0 registry.

## Scope correction and completion note

The v1.0 receipt is correct for its four checksum-verified, explicitly scoped
assets, but its statement that no *released* crosswalk was available was too
broad. On 2026-08-13, a normal publisher listing review identified
Supplementary Data 6 (`MOESM8`), outside the v1.0 asset inventory. Its first
section appears to name the same nine result units beside particle identifiers
and replicate numbers. T132 is opened to checksum and parse the complete
remaining publisher attachment set, verify that apparent map against the T131
units, and issue a separate correction receipt. Until that audit succeeds,
T131's negative conclusion is limited to its original four assets.

T131 is complete at its recovery-and-audit scope. The immutable receipt is
`reports/review_round_2/pxd017052_source_data/v1.0.0/`; it records
`NOT_ADMITTED`, `model_use=PROHIBITED`, zero explicit raw-to-particle maps and
false model/OOD/independent-validation fields. It is not the final statement
about uninspected publisher assets.
