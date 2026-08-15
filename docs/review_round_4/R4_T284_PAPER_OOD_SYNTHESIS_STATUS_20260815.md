# R4-T284 paper-derived OOD stress-suite status

T284 consolidates already frozen full-text/supplementary-data model outputs into a route-level stress suite. It does not refit or pool the studies, and it does not change the T195/T282 primary route. Every paper-derived row remains author-run analysis-only evidence.

## Route-level effects

| Route | Evidence class | Observations | Batches | Full Spearman | Composition Spearman | Full minus composition | Interpretation |
|---|---|---:|---:|---:|---:|---:|---|
| T203 / PMC10257194 | paper biological cohort | 4,362 | 45 | 0.1773 | 0.1532 | +0.0241 | positive exploratory |
| T159 / small-molecule corona | same-lineage paper cohort | 7,075 | 134 | 0.4002 | 0.4049 | -0.0047 | negative exploratory |
| T209 / Manchester | paper biological cohort | 4,150 | 288 | 0.2918 | 0.3514 | -0.0596 | negative boundary |
| T181 / PXD017052 | paper biological cohort | 17,026 | 666 | 0.0685 | 0.0392 | +0.0293 | small positive exploratory |
| T176 / PXD068107 | paper technical source | 1,976 | 21 | 0.1786 | 0.1999 | -0.0213 | negative technical stress |
| T177 / PMC13106918 | paper technical source | 418 | 16 | 0.0240 | -0.0296 | +0.0536 | technical stress; biological unit unresolved |
| T282 / Dalian holdout | primary three-lab holdout | 52 | 6 | 0.8302 | 0.8302 | 0.0000 | near-zero incremental effect |
| T282 / UCD holdout | primary three-lab holdout | 188 | 30 | 0.2534 | 0.2534 | 0.0000 | near-zero incremental effect |
| T282 / Edinburgh holdout | primary three-lab holdout | 404 | 49 | 0.4081 | 0.4081 | 0.0000 | near-zero incremental effect |

The suite contains 3 positive, 3 negative and 3 near-zero effects. This is a useful heterogeneity and claim-boundary result: the sequence model is not universally superior to composition-only features. No cross-route average is reported because the routes differ in laboratory lineage, target availability, biological-unit semantics and licensing.

## Current model/OOD editorial assessment

The model module is raised conservatively from 86 to **88/100** because T284 now binds the full/composition comparison, route-level uncertainty and both positive and negative stress results to hashed canonical inputs. It remains below 90 because all paper OOD runs are author-run, the incremental effect is heterogeneous, and no non-author protected-input OOD receipt exists.

The current evidence-bound operational scorecard is therefore:

| Module | Score |
|---|---:|
| Data compatibility and sample foundation | 92 |
| Statistical analysis design | 92 |
| Statistical execution and effective sample | 94 |
| Models, ablation, OOD and uncertainty | 88 |
| Independent lockbox evaluation | 0 |
| No-author scientific reproduction | 0 |
| External user adoption | 0 |
| DOI/version citability | 10 |

Descriptive arithmetic mean: **45.75/100**. The remaining 90+ gap is evidentiary, not a missing author-side rerun:

- one genuine non-author lockbox receipt;
- one no-author raw-input-to-result reproduction;
- two distinct external installation/use receipts;
- authenticated DOI/archive read-back;
- final five-role editorial review after those receipts.

## Canonical artifacts and claim boundary

- Protocol: `docs/data/R4_T284_PAPER_OOD_SYNTHESIS_PROTOCOL.json`.
- Effect table: `reports/review_round_4/t284_paper_ood_synthesis/v1.0.0/paper_ood_model_effects.csv`.
- Report and receipt: `reports/review_round_4/t284_paper_ood_synthesis/v1.0.0/`.
- CLI: `biointerfaceos data evaluate-r4-t284-paper-ood-synthesis --strict` and `verify-r4-t284-paper-ood-synthesis --strict`.

T284 is **not** independent validation, a lockbox, a no-author reproduction, or evidence of a biological mechanism. `scientific_submission_ready` remains `false`.

