# R4-T285 post-T284 multi-agent editorial review

This is an evidence-bound five-role panel generated after T284. It is a structured editorial simulation, not a claim that five real external people reviewed the manuscript.

## Panel

| Role | Main question |
|---|---|
| EIC | Is the claim level and evidence package suitable for a strong-Q1 computational-biology submission? |
| Methodology reviewer | Are estimand, nested selection, cluster uncertainty, missingness, ablation and null controls coherent? |
| Domain reviewer | Do the published cohorts support biological interpretation without overclaiming donor or laboratory independence? |
| Open-science/reproducibility reviewer | Are rights, hashes, release, installation and adoption evidence independently verifiable? |
| Devil's advocate | Could route selection, leakage, favorable-fold reporting or evidentiary relabeling explain the apparent result? |

## Role conclusions

### EIC

T195/T282 is now a defensible primary paper-data route, and T284 makes the heterogeneous paper-OOD record visible. The paper is a credible auditable methods/resource submission with exploratory portability evidence. It is not yet a strong-Q1 validated biological predictor because the independent lockbox, no-author reproduction, adoption and DOI gates remain empty. **Decision: Major Revision.**

### Methodology reviewer

The statistical spine is strong: frozen targets, laboratory-held-out outer folds, nested selection, batch/biological-unit accounting, pre-model technical-replicate collapse, cluster bootstrap, paired ablation and selection-aware negative controls are tied to receipts. The remaining methodological publication risk is external execution, not an unrecorded formula. **Score: 92–94.**

### Domain reviewer

T282 reports 3 laboratory anchors and 9 targets, but Dalian is pooled/unspecified, Edinburgh donor IDs are not represented in the current map, and UCD technical replicates are not biological units. T284 includes both positive and negative paper-derived cohorts. The correct claim is source-conditional portability, not a universal protein-corona law or mechanism. **Score: 90–92 for data foundation; biological discovery claim not supported.**

### Open-science/reproducibility reviewer

The redistributable T195 route, row-level maps, licenses and cross-environment hashes are strong. T282/T284 are reproducible author-side executions. The handoff protocol is ready, but a request is not an evaluator receipt: no independent lockbox, no-author execution, external adoption record or authenticated DOI read-back is present. **Score: 64 for external reproducibility/adoption readiness.**

### Devil's advocate

T284 reduces selective-reporting risk by retaining three positive, three negative and three near-zero effects. The primary route is frozen and sensitivity routes are separated. However, all execution remains author-controlled, and sequence-feature increments are zero in all T282 primary folds. Calling the paper externally validated, independently replicated or sequence-mechanistically explanatory would remain unsupported. **Critical issue: external identity and independence.**

## Evidence-bound scorecard

| Module | Score / 100 | Evidence judgement |
|---|---:|---|
| Data compatibility and sample foundation | **92** | Three anchored laboratories, nine frozen targets, 809 raw observations, 644 pre-model units after 165 replicate-group collapses, row-level provenance and explicit rights. Biological-unit limits remain. |
| Statistical analysis design | **92** | Estimand, target timing, nested selection, cluster uncertainty, missingness/coverage rules and selection-aware null are frozen. |
| Statistical execution and effective sample | **94** | T195/T265/T277/T282 execute models, denominators, intervals, ablations and negative controls; local/KAUST T282 artifact hashes match. |
| Models, ablation, OOD and uncertainty | **88** | T284 binds six paper-OOD routes plus three T282 folds; positive, negative and near-zero effects are retained. The sequence increment is heterogeneous and all runs are author-side. |
| Independent lockbox evaluation | **0** | No genuine non-author protected-input evaluator receipt. |
| No-author scientific reproduction | **0** | No raw-input-to-result run by a team without author execution assistance. |
| External user adoption | **0** | No two distinct, independently audited real downstream uses. |
| DOI/version citability | **10** | Release and archive preparation exist, but authenticated DOI/archive read-back is absent. |

Descriptive arithmetic mean: **45.75/100**. This is not averaged into a false readiness claim; the hard gates dominate.

## Editorial decision and remaining P0 gates

**Major Revision / not yet strong-Q1 submission-ready.** The valid current positioning is an auditable computational-biology methods/resource paper with exploratory, source-conditional published-data evidence.

The following must be verified before the final PASS review:

1. One non-author protected lockbox receipt with identity, COI, input hash, immutable release, environment, command, output hash and signature/timestamp.
2. One no-author scientific reproduction from raw public-input reacquisition through result, including deviations and failure logs.
3. Two distinct external installation/use receipts for real downstream tasks.
4. Authenticated DOI/API read-back of the exact release, archive bytes and manifest.
5. Final manuscript/figures/tables bound to T195/T282/T284 without route switching or favorable-fold selection.

All four external gate predicates and `scientific_submission_ready` remain `false`.

