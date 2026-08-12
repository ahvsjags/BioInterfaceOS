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

## Current evidence and access state

| Evidence | Verified fact | Limitation |
| --- | --- | --- |
| Nature Communications article | CC BY 4.0; three SPIONs have distinct coatings, DLS sizes and zeta potentials; Fig. 3 reports a three-replicate MaxLFQ protein-corona analysis. | Article text and figures are not a checksum-verified source-unit map. |
| PRIDE `PXD017052` | The article's Fig. 3--5 mass-spectrometry results are deposited under this accession; its CC0 archive listing was already screened. | The inspected archive README maps search archives to raw IDs only. |
| NCBI PMC OA metadata | Official EFetch lists `41467_2020_17033_MOESM3_ESM.xlsx` (Supplementary Data 1) and `41467_2020_17033_MOESM12_ESM.xlsx` (Source Data). | Current automated attachment access returns an HTML verification page; the OA package link currently returns HTTPS 404 and FTP traversal denial. |

No workbook has been downloaded, checksummed, or parsed.  The status is
`BLOCKED_OFFICIAL_WORKBOOK_DOWNLOAD_REQUIRED`.

## Exact recovery procedure

1. Through a normal user-completed browser session, download only these two
   official NCBI PMC attachments for PMC7376165:

   - `41467_2020_17033_MOESM3_ESM.xlsx`
   - `41467_2020_17033_MOESM12_ESM.xlsx`

2. Provide the original files to the workspace without renaming them.  T131
   will place them in ignored raw screening storage, calculate SHA-256 and
   record their NCBI locators, byte sizes, workbook sheets and headers.
3. Confirm, from cells rather than article prose, all three joins:

   ```text
   PRIDE result/raw unit -> SP-003/SP-007/SP-011 -> numeric size/charge/material fields
   PRIDE result/raw unit -> source-defined quantitative protein-crown endpoint
   unit -> biological versus technical replicate role
   ```

4. Keep all CC-BY-derived fields segregated from the T129 CC0-only cohort.  A
   later, explicit policy decision is required before creating a separate CC-BY
   public cohort or a T121 amendment.  No decision can substitute for the
   required second independent laboratory and shared endpoint.

## Acceptance and non-goals

T131 passes only a provenance audit: official checksums, workbook schema,
complete unit coverage, licence class and a no-inference decision are recorded.
It does **not** fit a model, convert the article's three replicates into an
independent validation set, or clear T123--T128.

If any file is unavailable, incomplete, lacks the three joins, or is not a
normal publisher-provided download, retain the blocked state.  Do not bypass
browser verification, scrape figures, query authors on behalf of the user, or
copy article labels into a public CC0 registry.
