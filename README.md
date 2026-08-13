# BioInterfaceOS

BioInterfaceOS is a provenance-grounded software and protocol framework for auditable protein-corona and biointerface proteomics analysis.

## Current public release

This repository contains the R4 real-data execution branch used on the KAUST server. The current release includes:

- a frozen 99-target rank benchmark spanning three laboratory anchors, 47 measurement batches and 2,724 rank-eligible development observations;
- nested selection, laboratory-held-out evaluation, cluster-aware uncertainty, paired composition ablation and within-batch negative controls;
- byte-verified public full-text/PRIDE source audits, including the CC0 PXD060795 Dalian plasma-corona workbook;
- reproducible source maps, receipts, tests and editorial claim-boundary documents.
- immutable release tag `v0.1.3-r9`, which includes the T180 paper-attached 141-subject source audit, the T181 biological-cohort OOD protocol/receipts, and the external evaluator handoff contract.

The PXD060795 result is a six-batch exploratory sensitivity analysis. It is not presented as an independent lockbox evaluation or as external scientific replication.

## Reproduce the audited software run

```bash
uv sync --locked --all-groups
uv run pytest tests/review_round_3 tests/review_round_4 -q
```

The audited KAUST run passed 25 tests. The test result establishes software and data-pipeline reproducibility under the reported environment; it does not establish non-author scientific replication.

## Evidence boundary

At this release, `scientific_submission_ready` remains `false`. There is not yet a non-author protected-data lockbox receipt, a non-author end-to-end reproduction receipt, or independently verifiable external user adoption. The project therefore does not claim independent validation, broad generalization, clinical utility or community adoption.

See:

- `docs/review_round_4/R4_R9_RELEASE_DOI_STATUS_20260813.md`
- `docs/release/R9_RELEASE_MANIFEST.json`
- `docs/review_round_4/R4_MULTI_AGENT_EDITORIAL_REEVALUATION.md`
- `docs/review_round_4/R4_STRONG_Q1_REMEDIATION_GOAL.md`
- `docs/review_round_3/R3_EXTERNAL_LOCKBOX_AND_REPRODUCTION_HANDOFF.md`
- `docs/external/INDEPENDENT_REPRODUCTION_AND_USER_HANDOFF.md`
- `docs/data/R4_T166_EXTERNAL_EVALUATOR_AND_REPRODUCTION_PROTOCOL.json`
- `docs/data/R4_T167_EXTERNAL_USER_ADOPTION_INTAKE.json`
- `docs/data/R4_T172_EXTERNAL_RECEIPT_BUNDLE_TEMPLATE.json`
- `docs/data/R4_T174_OOD_EFFECTIVE_N_MISSINGNESS_PROTOCOL.json`
- `docs/data/R4_T175_OOD_CLUSTER_SENSITIVITY_PROTOCOL.json`
- `docs/data/R4_T162_PXD060795_DALIAN_SOURCE_REGISTRY.json`

The public handoff is tracked in [GitHub Issue #1](https://github.com/ahvsjags/BioInterfaceOS/issues/1).
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
