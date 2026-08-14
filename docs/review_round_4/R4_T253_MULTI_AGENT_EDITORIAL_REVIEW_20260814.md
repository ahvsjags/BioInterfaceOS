# R4-T253 multi-agent editorial re-review — 2026-08-14

## Decision

**Major Revision. `scientific_submission_ready=false`.**

Five independent read-only roles reviewed the current r10.32 scientific
candidate, the r10.33/r10.34 handoff materials, T249/T250, the public-data
registries, and T251. No role treated an Issue comment, a template, an
author/Codex run, or a public Release as third-party evidence.

The strongest defensible positioning is:

> An author-run, paper-derived, source-conditional protein-target rank
> portability/resource analysis with auditable provenance and exploratory
> laboratory-anchor-held-out execution.

It is not four independent biological cohorts, donor-level validation, a
non-author reproduction, or proof of sequence-feature superiority.

## Conservative module scores

| Module | Score | Panel basis |
|---|---:|---|
| Data compatibility and sample foundation | 82 | Public source maps and strict rank semantics are strong; donor/technical-unit semantics and cross-assay comparability remain limiting. |
| Statistical analysis design | 88 | Nested batch selection, laboratory-anchor folds and cluster uncertainty are strong; T250 is conditional on the pre-frozen all-source target intersection. |
| Statistical execution and effective n | 77 | Real 783-row/115-batch execution is auditable, but those counts are not donor-level effective n and the biological hierarchy is incompletely resolved. |
| Models, ablation, negative controls and OOD | 75 | Models and controls run, but full-minus-composition is zero in T250 and paper-attached OOD directions are heterogeneous. |
| Independent protected lockbox | 12 | No verified non-author protected evaluator receipt. |
| No-author scientific reproduction | 8 | Fixed tag and PMC/PXD route are ready; no independent receipt exists. |
| External user adoption | 46 | Intake and public coordination exist; verified non-author real-task receipts: 0/2. |
| DOI / immutable archive read-back | 25 | Preparation metadata exists; authenticated archive read-back is absent. |

Internal scientific core mean: **80.5**. External-evidence mean: **22.8**.
Eight-module simple mean: **51.6**. The means are descriptive only; the four
external predicates remain hard gates.

## Panel findings that changed the remediation target

1. The T249 seven-target intersection is outcome-free and model-free, but it
   uses all four source lineages before T250. T250 therefore measures
   portability conditional on all-source availability; it is not fully
   independent of the held-out source's target membership. T197's fold-local
   availability route should be the primary sensitivity if a stricter
   external estimand is claimed.
2. The primary score is a batch-level rank estimand. Report row count,
   measurement-batch clusters, source/laboratory anchors, and donor-resolved
   units separately. Technical replicates and pooled plasma cannot be promoted
   to biological n.
3. The T250 permutation keeps the observed nested-selected alpha fixed. It is
   a conditional permutation null, not a fully selection-aware null that
   re-runs alpha selection for every permutation.
4. Full sequence versus composition-only has no T250 incremental Spearman
   signal, while paper-attached OOD routes are directionally heterogeneous.
   The manuscript must use source-conditional/exploratory language.
5. PMC6592156/PXD007648 supplies a public paper-derived route; the current
   path primarily uses processed supplementary LFQ data, not an independent
   raw-MS reanalysis. [PMC6592156](https://pmc.ncbi.nlm.nih.gov/articles/PMC6592156/)
   [PXD007648](https://proteomecentral.proteomexchange.org/cgi/GetDataset?ID=PXD007648)

## Remaining hard gates

All four are still false: one non-author protected lockbox receipt, one
no-author accession-to-result receipt, two distinct non-author real-task
adoption receipts, and one authenticated DOI/immutable-archive read-back.
They require real external actors or an archival service and cannot be
created by additional author-side computation.

## Submission recommendation

Do not submit the current package as a strong-Q1 biological-validation or
universal sequence-prediction paper. After claim downgrading it is suitable for
continued development as a computational methods, provenance, benchmark, or
source-conditional portability/resource manuscript. Strong-Q1 submission
requires the four external artifacts, a final clean immutable snapshot, and a
new editorial review with no major gate.
