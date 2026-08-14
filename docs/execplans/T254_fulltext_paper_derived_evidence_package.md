# T254: full-text paper-derived evidence package

Date: 2026-08-14
Status: `COMPLETED_INTERNAL_EXTERNAL_GATES_UNVERIFIED`
Objective: make the no-new-wet-lab fallback auditable without promoting paper-derived, pooled, technical, or author-run material to independent biological validation.

## Frozen positioning

The primary manuscript claim is limited to an author-run, paper-derived,
source-conditional benchmark for protein-corona rank portability. T238 is the
primary availability-aware estimand. T250, T246, T177, T203 and T209 are
separate sensitivity or analysis-only strata. They must not be pooled into one
confirmatory effect or relabelled as independent cohorts.

## Required evidence contract

Every admitted route must declare:

- article/full-text and supplementary or accession locator;
- source and laboratory/core anchor;
- license and redistribution status;
- source-row/cell provenance and input hashes;
- measurement-batch, technical-replicate and biological-unit semantics;
- target selection and missingness rule;
- model, ablation, negative-control and uncertainty receipts;
- the exact claim level and prohibited interpretations.

Analysis-only sources may contribute a hashed local receipt and a bounded
summary, but their raw matrix and numeric derivatives must not enter the public
release unless redistribution is explicitly permitted.

## Acceptance criteria

1. The JSON evidence package validates as UTF-8 JSON.
2. The T238 report and protocol agree on the frozen protocol hash and on the
   separate 3,844 fold-ledger / 3,061 development / 783 held-out accounting.
3. T238 has fold-local target membership and selection-aware finite nulls.
4. Technical routes explicitly report pooled/common-material semantics.
5. Analysis-only and screen-only routes remain non-redistributable or
   non-admitted, with no model or claim promotion.
6. The package keeps all four external predicates false until real receipts are
   received from non-author actors or an authenticated archive service.

## Artifacts

- `docs/data/R4_T254_FULLTEXT_PAPER_DERIVED_EVIDENCE_PACKAGE_20260814.json`
- `docs/review_round_4/R4_T254_FULLTEXT_PAPER_DERIVED_EVIDENCE_STATUS_20260814.md`
- `tests/review_round_4/test_r4_t254_fulltext_evidence_package.py`

## Explicit non-goals

This target does not create wet-lab measurements, donor-level effective n,
protected lockbox performance, no-author reproduction, external adoption, or
an authenticated DOI read-back. Those gates remain independently verifiable
only.
