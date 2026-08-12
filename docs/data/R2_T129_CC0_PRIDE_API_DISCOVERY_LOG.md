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
