# T129 PRIDE API candidate-discovery log

**Decision class:** `DEVELOPMENT_OBSERVATION`; exploratory source screening,
not an empirical result or a model input.

**Screened on:** 2026-08-13.  **Development cutoff:** 2024-12-31T23:59:59Z.

## Reproducible search scope

The official PRIDE Archive v2 `search/projects` endpoint was queried with
`page=0&pageSize=100` for `protein corona` (77 records), `nanoparticle corona`
(5), `liposome corona` (0) and `plasma corona` (2), yielding 80 distinct
project accessions before eligibility filtering.  A record was retained for
manual asset screening only when the official project response reported
`Creative Commons Public Domain (CC0)`, `Homo sapiens (human)`, a publication
date no later than the cutoff, and a protein-corona or nanoparticle-plasma
context.  This is a discovery screen; it is not evidence that every retained
record has an admissible target.

The PRIDE API guide documents project, project-file and MSRun-metadata
resources, but no separate project-level sample-design resource.  Candidate
file listings and project protocols therefore cannot be promoted to a
biological analysis-unit map unless an official released asset explicitly
joins the source file or result to numeric covariates.

## High-priority listing screen

The following records describe multiple nanoparticles, protein-corona dynamics
or plasma cohorts.  Their official project metadata make them useful leads,
but the explicitly scoped listing inspection below did **not** yield a
source-matched, unit-level numeric covariate map or a reusable common endpoint.

| PRIDE accession | Scoped official evidence inspected | Non-admission finding | Current decision |
| --- | --- | --- | --- |
| PXD017052 | Project protocol describes a five-nanoparticle plasma workflow. A subsequent complete official archive-index review found acquisition streams, four large search archives and `README.txt` (984,586 bytes; SHA-256 `30d06d8c90e73f4e8086ed6685c8be76f7ec2ab3bb6dacf51a35ae6f73e040f7`). The README schema is only `ID`, `NAME`, `URI`, `TYPE`, `MAPPINGS`: it links search archives to raw acquisition IDs, not to sample roles, materials or numeric covariates. | Raw acquisition labels and archive-to-raw mappings cannot establish biological units or numeric nanoparticle covariates. | `NOT_ADMITTED_WITH_SCREENED_LISTING` |
| PXD022285 | Project description states a five-nanoparticle panel and physicochemical selectivity; the first two 100-file listing pages contained raw/WIFF acquisition streams and no mapping-named asset. | A protocol-level panel is not a file-to-unit covariate map. | `NOT_ADMITTED_WITH_SCREENED_LISTING` |
| PXD028634 | The same multi-nanoparticle project description; all 135 listed files across two pages were acquisition streams, with no mapping-named asset. | No released unit-level map was found in the complete file listing. | `NOT_ADMITTED_WITH_SCREENED_LISTING` |
| PXD030327 | **Superseded by [`PXD030327_UNIT_MAP_CORRECTION`](R2_T129_PXD030327_UNIT_MAP_CORRECTION.md).** The earlier first-two-page listing check missed the project-level `Sample_table.xlsx`; the official asset maps 636 unexcluded runs to source-defined NP, P/NP ratio, replicate and incubation-time fields and those runs match matrix columns. | The verified P/NP ratio is an exposure condition, not a numeric material/size covariate; NP labels remain categorical and a cross-lab common endpoint is unavailable. | `NOT_ADMITTED_PENDING_NUMERIC_MATERIAL_COVARIATE_AND_CROSS_LAB_ENDPOINT` |
| PXD042852 | Project protocol describes five proprietary nanoparticles across a large plasma cohort; the first two 100-file pages contained acquisition streams, result fragments and no mapping-named asset. | Proprietary particle descriptions and run identifiers cannot be converted into material features. | `NOT_ADMITTED_WITH_SCREENED_LISTING` |
| PXD048186 | Project protocol describes a zeolite material and plasma workflow; all 175 listed files across two pages were raw or raw-quant outputs, with no sample-design or mapping-named asset. | One material plus raw-quant outputs does not supply a cross-study material target. | `NOT_ADMITTED_WITH_SCREENED_LISTING` |

`NOT_ADMITTED_WITH_SCREENED_LISTING` is deliberately narrow: it says that the
reviewed official metadata and file pages do not meet the gate.  It does not
assert that no relevant evidence exists elsewhere, and it does not authorize
bulk download, author-contact claims, relabelling or model fitting.

## Additional directory-level lead screen

One directory inventory lead was small enough for a bounded asset inspection
but fails the material-covariate gate before it can enter the consolidated
five-candidate T129 synthesis.

| PRIDE accession | Bounded official asset evidence | Non-admission finding | Current decision |
| --- | --- | --- | --- |
| PXD020584 | `README.txt` (18,032 bytes; SHA-256 `b33cf300e9554b9c35f00dacb94f04ac79b30a9c3d4306e01bfef32283a997c6`) links named XLSX search results to BAF files. Two representative official XLSX files (`Sample_1_HS_nascent_THP1.xlsx`, 42,225 bytes, SHA-256 `b53842f7d944e560437b33d1370e5a235023cbcf0c208ad2819e5ba6e655690b`; `Sample_1_RA_nascent_THP1.xlsx`, 30,031 bytes, SHA-256 `5eae25f1888e03d691de2321bdc14fad2f6c0200fac44c9db1ed238059b53cba`) contain protein-identification fields: accession, protein, molecular weight, pI, search score, peptide count, sequence coverage and mass error. | The released fields provide neither a source-matched numeric material/size covariate nor a common cross-study quantitative corona endpoint. `Sample`, HS/RA, THP1, nascent/washed/pellet and fraction-like tokens are source/process identifiers, not inferred predictive material features or independent biological units. | `NOT_ADMITTED_BOUNDED_RESULT_ASSET_SCREEN` |

This record preserves a narrowly inspected non-admission decision. It does not
claim that all project files have been exhaustively interpreted and does not
authorize reuse of the named source labels as covariates.

## PXD017052 public source-data recovery route

The high-priority PXD017052 listing screen above remains correct for the CC0
archive itself: the inspected README only links search archives to raw IDs. A
separate first-party article route was therefore audited under T131 without
promoting the source to a target.

- The CC BY Nature Communications article
  [10.1038/s41467-020-17033-7](https://doi.org/10.1038/s41467-020-17033-7)
  explicitly links its Fig. 3--5 proteomics data to PXD017052.  It describes
  three SPIONs with distinct surface chemistries, DLS sizes and zeta potentials,
  assayed as three independent replicates in pooled plasma.
- Four direct publisher assets (Supplementary Information, file description,
  Supplementary Data 1 and Source Data) were subsequently acquired through
  normal HTTPS routes, checksum-verified and parsed under T131. Supplementary
  Data 1 has nine `Intensity` and nine `LFQ intensity` columns whose headers
  exactly match all nine raw-file basenames registered by the PRIDE README for
  `txt3NP.zip`; Source Data separately publishes the three particle-labelled
  replicate triplets and the PDF publishes numeric particle records.
- The public assets do **not** publish an explicit raw/result-unit-to-SPION
  crosswalk. File order, intensity values and replicate grouping are not used as
  a substitute.

**Current decision:** `NOT_ADMITTED_INCOMPLETE_SOURCE_UNIT_TO_PARTICLE_MAP`.
The paper is CC BY, but it is not automatically part of T129's CC0-only cohort.
T131 retains the exact verified records and prohibits inference; no separate
CC-BY candidate cohort is created. This still would not establish the required
second independent laboratory or frozen common endpoint.

## Relation to existing T129 evidence

PXD016229 and PXD054751 remain in the immutable admission receipt; PXD053359
and PXD050779 remain in the separate immutable discovery receipt.  This log
does not alter either receipt or their hashes.  It only documents why further
metadata-first screening did not justify a T121 amendment.

## Required evidence before reassessment

1. An official, reusable asset that maps every result or raw-file unit to
   source-defined biological/technical roles and numeric material or size
   covariates.
2. A common, explicitly processed protein-corona endpoint across at least two
   independent laboratories; author result scales must not be concatenated.
3. A versioned T121 amendment freezing units, endpoint, features, splits,
   negative controls and code hashes before any model, ablation, OOD or
   independent-evaluator workflow.
