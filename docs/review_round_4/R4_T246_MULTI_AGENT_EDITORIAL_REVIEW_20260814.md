# R4-T246 multi-agent editorial review

Date: 2026-08-14  
Review mode: role-separated evidence audit  
Consensus: `MAJOR_REVISION`  
`scientific_submission_ready`: `false`

This panel was rerun after the paper-data fallback routes, T194/T195 model
execution and T245 CI repair. It evaluates claims against frozen receipts and
does not treat the existence of a paper, a GitHub release or an author-run
analysis as independent validation.

## Agent A — data provenance and compatibility

Score: 88/100 under the strict rubric; 92/100 if the manuscript limits its
primary claim to technical/source-conditional portability.

The project now has a materially credible paper-data fallback: official
full-text/supplementary assets, source-cell maps, licenses and exact common
targets. T192/T195 provide three laboratory anchors and nine exact common
accessions; T194 provides 12 core-facility folds. The score remains below 90
for a biological-validation claim because Dalian is pooled/unspecified,
Edinburgh donor identifiers are not encoded in the current map, and UCD
replicate columns are technical. The correct editorial remedy is claim
reframing plus explicit strata, not relabeling.

## Agent B — statistical design

Score: 94/100.

The design is now close to publication-grade for an exploratory portability
paper: a pre-frozen target universe, a named primary estimand, study/source or
core-held-out folds, nested selection, cluster bootstrap, selection-aware
permutation controls, explicit missingness rules and a multiplicity ledger are
all present. Remaining deductions are for the small number of source anchors
and the fact that the biological and technical strata cannot be pooled into a
single confirmatory estimand.

## Agent C — statistical execution and effective sample size

Score: 91/100.

T193, T194 and T195 execute real model paths, paired composition ablations,
negative controls and uncertainty intervals. T198/T200 make the effective-n,
threshold and missingness accounting visible. The report must keep biological
unit counts distinct from measurement batches and source/core folds; otherwise
the score falls back below 90.

## Agent D — model, ablation and OOD evidence

Score: 89/100.

The evidence is no longer a fixture-only claim. There are positive and
negative paper-data OOD routes, full-versus-composition comparisons,
selection-aware nulls and cluster uncertainty. However, the most informative
OOD executions are author-run and source-conditional; T209 also contains a
negative paired delta. The paper should present this as a failure-boundary and
transportability result, not as universal biological generalization. One final
release-bound rerun and a claim-matrix audit are needed for a 90+ score.

## Agent E — reproducibility and independent evaluation

Internal software reproducibility: 91/100.  
Independent scientific evaluation: 12/100.

T245 shows local, KAUST and GitHub CI agreement, and the fixed release handoff
is structurally complete. That proves executable engineering. It does not
prove that an unrelated evaluator held unseen data or that an external team
obtained the same scientific conclusion. The evaluator and reproduction gates
remain false.

## Agent F — external adoption and editorial decision

External adoption: 46/100.  
Strict publication maturity: 58/100.

The repository, fixed release, intake package and GitHub coordination issues
are useful infrastructure, but author comments and public metadata are not
adoption receipts. A DOI preparation package is not an archived DOI. The
decision is Major Revision until one protected non-author lockbox receipt, one
no-author reproduction receipt, two distinct adoption receipts and one real
archive read-back receipt are independently verified.

## Consensus scorecard

| Module | Score | Verdict |
|---|---:|---|
| data compatibility and sample base | 88 | close for technical portability; not yet 90 for biological validation |
| statistical analysis design | 94 | pass internal target |
| statistical execution and effective n | 91 | pass internal target with unit-boundary wording |
| model, ablation, negative control and OOD | 89 | one release-bound rerun and claim audit needed |
| independent lockbox evaluation | 12 | hard fail; receipt absent |
| external scientific reproduction | 8 | hard fail; receipt absent |
| external user adoption | 46 | hard fail; verified users absent |
| DOI/immutable archive | 25 | hard fail; authenticated archive receipt absent |
| strict strong-Q1 maturity | 58 | Major Revision |

## Editorial recommendation

The work is now defensible as a paper-data-driven computational method and
technical cross-source portability study, provided the manuscript narrows its
claims and keeps all source-specific failures visible. It is not yet a strong
Q1 submission under the requested all-modules-at-least-90 rule.

The shortest valid route to the requested threshold is:

1. publish a new immutable release containing the current post-CI receipts and
   the T246 claim boundary;
2. obtain the four external evidence classes listed in T246; and
3. rerun the final panel after independent receipt verification.

No internal agent can legitimately manufacture steps 2 or 3.

