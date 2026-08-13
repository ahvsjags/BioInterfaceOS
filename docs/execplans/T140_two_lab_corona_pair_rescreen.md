# T140: Two-laboratory human-plasma corona pair rescreen

## Purpose

Audit a promising pair of primary studies that may support a future
cross-laboratory protein-corona target: UCD's 2008 PNAS study and PNNL's 2011
Proteomics study. Both article records describe human plasma, polystyrene
particles at 50 and 100 nm, and quantitative/structured corona protein
measurements. This is a candidate-source audit, not target admission.

## Current decision

`BLOCKED_PAIR_ASSET_LICENCE_UNIT_MAP_AND_SHARED_ENDPOINT_AUDIT`.

The pair has two distinct publication laboratories and a promising overlapping
size design, but the following evidence is still missing:

1. first-party supplementary bytes and SHA-256/byte-count receipts;
2. reuse terms for every source asset, with a segregated CC-BY or analysis-only
   route if CC0 is not supported;
3. explicit source-file/result-unit-to-size/material maps for both studies;
4. a shared preprocessing and endpoint contract that does not concatenate the
   UCD and PNNL author-specific scales.

Until these conditions close, T129 remains unchanged, the CC0 cohort is not
expanded, T121 Amendment v1.0.1 is not created, and model/T124/T126--T128
scientific gates remain blocked.

## Primary sources

- Lundqvist et al., PNAS 2008, DOI `10.1073/pnas.0805135105`,
  [PMC2567179](https://pmc.ncbi.nlm.nih.gov/articles/PMC2567179/).
- Zhang et al., Proteomics 2011, DOI `10.1002/pmic.201000587`,
  [PMC3252235](https://pmc.ncbi.nlm.nih.gov/articles/PMC3252235/).

## Validation

The strict workflow records exactly two sources, two distinct laboratories and
the two shared article-level sizes, then writes a non-admission report and
receipt with `target_status=NOT_FROZEN`, `model_use=PROHIBITED` and all model,
OOD, independent-validation and submission fields false. Regression tests
reject candidate promotion, altered source identity, weakened policy and
tampered receipts.
