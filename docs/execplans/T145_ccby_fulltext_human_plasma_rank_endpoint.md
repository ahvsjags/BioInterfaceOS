# T145 — CC-BY full-text human-plasma cohort and rank endpoint

## Decision

Create a new R3 route separate from the failed CC0-only route. The route may
use only CC-BY full text and publisher/Europe PMC supplementary assets whose
bytes, licence and source coordinates are verified. It must not alter any R2
CC0 receipt or promote its blocked target.

The candidate sources are enumerated in
`docs/data/R3_T145_CCBY_HUMAN_PLASMA_CANDIDATE_COHORT.json`. They provide three
independent laboratory anchors and a common context: human-plasma nanoparticle
protein-corona proteomics. They do not provide a shared raw abundance scale.

## Proposed shared endpoint

For a source-provided `study_condition_analysis_batch`, the candidate endpoint
is the within-condition abundance percentile of a *reported* protein record:

`rank_percentile = rank_descending(author_reported_quantification) / n_reported_proteins`

The value is an analysis target only after the amendment below is locked. It is
not a biological concentration, a cross-study abundance, or an imputed value.
The only permitted cross-source comparison is of this source-local, monotonic
rank transform and its uncertainty.

## Strict extraction rules

1. Retain the article DOI, PMCID, CC-BY licence, asset SHA-256, worksheet,
   original row number and original cell range for every extracted record.
2. Retain author `NA` values as missingness codes. Do not convert them to zero,
   detection, non-detection or a numeric value during intake.
3. A source table that lists only identified proteins is **rank-only**. A
   protein absent from such a table has no negative label.
4. Use an author-provided quantity only inside its own source condition. Never
   concatenate intensity, PSM, spectral-count or normalized-abundance scales.
5. Canonical protein accessions may be added only through a versioned mapping
   table. Ambiguous proteins remain source-native or are excluded under a
   predeclared rule; they are never silently collapsed.
6. Source identity, facility code, figure labels, worksheet names and patient
   identifiers are provenance variables. They may not become predictive identity
   features.

## Evaluation design to lock before fitting

* Primary split: leave one independent laboratory anchor out. The MSU study is
  additionally evaluated by leave-one-core-facility-out splits.
* Tuning and protein-feature preprocessing occur only within the development
  side of each outer split.
* Report source-local rank correlation, calibrated interval coverage, retained
  record counts, author-NA rates and the full missingness decision table for
  every split. Do not pool metrics before reporting each held-out source.
* Compare no-harmonization, source-local rank transformation and any learned
  harmonization method under the same splits. Include shuffled-rank and
  facility-label negative controls.
* The Oklahoma tables enter only as rank-only external evidence unless their
  source files establish a complete condition universe; they cannot supply
  pseudo-negatives.

## Admission gate

Before model fitting, all of the following are required:

1. A byte-verified, row-level map for the Oklahoma tables, matching the map
   already generated for PMC9633814 and the published PXD017052 unit map.
2. A locked R3 amendment defining study condition, biological/technical
   replicate role, canonical protein mapping version, analysis population and
   missingness rule.
3. A dry-run manifest proving that every candidate record is assigned to one
   laboratory anchor without reusing a source asset as evidence for another.
4. A signed data-licence notice bundled with the release.

Until all four conditions are met: `model_use=PROHIBITED`,
`scientific_submission_ready=false`.
