# BioInterfaceOS

BioInterfaceOS is a provenance-grounded software and protocol framework for auditable protein-corona and biointerface proteomics analysis.

## Current public release

This repository contains the R4 real-data execution branch used on the KAUST server. Historical R4 assets remain available, but the current external-handoff candidate is `v0.1.3-r10.56`. The release contains the public T250 route, the analysis-only T265 supplement, and the external evidence contracts; it does not claim scientific results from non-author evaluators or external users. The current paper-data execution includes:

- a four-source, four-source/laboratory-anchor common-target route with seven exact canonical accessions, 783 row-traceable observations, 115 measurement batches and four laboratory-held-out folds; this is exploratory, conditioned on the pre-frozen all-source target-availability intersection, and not four independent biological cohorts;
- a public full-text/supplementary-data route using paper-derived observations, with source-local ranks, nested batch selection, cluster uncertainty, paired composition ablation and permutation controls; paper-derived data are not a substitute for non-author validation;
- a T254 stratified full-text evidence package that binds article/accession locators, license and redistribution status, biological-unit semantics, execution receipts, negative/exclusion results and the external-gate boundary;
- a T238 four-source fold-local target-membership sensitivity with 3,844 fold-ledger rows (3,061 development and 783 non-repeated held-out test observations), 9/9/10/10 development target counts, 115 batch clusters and explicit finite-null accounting;

The following bullets preserve the earlier R4 benchmark and sensitivity assets for provenance and comparison:

- a frozen 99-target rank benchmark spanning three laboratory anchors, 47 measurement batches and 2,724 rank-eligible development observations;
- a strict nine-accession common-target sensitivity route spanning three laboratory anchors, 809 row-traceable observations and 85 measurement batches;
- a CC-BY-4.0 paper-attached biological-cohort route with 141 subject units, 705 subject-by-particle batches, 666 rank-qualified batches and 17,026 external target observations;
- a T197 outer-fold target-availability sensitivity with development-only target membership, 2,792 fold-specific observations, 85 measurement batches and selection-aware permutation nulls;
- a T198 paper-cohort threshold/missingness sensitivity over eight coverage thresholds, including 6,640 retained `AUTHOR_NA` rows and biological-unit retention accounting;
- a T200 statistical closure with fold-level measurement-batch intervals, frozen estimands, Holm bookkeeping and stratified paper-cohort missingness tables;
- a locally executed analysis-only Manchester paper-anchored OOD route with 60 patient clusters, 288 longitudinal batches and 4,150 external observations; the unlicensed raw matrix remains analysis-only and is not redistributed;
- the corrected Manchester OOD negative result is retained: full ridge is below composition-only by `-0.0596` patient-equal Spearman (95% CI `[-0.0786, -0.0409]`), so no universal full-feature superiority claim is made; the unanchored matrix unit `HA5` is excluded against Supplementary Data 3;
- nested selection, laboratory-held-out evaluation, cluster-aware uncertainty, paired composition ablation and within-batch negative controls;
- an analysis-only paper-full-text OOD route from PMC10257194 with 45 biological units, 97 shared targets, 4,362 row-traceable source cells, paired ablation, cluster bootstrap and permutation control; the CC-BY-NC-ND workbook and numeric derivatives are not redistributed;
- byte-verified public full-text/PRIDE source audits, including the CC0 PXD060795 Dalian plasma-corona workbook;
- reproducible source maps, receipts, tests and editorial claim-boundary documents.
- a descriptive source-conditional heterogeneity audit with five effect units (not five independent studies), explicit non-inference of biological n from measurement batches, rounded presentation fields, degenerate-interval semantics and a KAUST fresh author-run replay receipt (T214-T216);
- historical immutable release tags remain available for provenance; the current fixed handoff release is `v0.1.3-r10.56` and the current handoff contract is `docs/data/R4_T279_EXTERNAL_GATE_HANDOFF_PROTOCOL_20260815.json`.

The PXD060795 result is a six-batch exploratory sensitivity analysis. It is not presented as an independent lockbox evaluation or as external scientific replication.

## Reproduce the audited software run

```bash
uv sync --locked --all-groups
uv run pytest tests/review_round_3 tests/review_round_4 -q
```

The audited KAUST run includes the T197/T198/T200 receipt checks across the review-round suites. The result establishes software and data-pipeline reproducibility under the reported environment; it does not establish non-author scientific replication.

## Evidence boundary

At this release, `scientific_submission_ready` remains `false`. There is not yet a non-author protected-data lockbox receipt, a non-author end-to-end reproduction receipt, or independently verifiable external user adoption. The project therefore does not claim independent validation, broad generalization, clinical utility or community adoption.

See:

- `release/empirical_candidate_v0.1.3-r10.56/README.md`
- `docs/release/R10_56_DOI_DEPOSIT_METADATA.json`
- `docs/data/R4_T279_EXTERNAL_GATE_HANDOFF_PROTOCOL_20260815.json`
- `docs/data/R4_T279_EXTERNAL_GATE_HANDOFF_PROTOCOL_20260815.json`
- `docs/data/R4_T279_LOCKBOX_WORK_PACKAGE_20260815.json`
- `docs/data/R4_T279_EXTERNAL_USER_ADOPTION_INTAKE_20260815.json`
- `docs/data/R4_T279_EXTERNAL_RECEIPT_BUNDLE_TEMPLATE.json`
- `docs/external/R4_T279_EXTERNAL_EVIDENCE_REQUEST_20260815.md`
- `scripts/r4_external_reproduction_r10_54.sh`
- `docs/review_round_4/R4_T272_STRONG_Q1_EXTERNAL_EVIDENCE_CLOSURE_GOAL_20260815.md`
- `docs/review_round_4/R4_T273_BIOLOGICAL_UNIT_PRIMARY_STATUS_20260815.md`
- `docs/review_round_4/R4_T274_COVERAGE_SENSITIVITY_STATUS_20260815.md`
- `docs/review_round_4/R4_T275_T250_REPLICATE_SENSITIVITY_STATUS_20260815.md`
- `docs/review_round_4/R4_T275_CROSS_ENVIRONMENT_REPRODUCIBILITY_RECEIPT_20260815.json`
- `docs/review_round_4/R4_T276_CURRENT_EDITORIAL_SCORECARD_20260815.md`
- `docs/review_round_4/R4_T277_T250_REPLICATE_AWARE_REFIT_STATUS_20260815.md`
- `docs/review_round_4/R4_T277_CROSS_ENVIRONMENT_REPRODUCIBILITY_RECEIPT_20260815.json`
- `docs/review_round_4/R4_T278_POST_T277_EDITORIAL_SCORECARD_20260815.md`
- `docs/review_round_4/R4_T279_CLEANROOM_HELPER_SELFTEST_20260815.json`
- `docs/data/R4_T277_T250_REPLICATE_AWARE_REFIT_PROTOCOL.json`
- `docs/data/R4_T277_T250_REPLICATE_AWARE_REFIT_REGISTRY.json`
- `docs/release/R10_53_DOI_DEPOSIT_METADATA.json`
- `docs/release/R10_53_ARCHIVE_BUILD_RECEIPT_20260815.json`
- `docs/release/R10_54_DOI_DEPOSIT_METADATA.json`
- `docs/release/R10_54_ARCHIVE_BUILD_RECEIPT_20260815.json`
- `docs/release/R10_55_DOI_DEPOSIT_METADATA.json`
- `docs/release/R10_55_ARCHIVE_BUILD_RECEIPT_20260815.json`
- `docs/release/R10_56_DOI_DEPOSIT_METADATA.json`
- `docs/release/R10_56_ARCHIVE_BUILD_RECEIPT_20260815.json`

- `docs/review_round_4/R4_T191_RELEASE_STATUS_20260814.md`
- `release/empirical_candidate_v0.1.3-r10.28/release_manifest.json`
- `docs/review_round_4/R4_T196_PAPER_ATTACHED_BIOLOGICAL_COHORT_PUBLIC_STATUS_20260814.md`
- `docs/review_round_4/R4_T197_SOURCE_AVAILABILITY_STATUS_20260814.md`
- `docs/review_round_4/R4_T238_FOUR_SOURCE_AVAILABILITY_STATUS_20260814.md`
- `docs/review_round_4/R4_T239_POST_T238_MULTI_AGENT_EDITORIAL_REVIEW_20260814.md`
- `docs/data/R4_T254_FULLTEXT_PAPER_DERIVED_EVIDENCE_PACKAGE_20260814.json`
- `docs/review_round_4/R4_T254_FULLTEXT_PAPER_DERIVED_EVIDENCE_STATUS_20260814.md`
- `docs/data/R4_T255_CLUSTER_UNCERTAINTY_PROTOCOL_20260814.json`
- `reports/review_round_4/t255_cluster_uncertainty/v1.0.0/`
- `docs/review_round_4/R4_T198_PAPER_COHORT_MISSINGNESS_STATUS_20260814.md`
- `docs/review_round_4/R4_T199_STRONG_Q1_REMEDIATION_GOAL_20260814.md`
- `docs/review_round_4/R4_T200_STATISTICAL_CLOSURE_STATUS_20260814.md`
- `docs/review_round_4/R4_T203_PMC10257194_PAPER_OOD_STATUS_20260814.md`
- `docs/review_round_4/R4_T208_MULTI_SOURCE_CLAIM_REPAIR_20260814.md`
- `docs/review_round_4/R4_T209_MANCHESTER_COHORT_RECONCILIATION_20260814.md`
- `docs/review_round_4/R4_T211_MULTI_AGENT_EDITORIAL_REVIEW_20260814.md`
- `docs/review_round_4/R4_T215_MULTI_AGENT_EDITORIAL_REVIEW_20260814.md`
- `docs/review_round_4/R4_T216_KAUST_FRESH_REPLAY_RECEIPT_20260814.json`
- `docs/review_round_4/R4_T217_STATISTICAL_AMENDMENT_EXECUTION_20260814.md`
- `docs/review_round_4/R4_T217_KAUST_FRESH_REPLAY_RECEIPT_20260814.json`
- `docs/review_round_4/R4_T228_R10_28_RELEASE_DOI_STATUS_20260814.md`
- `docs/review_round_4/R4_T229_CURRENT_STRONG_Q1_COMPLETION_AUDIT_20260814.md`
- `docs/review_round_4/R4_T230_PUBLIC_PAPER_DATA_RESCREEN_20260814.md`
- `docs/review_round_4/R4_T231_FULLTEXT_PRIDE_CANDIDATE_RESCREEN_20260814.md`
- `docs/review_round_4/R4_T232_POST_T231_STRONG_Q1_GATE_AUDIT_20260814.md`
- `docs/review_round_4/R4_T233_PXD026615_MZID_REPROCESSING_20260814.md`
- `docs/external/R4_T234_FIXED_RELEASE_EXTERNAL_HANDOFF_20260814.md`
- `docs/review_round_4/R4_T205_DOI_DEPOSIT_PREFLIGHT_20260814.md`
- `docs/execplans/T196_publish_paper_attached_biological_cohort.md`
- `docs/review_round_4/R4_MULTI_AGENT_EDITORIAL_REEVALUATION.md`
- `docs/review_round_4/R4_STRONG_Q1_REMEDIATION_GOAL.md`
- `docs/review_round_3/R3_EXTERNAL_LOCKBOX_AND_REPRODUCTION_HANDOFF.md`
- `docs/external/INDEPENDENT_REPRODUCTION_AND_USER_HANDOFF_R10_28.md`
- `docs/data/R4_T218_EXTERNAL_EVIDENCE_HANDOFF_PROTOCOL.json`
- `docs/data/R4_T218_EXTERNAL_USER_ADOPTION_INTAKE.json`
- `docs/data/R4_T218_EXTERNAL_RECEIPT_BUNDLE_TEMPLATE.json`
- `docs/data/R4_T174_OOD_EFFECTIVE_N_MISSINGNESS_PROTOCOL.json`
- `docs/data/R4_T175_OOD_CLUSTER_SENSITIVITY_PROTOCOL.json`
- `docs/data/R4_T162_PXD060795_DALIAN_SOURCE_REGISTRY.json`

The public handoff is tracked in [GitHub Issue #2](https://github.com/ahvsjags/BioInterfaceOS/issues/2). This is a request for genuinely non-author participation, not evidence that external work has already occurred.
Issue creation, page views and author-controlled reruns are not evidence of
independent reproduction or adoption.

```bash
uv run biointerfaceos data preflight-r4-external-receipts \
  --bundle external_bundle.json \
  --documents-root external_receipts \
  --receipt-out r4_preflight_receipt.json \
  --strict
```

The command intentionally returns
`STRUCTURALLY_COMPLETE_PENDING_IDENTITY_REVIEW` and keeps
`scientific_submission_ready=false` until the editorial identity and
independence audit is complete.

The R4 same-lineage OOD candidate also has a non-promoting effective-n and
missingness audit:

```bash
uv run biointerfaceos data audit-r4-ood-effective-n --strict
uv run biointerfaceos data verify-r4-ood-effective-n --strict
```

It reports 8,064 source rows, 7,075 rank-eligible rows, 142 measurement
batches, 134 primary-eligible batches, 5 biological units and 1 laboratory.

The same-lineage OOD result also has a cluster-sensitive paired audit:

```bash
uv run biointerfaceos data audit-r4-ood-cluster-sensitivity --strict
uv run biointerfaceos data verify-r4-ood-cluster-sensitivity --strict
```

Across the five biological units, the unit-weighted full-model mean Spearman
is 0.2229 versus 0.2346 for composition-only; the paired full-minus-
composition delta is -0.0118 (cluster bootstrap 95% interval -0.0295 to
0.0111). The batch-weighted delta is -0.0047. This is an author-run,
same-lineage sensitivity audit from one laboratory and does not create
independent validation.

## License and data policy

Software is released under Apache-2.0. Each data asset is retained only when its source licence and redistribution status are recorded in the corresponding registry. Ambiguous or non-redistributable source material is kept out of the public redistributable cohort; accession and download instructions may be retained as pointers for a separately governed analysis-only route.

This repository is a public, versioned methods and audit package. A DOI has not yet been issued for this release; the DOI field must remain unresolved until an archival service produces an immutable deposit receipt.
