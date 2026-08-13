# R4 T188 Multi-Agent Review — PXD064962 CC0 Low-Coverage Source

## Decision

**Conditional accept as a secondary exploratory sensitivity asset; Major Revision for the overall manuscript.**

T188 adds an official PRIDE CC0 metadata snapshot, a row/column-hash-bound MaxQuant table, and an explicit source-cell map. It must not be presented as primary OOD, independent validation, or external scientific reproduction.

## Audited accounting

| Quantity | Verified value | Interpretation |
|---|---:|---|
| Raw source-table cells | 24,300 | 405 protein-group rows × 60 LFQ columns |
| Positive raw source cells | 11,776 | Strictly positive finite LFQ values |
| Expanded target-accession/source-coordinate pairs | 1,260 | Not 1,260 physical cells; target mapping expansion |
| Unique target source coordinates | 1,140 | Physical row/column coordinates represented in the target map |
| Ambiguous target coordinates | 60 | Each maps to three frozen accessions; all are non-positive in this source |
| Positive target-accession pairs | 454 | Positive source value after frozen-target mapping |
| Positive canonical target accessions | 15 | Distinct accessions with at least one positive mapped value |
| Batch × target positive observations | 259 | Detection accounting, not independent sample size |
| Labelled biological units / batches | 30 / 30 | Each batch has two technical replicate columns |
| Shared candidate / qualified batches | 21 / 5 | Five of 30 meet the frozen ≥10-target gate |

## Agent findings

The data auditor accepted the byte-level and row-level traceability but required the distinction between physical coordinates and expanded target pairs, and rejected any claim of 30 independently proven patients beyond the deposited labels.

The statistics reviewer accepted the unchanged primary `≥10` rule and the no-imputation boundary, but found that the optional `≥5` sensitivity is all 30 batches in this source. A future quantitative sensitivity execution must separately report `5–9` and `≥10` coverage strata, freeze technical-replicate aggregation, exclude ambiguous protein-group coordinates unless a new protocol says otherwise, inherit the R3 rank denominator, and use biological-unit—not technical-column—uncertainty.

The handling editor kept the overall decision at Major Revision. T188 raises data compatibility only to approximately **87/100**; it does not raise model/OOD evidence because no model was fitted on T188. The hard gates remain: protected non-author lockbox receipt **4/100**, no-author scientific reproduction **0/100**, external adoption **0/100**, DOI/immutable release **20/100**, and strong-Q1 maturity approximately **28/100**.

## Claim boundary

The T188 receipt verifies a licensed public source and an auditable low-coverage candidate. It does not establish model validity, independent validation, evaluator independence, no-author reproduction, user adoption, DOI deposition, or `scientific_submission_ready=true`.

## Required next actions

1. If T188 is analyzed further, produce a separate exploratory analysis receipt with the frozen rank denominator, ambiguity policy, technical-replicate rule, coverage strata, patient-level effective `n`, missingness table and selection-aware negative control.
2. Close the external hard gates through real non-author actors and an actual DOI archive event; author-generated reports or agent reviews cannot substitute for those receipts.
