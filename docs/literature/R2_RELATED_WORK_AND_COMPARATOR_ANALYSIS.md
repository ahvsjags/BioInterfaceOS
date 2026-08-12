# R2 external literature and comparator evidence packet

## Scope and search record

This packet is a targeted, reproducible related-work review for the second
round. It addresses the reviewer finding that external literature,
comparators, and operational definitions were missing. The search question,
source classes, inclusion/exclusion criteria and retrieval time are stored in
`R2_EXTERNAL_EVIDENCE.json`. It is not a systematic review, and it cannot
replace a compatible real target (T123), protected independent evaluation
(T124), or external scientific reproduction (T128).

## Portfolio decision

The R2 portfolio has two non-overlapping manuscript targets.

1. **Paper A+B** is one future real-data provenance, benchmark and method
   manuscript. Its valid present contribution is the audited source-locator
   workflow and its boundaries. It must not present fixture metrics, raw-cell
   resolution, or external papers' performance as biological prediction,
   causal inference, or independent validation.
2. **Paper C** is a results-blind protocol until T124 returns a signed,
   independent evaluator receipt from protected real observations. It must not
   use ?law discovery?, ?replicated?, ?refuted?, or post-lock result language
   before then.

The machine-readable citation coverage, comparator map and claim constraints
are in `R2_MANUSCRIPT_COMPARATOR_MAP.json`.

## Nearest-neighbour comparison

| Comparator | What it establishes | R2 positioning | Non-equivalence that must remain in the manuscript |
|---|---|---|---|
| MIRIBEL | Minimum reporting across material, biology and protocol for bio?nano experiments. | R2 requires the same categories as source/provenance fields. | Metadata admission does not make sources comparable or validate a model. |
| MINBE | Corona-specific experimental-design/reporting checklist. | R2 exposes biological/corona condition and protocol fields. | R2 currently does not create a new corona-proteomics dataset. |
| eNanoMapper | Ontology-based integration of nanomaterials, assays, endpoints and units. | R2 uses a narrow controlled glossary and source units. | The glossary is not a full ontology mapping. |
| SciFact | Claim-evidence retrieval with support/refute decisions and rationales. | R2 records evidence locators and semantic gates. | Raw-cell retrieval is not support/refute claim verification. |
| WILDS | Declared real-world distribution shifts with separate OOD evaluation. | R2 requires frozen group keys and an external cohort before OOD claims. | Current one-study-per-endpoint data cannot support OOD evaluation. |
| Life-science ML reproducibility standards | Publication of data, model, code and workflow details. | R2 adds checksums, receipts, replay and fail-closed workflows. | Software replay is not independent scientific replication. |
| Protein-corona predictive models | Concrete predictor/target/covariate designs in corona research. | They are nearest domain comparators for a future compatible corona target. | Their corpora and scores cannot be reused as R2 data, baseline or external test without audited admission. |
| Registered Reports | Results-blind evaluation of question and methods. | Paper C stays protocol-only before T124. | A protocol does not establish a result. |

## Current evidence gap and resulting manuscript language

The strict T123 audit found three real sources but three distinct endpoint/unit
pairs, with effective n=1 for each pair. Therefore A+B must state that the
current source-locator benchmark is not a biological model target, and C must
remain a protocol. The dedicated expansion requirements are in
`../data/R2_REAL_MODEL_SOURCE_EXPANSION_REQUIREMENTS.md`.

## References

All references below have a verified landing page in
`R2_EXTERNAL_EVIDENCE.json`.

- Monopoli et al. (2012), biomolecular corona context ?
  <https://doi.org/10.1038/nnano.2012.207>
- Faria et al. (2018), MIRIBEL ? <https://doi.org/10.1038/s41565-018-0246-4>
- Chetwynd et al. (2019), MINBE ? <https://doi.org/10.1016/j.nantod.2019.06.004>
- Wilkinson et al. (2016), FAIR ? <https://doi.org/10.1038/sdata.2016.18>
- Hastings et al. (2015), eNanoMapper ? <https://doi.org/10.1186/s13326-015-0005-5>
- Wadden et al. (2020), SciFact ? <https://doi.org/10.18653/v1/2020.emnlp-main.609>
- Koh et al. (2021), WILDS ? <https://proceedings.mlr.press/v139/koh21a.html>
- Heil et al. (2021), life-science ML reproducibility ?
  <https://doi.org/10.1038/s41592-021-01256-7>
- Findlay et al. (2018), silver-nanoparticle corona prediction ?
  <https://doi.org/10.1039/C7EN00466D>
- Ban et al. (2020), functional-corona prediction ?
  <https://doi.org/10.1073/pnas.1919755117>
- Canchola et al. (2025), multi-study corona database and ML ?
  <https://doi.org/10.1021/acsnano.5c08608>
- Nosek & Lakens (2014), Registered Reports ?
  <https://doi.org/10.1027/1864-9335/a000192>
