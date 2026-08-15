# R4-T290 paper-OOD estimand and uncertainty correction

T290 supersedes the metric labeling and uncertainty summary used by T284 for the six paper-derived OOD routes. It recomputes Spearman's rho with tie-aware average ranks, uses the source-native cluster unit for each route, and reports paired full-versus-composition deltas with a 2,000-resample percentile cluster bootstrap. It does not pool routes or change the T195/T282 primary analysis.

## Corrected route-level results

| Route | Estimand | Cluster unit | Clusters | Full mean | Composition mean | Paired delta (95% CI) | Status |
|---|---|---|---:|---:|---:|---:|---|
| T203 / PMC10257194 | mean batch Spearman | measurement batch | 45 | 0.1773 | 0.1532 | +0.0241 (0.0202, 0.0284) | supported positive |
| T159 / small-molecule corona | mean batch Spearman | measurement batch | 134 | 0.4002 | 0.4049 | −0.0047 (−0.0100, 0.0006) | indeterminate |
| T209 / Manchester | subject-equal mean Spearman | biological unit | 60 | 0.2933 | 0.3524 | −0.0591 (−0.0769, −0.0420) | supported negative |
| T181 / PXD017052 | subject-equal mean Spearman | biological unit | 141 | 0.0734 | 0.0400 | +0.0334 (0.0287, 0.0382) | supported positive |
| T176 / PXD068107 | mean batch Spearman | measurement batch | 21 | 0.1786 | 0.1999 | −0.0213 (−0.0389, −0.0035) | supported negative |
| T177 / PMC13106918 | mean batch Spearman | measurement batch | 16 | 0.0240 | −0.0296 | +0.0536 (0.0210, 0.0863) | supported positive |

The corrected suite has three positive, two negative and one indeterminate route-level deltas. The change from T284 is primarily inferential: subject-equal routes are no longer mislabeled as batch-equal, and paired uncertainty is explicit. Route heterogeneity remains the result; no universal sequence-feature increment is supported.

## Evidence boundary

These are public-paper/full-text or supplementary-data derived, author-controlled analyses. They are useful for transparent stress testing and claim calibration, but they are not a non-author lockbox receipt, a no-author reproduction, target-held-out generalization, or external adoption. `scientific_submission_ready` remains `false` until the independent gates are populated.

## Current score impact

T290 closes the T284 estimand-labeling and paired-delta reporting defects. The models/OOD/uncertainty module is raised conservatively from 88 to **89/100**. It remains below 90 because every paper-OOD execution is author-run and no protected-input non-author receipt exists.

| Module | Score |
|---|---:|
| Data compatibility and sample foundation | 92 |
| Statistical analysis design | 92 |
| Statistical execution and effective sample | 94 |
| Models, ablation, OOD and uncertainty | 89 |
| Independent lockbox evaluation | 0 |
| No-author scientific reproduction | 0 |
| External user adoption | 0 |
| DOI/version citability | 10 |

Descriptive arithmetic mean: **47.125/100**. The mean is intentionally not treated as a submission gate; the zero-valued independence/adoption gates remain decisive.

## Reproducibility artifacts

- Protocol: `docs/data/R4_T290_PAPER_OOD_UNCERTAINTY_PROTOCOL_20260815.json`.
- Code: `src/biointerfaceos/r4_t290_paper_ood_uncertainty.py`.
- Route table: `reports/review_round_4/t290_paper_ood_uncertainty/v1.0.0/route_specific_paired_uncertainty.csv`.
- Report and receipt: `reports/review_round_4/t290_paper_ood_uncertainty/v1.0.0/`.
- Strict commands: `biointerfaceos data evaluate-r4-t290-paper-ood-uncertainty --strict` and `biointerfaceos data verify-r4-t290-paper-ood-uncertainty --strict`.

