# R4-T277 T250 replicate-aware refit status

Date: 2026-08-15  
Audit: `bioif-r4-t277-t250-replicate-aware-refit-v1.0.0`  
Evidence class: `DEVELOPMENT_OBSERVATION`  
Claim level: `EXPLORATORY`

## Result

T277 completed a strict four-laboratory held-out refit of T250 after collapsing
technical replicate rows before the outer split, nested alpha selection, model
fit, and negative-control permutation. The input contains 783 raw positive
target observations, 112 duplicate technical-replicate groups, and 671
collapsed fit observations across 115 measurement batches and seven targets.

| held-out laboratory/source anchor | batches | fit observations | full ridge Spearman | selection-aware null p |
|---|---:|---:|---:|---:|
| Dalian University of Technology | 6 | 40 | 0.9262 | 0.0117 |
| University College Dublin / Conway Institute | 30 | 132 | 0.6920 | 0.0623 |
| University of Edinburgh | 49 | 306 | 0.6845 | 0.0272 |
| University of Southern Denmark / Russian Academy of Sciences | 30 | 193 | 0.7662 | 0.0195 |

The composition-only model has exactly the same Spearman score in all four
outer folds; paired full-minus-composition Spearman is therefore 0.0000 in
each fold. The negative control re-runs grouped nested alpha selection for
each of its 256 within-development measurement-batch permutations. The
selected alpha is not fixed under the null: all four folds use multiple alpha
values across the resamples.

The local and KAUST runs were byte-identical for all 11 canonical artifacts.
The cross-environment receipt is
`docs/review_round_4/R4_T277_CROSS_ENVIRONMENT_REPRODUCIBILITY_RECEIPT_20260815.json`;
the report SHA-256 is
`4fb6353f4cd23d51dc1795789ab6dc8039e0938a2948f22737bc25ec90a9f019`.

## Interpretation boundary

This is a reproducible author-side analysis of compatible quantitative values
extracted from published full-text/supplementary sources. It is not an
independent evaluator lockbox, an external no-author reproduction, or evidence
of donor-level effective sample size. Because the four-source common target
intersection and feature table were assembled before T277, the result remains
an exploratory portability refit and does not set
`scientific_submission_ready=true`.

## Reproduction commands

```powershell
.\.venv\Scripts\python.exe scripts\run_r4_t277_t250_replicate_aware_refit.py
.\.venv\Scripts\python.exe scripts\verify_r4_t277_t250_replicate_aware_refit.py
```

The canonical artifacts are under
`reports/review_round_4/t277_t250_replicate_aware_refit/v1.0.0/`; raw and
licensed analysis outputs remain outside the public source commit.
