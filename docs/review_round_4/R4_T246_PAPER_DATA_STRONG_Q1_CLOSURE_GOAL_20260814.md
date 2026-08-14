# R4-T246: paper-data fallback strong-Q1 closure goal

Date: 2026-08-14  
Status: `IN_PROGRESS`  
Decision: `MAJOR_REVISION`; `scientific_submission_ready=false`

## Objective

When new wet-lab acquisition is unavailable, use only public full-text articles,
official supplementary tables and public repository assets to complete the
internal empirical evidence layer. The primary claim is explicitly bounded to
technical/source-conditional portability. The project must reach at least
90/100 on every internal scientific module and must separately obtain real
non-author evidence for the external hard gates.

The objective does not permit a paper-attached processed table to be described
as a new donor cohort, a lockbox, an independent evaluator, or an external
reproduction.

## Evidence already available

| Evidence route | What is frozen and executed | Permitted interpretation | Key boundary |
|---|---|---|---|
| `PMC9633814`, CC-BY-4.0 | 9,909 source-map rows, 707 eligible target observations, 99 pre-frozen targets, 12 core-facility-held-out folds, full/composition ablation, cluster bootstrap and permutation control | technical cross-core portability on a common pooled aliquot | one biological aliquot; not 12 biological cohorts |
| `PMC11328176`, CC-BY-4.0 | byte-verified SI1: 6,651 rows, 1,001 accessions, 6 blinded core anchors, 3 technical replicates, 70 frozen-target overlaps; six-fold nested ridge execution gives full Spearman `0.509683` (core-bootstrap 95% CI `[0.391177, 0.612970]`) and paired full-minus-composition `0.076958` | independent technical sensitivity route on a second multicore paper dataset | one common prepared corona/plasma material; not six biological cohorts; `P60174` absent |
| `T192/T195` three-source route | 3 public source registries, 9 exact common accessions, 809 row-traceable observations, 85 batches, 3 leave-one-source-anchor-out folds | source-conditional common-target sensitivity | pooled/unspecified plasma, donor IDs or technical-replicate limits remain |
| `T180/T181/T198` paper cohort | 141 biological units, 705 batches, 17,026 external target observations, threshold and missingness sensitivity | author-run biological-cohort OOD | not an independent laboratory, lockbox or no-author run |
| `T203` and corrected `T209` | paper-derived OOD with paired ablation, negative controls and cluster uncertainty; T209 has 60 paper-anchored units, 288 batches and 4,150 target cells | author-run external/paper-data sensitivity | source-specific and analysis-only; does not close external gates |
| `T245` | local, KAUST and GitHub CI engineering evidence | reproducible software execution | software CI is not scientific independence |

The full-text/core-facility route is scientifically relevant: the published
study reports identical corona samples processed by multiple proteomics cores,
but the current repository keeps the core identity and common-aliquot boundary
explicit. The related uniform-processing paper also reports processed
supplementary datasets while stating that raw files are available on request
because core names are blinded; it is therefore useful as corroboration or
sensitivity evidence, not as an unqualified primary independent-cohort claim.

T246 now includes the second multicore route in
`docs/data/R4_T246_PMC11328176_MULTICORE_SCREEN_20260814.md` and its JSON
receipt. The new asset strengthens byte-level provenance, license closure and
technical portability coverage. It does not increase the biological effective
`n` or close the three external hard gates, so the conservative strict score
remains unchanged until a genuinely independent biological unit or a verified
non-author receipt is available.

## Current conservative panel score

Scores below are for the strict strong-Q1 rubric, not for the narrower
software/protocol rubric.

| Module | Current score | Target | Evidence-based reason |
|---|---:|---:|---|
| data compatibility and sample base | 88 | >=90 | row-level public assets and 3 source anchors exist, but biological-unit semantics are not uniformly independent |
| statistical analysis design | 94 | >=90 | estimand, pre-frozen target universe, nested selection, cluster uncertainty, missingness and multiplicity are explicit |
| statistical execution and effective n | 91 | >=90 | T193/T194/T195/T198/T200 execute models, ablations, negative controls and uncertainty; effective biological n remains bounded by source semantics |
| model, ablation, negative control and OOD evidence | 89 | >=90 | several real paper-data routes and one negative cross-source result are retained; all results remain author-run |
| independent lockbox evaluation | 12 | >=90 | no verified non-author protected evaluator receipt |
| external scientific reproduction | 8 | >=90 | no no-author accession-to-result receipt |
| external user adoption | 46 | >=90 | public release and intake are present, but no verified independent users, installs, issues/PRs or adoption receipts |
| DOI/immutable archive | 25 | >=90 | DOI metadata is prepared; authenticated archive record and read-back receipt are absent |

Strict submission maturity is therefore `58/100` by the current panel's
minimum-gate interpretation. The project is not submission-ready even though
the internal data, statistics and engineering modules have materially improved.

## Exit criteria for this improvement round

### Internal scientific closure

1. Freeze the scope as technical/source-conditional portability and retain the
   biological-cohort and OOD routes as separate strata.
2. Bind T192, T193, T194, T195, T197, T198, T200, T203 and T209 to one new
   immutable release whose manifest contains all input/output hashes.
3. Re-run the strict validator, clean-room replay and KAUST replay from that
   release; all model, ablation, negative-control, missingness and uncertainty
   receipts must be readable without author-only files.
4. Update the manuscript claim matrix so every headline number names its
   biological unit, laboratory/core unit, source license and analysis-only
   boundary.
5. Pass a new role-separated editorial review with every internal module at
   least 90/100. A score is not raised merely because an additional paper was
   found; it rises only when the unit and license semantics are closed.

### External hard-gate closure

The following require real parties or a real archival service and cannot be
completed by the author-side agent:

1. one non-author evaluator holds protected held-out input or an unseen real
   dataset and returns a signed aggregate lockbox receipt;
2. one no-author team starts from the public accession/release and returns a
   signed accession-to-result reproduction receipt;
3. two distinct non-author users or institutions complete clean installations
   and real tasks with environment and output hashes;
4. an authenticated DOI/archive service returns an immutable locator, version
   DOI and read-back hash receipt;
5. after those receipts are independently checked, run the final editorial
   gate and only then allow `scientific_submission_ready=true`.

## Current action order

| Priority | Action | State | Acceptance artifact |
|---|---|---|---|
| P0 | paper-data scope, claim boundary and score reset | completed in T192--T222; formalized here | this goal plus T246 panel report |
| P0 | post-CI immutable release containing current receipts | completed as release-integrity handoff; DOI pending | `v0.1.3-r10.29`, overlay manifest, tag target and KAUST replay |
| P0 | non-author lockbox and no-author reproduction intake | open | signed third-party receipts only |
| P0 | two external adoption records | open | two distinct identity/COI/environment/output receipts |
| P1 | authenticated DOI deposit and read-back | open | DOI/archive service receipt |
| P0 | final multi-agent/editorial gate | blocked on P0 external receipts | new gate ledger with all predicates true |

## T248 release handoff update

The latest paper-data evidence is now bound to immutable tag
`v0.1.3-r10.29` at commit
`2cecba46a5b51af6f8a00aaeec8a5294dc96313b`. Its overlay manifest is
`release/empirical_candidate_v0.1.3-r10.29/release_manifest.json` with SHA-256
`4d49bc2ff6be959cd0c09495682b2571e6263f3747d3f879847f4375f11a706a`.
The r10.29 handoff contains the PMC11328176 execution path and the exact
external work packages. This closes release-binding drift only; it does not
create a lockbox receipt, no-author reproduction, adoption record or DOI
read-back. The four external predicates and
`scientific_submission_ready` remain false.

## Non-negotiable negative findings

- Do not pool abundance scales across papers.
- Do not treat core facilities processing a common pooled aliquot as
  independent biological cohorts.
- Do not turn technical replicates into biological effective n.
- Do not use agent-generated, author-run, CI, GitHub or DOI-preparation files
  as substitutes for third-party receipts.
- Preserve the negative and source-specific OOD results in the manuscript.
