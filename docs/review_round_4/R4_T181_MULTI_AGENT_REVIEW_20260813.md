# T181 Multi-Agent Editorial Re-review — 2026-08-13

Three independent read-only agents reviewed the T180/T181 source audit, protocol, implementation, and execution receipt. Their role-specific conclusions converge on a bounded improvement, not a submission-readiness upgrade.

## Evidence accepted by all agents

- Supplementary Data 5 is a paper-attached matrix with 141 individual subjects, 5 NP-corona conditions, and a depleted-plasma control; the project ledger excludes the control from the NP-corona analysis.
- T180 is row-traceable: 705 subject-particle batches, 666 batches passing the predeclared 10-positive-target threshold, 34 uniquely mapped frozen-target proteins, 23,970 source cells, 17,330 positive cells, and 6,640 preserved `AUTHOR_NA` states.
- T181 fits only on the frozen R3 development population. The external cohort is not used for feature selection, alpha selection, or refitting.
- T181 scores 17,026 external observations across 666 qualified batches and 141 biological-unit clusters.
- Full sequence ridge has subject-equal mean Spearman `0.06845` with 95% cluster CI `[0.05253, 0.08293]`; composition-only has `0.03917` with `[0.02132, 0.05493]`; paired delta is `0.02928` with `[0.02413, 0.03451]`.
- Full model does not beat the constant baseline on MAE/RMSE: constant MAE/RMSE `0.26192/0.30238`; full `0.26543/0.30761`.
- The fixed-alpha development-batch permutation negative control has one-sided `p=0.24125`; it does not provide confirmatory evidence of a non-null signal.

## Role-specific findings

### Statistical methods reviewer

Nested alpha selection and biological-unit cluster bootstrap are implemented correctly for the declared exploratory estimands. The review flags three remaining statistical limitations: batch qualification may induce informative missingness; the number of qualified batches varies by subject (2–5); and the negative control fixes alpha rather than repeating the selection step, so it is not fully selection-aware. The reviewer recommends a clinical-group/particle-condition/missingness sensitivity analysis before any confirmatory claim.

### Computational biology/domain reviewer

The correct description is “same-laboratory biological-cohort OOD” or “subject-level effective-n evaluation.” The 141 subjects are biological units inside the Seer/Broad source; they are not 141 laboratories, not independent laboratory replication, and not a new lineage. The 34 proteins are a target intersection, not 34 independent mechanisms. Source-local rank prediction is compatible with a within-subject NP-corona ranking claim, but not with absolute abundance, material effect size, mechanism, clinical biomarker, or clinical utility claims.

### Editor / Devil’s Advocate

The evidence supports a small, exploratory paired advantage over composition-only, but the absolute correlation is low, the negative control is not supportive, and the full model is worse than the constant baseline on error metrics. The proper editorial verdict remains **Major Revision**. T180/T181 are not a protected lockbox evaluation, a non-author reproduction, external adoption evidence, or DOI-backed release evidence. Current worktree artifacts must be included in a public immutable release before they count as release-grade submission evidence.

## Conservative score update

| Module | Score | Editorial interpretation |
|---|---:|---|
| Data compatibility and sample basis | 84 | Strong row-level paper source and 141 biological units, but one laboratory anchor and only 34 target intersection proteins. |
| Statistical analysis design | 86 | Frozen source-local estimand, development-only nested selection, cluster-aware uncertainty, paired ablation, and negative control. |
| Statistical execution and effective n | 68 | Real execution with 17,026 observations and n=141 biological clusters; author-run and missingness qualification remain limitations. |
| Model, ablation, and OOD evidence | 52 | Real cohort OOD and positive paired delta, but low absolute correlation, non-supportive negative control, and no constant-baseline error win. |
| Protected independent lockbox | 4 | Structure and handoff exist; no real non-author evaluator receipt. |
| External scientific reproduction | 0 | No clean-checkout, no-author, end-to-end receipt. |
| External user adoption | 0 actual evidence | Public handoff readiness is not adoption. |
| DOI/release provenance | 30 | Public branch/tag infrastructure exists, but T180/T181 are not yet in an immutable release and DOI remains pending. |
| Strict strong-Q1 composite | 30 | Hard gates dominate; `scientific_submission_ready=false`. |

## Decision

T181 is a substantive improvement to the methods/software benchmark and makes the effective biological-unit accounting real. It does not justify a strong-Q1 biological-discovery or clinical-validation submission. The next gate-closing work is external and cannot be manufactured inside the author-controlled repository: a real protected lockbox receipt, a no-author end-to-end reproduction receipt, two or more independently verifiable adoption receipts, and an immutable DOI release containing T180/T181.

All flags remain:

```text
independent_validation=false
external_scientific_reproduction=false
scientific_submission_ready=false

## T182 release update

T180/T181 are now represented in the immutable `v0.1.3-r9.1` release and the R9 DOI handoff manifest. This raises release provenance but does not change the scientific scores or the editorial decision: the cohort is still author-run and same-laboratory, and the protected lockbox, no-author reproduction, adoption, and archival DOI receipts are still absent.
```
