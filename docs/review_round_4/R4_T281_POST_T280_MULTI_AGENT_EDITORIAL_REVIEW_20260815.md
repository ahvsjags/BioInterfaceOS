# R4-T281 post-T280 multi-agent editorial review — 2026-08-15

This is a new evidence-bound role panel, not a claim that five real people reviewed the manuscript. The panel applies the project evidence ledger and the reviewer rubric to the current paper-data route.

## Reviewer configuration

| Role | Review lens |
|---|---|
| EIC | Computational-biology journal fit, claim level and editorial readiness |
| Methodology reviewer | Study-held-out design, estimands, missingness, clustering, uncertainty and reproducibility |
| Domain reviewer | Proteomics/protein-corona biological meaning, sample lineage and target semantics |
| Cross-disciplinary reviewer | Open science, data rights, adoption and transferability |
| Devil's advocate | Leakage, route switching, cherry-picking, negative results and overclaiming |

## Independent role reports

### EIC

The T280 decision substantially improves the manuscript spine: T195 is a defensible redistributable primary route, while T265/T193/T277 are clearly separated sensitivities. The project is now credible as an auditable paper-data methods/resource study. It is not ready as a strong-Q1 biological-discovery paper because the evidence is still author-run and the external gates are empty. **Decision: Major Revision.**

### Methodology reviewer

The strongest part is the alignment between frozen target membership, leave-one-laboratory-anchor-out evaluation, nested batch selection, cluster bootstrap and within-batch permutation control. T195 provides the cleanest primary estimand, and T277 demonstrates pre-fit technical-replicate handling. The remaining major issue is not a missing statistical formula; it is the absence of a non-author execution that can test whether the protocol survives outside the author environment. **Methods score: 92/100.**

### Domain reviewer

The three source lineages are relevant published experimental proteomics data, and the rank endpoint avoids invalid cross-study abundance pooling. However, Dalian is pooled/unspecified, Edinburgh donor IDs are not encoded in the current map, and the T265 Manchester result is negative. The manuscript must present these as limits of biological interpretation, not as evidence of universal protein-corona behavior. **Domain evidence score: 78/100.**

### Cross-disciplinary reviewer

The source maps, licenses, hashes and external handoff contracts are unusually strong for a software/protocol paper. T195 should be the public primary route because its source packages are redistributable; non-redistributable T265 assets must remain analysis-only. Adoption is currently a request, not adoption: no independent installation, downstream task, issue/PR or citation is verified. **Open-science/adoption score: 64/100.**

### Devil's advocate

The main remaining failure mode is evidentiary relabeling. Choosing T195 after seeing that it has the clearest rights and stronger positive held-out values is acceptable only because the route decision is now frozen and T265/T193/T277 remain visible as prespecified sensitivities. It would be unacceptable to report only favorable T195 folds, to hide the zero ablation effect in T277, or to call paper-derived author runs “external validation.” **Critical issue: unresolved external independence.**

## Panel scorecard

| Module | Score | Evidence-based judgement |
|---|---:|---|
| Data compatibility and sample foundation | **90** | T195 supplies 3 anchored labs, 9 common targets, 809 row-traceable observations and CC-BY/CC0 redistribution boundaries; biological-unit caveats remain explicit. |
| Statistical analysis design | **92** | Frozen estimand, target timing, nested selection, cluster uncertainty, missingness and non-pooling rules are explicit. |
| Statistical execution and effective sample | **92** | T195/T265/T277 provide executed models, denominators, intervals, ablations and negative controls; effective n is not overclaimed. |
| Models, ablation, OOD and uncertainty | **84** | Multiple real model routes and uncertainty artifacts exist, but incremental sequence effects are often zero and T265 includes a negative Manchester OOD result; no non-author OOD exists. |
| Independent lockbox evaluation | **0** | No genuine non-author protected-input receipt. |
| No-author scientific reproduction | **0** | No genuine accession-to-result receipt performed without author assistance. |
| External user adoption | **0** | No two independently audited users or institutions. |
| DOI/version citability | **10** | Release/archive build exists; authenticated DOI read-back is absent. |

Arithmetic mean of these operational modules: **46.0/100**. This mean is intentionally not used as a substitute for the hard gates.

## Editorial decision

**Major Revision — promising methods/resource submission, not yet strong-Q1 submission-ready.**

T280 resolves the primary-route ambiguity and makes the paper-data claim substantially more defensible. It does not satisfy the objective's final state because all four external predicates remain false. The correct manuscript positioning is an auditable computational-biology methods/resource paper with exploratory published-data evidence, not a validated biological predictor.

## P0 closure sequence

1. Obtain one real protected lockbox evaluator receipt.
2. Obtain one no-author, raw-input reacquisition-to-result reproduction receipt.
3. Obtain two distinct external-user installation/use receipts.
4. Deposit the exact release to an archive and independently read back DOI, archive bytes and manifest hashes.
5. Run the final five-role review against the complete manuscript and all receipts; only then can `scientific_submission_ready` be reconsidered.

All gate fields remain `false` in the machine-readable decision record.
