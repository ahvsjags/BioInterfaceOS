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

## Exact-match API additions: license and covariate gates

Two additional official PRIDE API leads were screened after the initial
keyword pass.  Neither changes the consolidated T129 candidate count or its
frozen decision boundary.

| PRIDE accession | Bounded official evidence | Non-admission finding | Current decision |
| --- | --- | --- | --- |
| PXD004441 | The [official project record](https://www.ebi.ac.uk/pride/ws/archive/v3/projects/PXD004441) describes `Interaction of iron oxide nanoparticles with human plasma`, reports *Homo sapiens* and protein-corona/iron-oxide context, but reports its license as `EBI terms of use`. | The T129 admission policy is CC0-only.  A topical record under EBI terms of use cannot enter the cohort; no file-level interpretation was undertaken. | `NOT_ELIGIBLE_NON_CC0_LICENSE` |
| PXD024284 | The [official project record](https://www.ebi.ac.uk/pride/ws/archive/v3/projects/PXD024284) reports CC0 and *Homo sapiens*.  Its official `Experimental_Design.pdf` (145,768 bytes; SHA-256 `663fa3c1195b7a5e44e406dad1379edc3629718976d889666d75a432b8276ca9`) states that standard and treated Nitinol disks were incubated with platelet-poor plasma from three donors.  The official protein table `ProteinMeasurement_PG_hi3_inclSingleHits.xlsx` (770,278 bytes; SHA-256 `66994afa72e4cf0f4d0617f0ad8ceb4fb470e6550d12388a8f4a626b1f28d2a1`) has six abundance columns labelled `S1`--`S3` and `T1`--`T3`; the source labels resolve only to untreated (`NaCl`) versus treated (`Hanks`) disk groups. | The released assets provide a binary treatment contrast but no numeric surface-treatment, size, composition or dose covariate attached to the quantitative units.  The condition labels must not be transformed into a material descriptor. | `NOT_ADMITTED_NO_NUMERIC_MATERIAL_COVARIATE` |

The PXD024284 PDF was visually inspected as a rendered page before its text
and table headers were used.  These checks are limited to the named official
assets and do not claim that undocumented treatment details are absent from
all external sources.

## Follow-up API additions: complete listing and licence gates

Two further exact-accession leads were checked through the official PRIDE v3
project and project-file endpoints.  The checks preserve the same narrow
evidence boundary: a topical title, a licence, or a condition token in a raw
file name is not an analysis-unit-to-numeric-covariate map.

| PRIDE accession | Bounded official evidence | Non-admission finding | Current decision |
| --- | --- | --- | --- |
| PXD007648 | The [official project record](https://www.ebi.ac.uk/pride/ws/archive/v3/projects/PXD007648) reports `Protein Corona of 60nm Silver Nanoparticles`, *Homo sapiens*, publication date 2019-01-23, and licence `EBI terms of use`. | The topical, pre-cutoff record fails T129's CC0-only licence gate.  Its title is not used as a material covariate, and no file-level interpretation was undertaken. | `NOT_ELIGIBLE_NON_CC0_LICENSE` |
| PXD018160 | The [official project record](https://www.ebi.ac.uk/pride/ws/archive/v3/projects/PXD018160) reports CC0, *Homo sapiens*, and publication date 2020-08-19.  Its complete official file-list response at `page=0&pageSize=1000` returns 14 assets (16,873,216,920 bytes): twelve `.baf` raw streams (16,239,725,376 bytes), `2peptidesperprotein.zip` (620,094,058 bytes; API category `Search engine output file URI`) and `SPhumanCr_20170302.fasta` (13,397,486 bytes).  The list has no separately released sample-design, SDRF, annotation, or result-to-unit mapping asset. | The listing exposes only raw-source labels (including `Plasma`, `Fetal` and `Maternal`), a bulk result archive and a FASTA database.  Those labels and the project title cannot be converted into biological units or numeric material/size covariates; no bulk asset was downloaded merely to search for an unstated map.  This does not assert that such evidence is absent inside an uninspected archive or elsewhere. | `NOT_ADMITTED_WITH_SCREENED_LISTING` |

The two API responses were queried on 2026-08-13 using the linked official
project records and `https://www.ebi.ac.uk/pride/ws/archive/v3/projects/PXD018160/files?page=0&pageSize=1000`.
The stated archive-byte accounting comes directly from the returned
`fileSizeBytes` fields; it is not a local transfer receipt.  Neither record
changes the six-source, five-laboratory consolidated T129 candidate synthesis
or authorizes a T121 amendment.

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

**Correction (T132):** This decision is superseded for the complete publisher
attachment set. Checksum-verified Supplementary Data 6 explicitly maps all
nine T131 result/raw unit identifiers to SP-003-001, SP-007-002 or SP-011-001
and a replicate number. The route is now a complete **CC-BY,
single-laboratory** source, not a CC0 target: it remains non-admitted pending
an explicit CC-BY cohort amendment, a second independent laboratory and a
frozen shared endpoint.

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
