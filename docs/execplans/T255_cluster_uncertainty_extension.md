# T255 cluster-aware uncertainty extension

Status: `IN_PROGRESS`

## Objective

Add a pre-registered uncertainty layer to the executed T238 four-source route.
The extension must reuse the frozen T238 batch-level predictions and must not
change target membership, model selection, primary estimands, or claim level.

## Frozen contract

- Input is the release-bound T238 `outer_fold_batch_metrics.csv` and its report.
- A cluster is one held-out `measurement_batch_id` within one outer fold and
  model. No donor-level independence is inferred.
- For each fold/model/metric, the estimand is the arithmetic mean of finite
  batch-level values.
- The uncertainty interval is a percentile 95% bootstrap over measurement
  batches, with 2,000 resamples and deterministic protocol seeds.
- Constant-model Spearman remains undefined; it receives no interval.
- The paired full-versus-composition interval is reused from the T238 frozen
  paired-ablation artifact and is not recomputed with a different estimand.

## Deliverables

- Frozen protocol and registry under `docs/data/`.
- Hash-bound report, receipt and metric-level CSV under
  `reports/review_round_4/t255_cluster_uncertainty/v1.0.0/`.
- CLI execute/verify commands and regression tests.

## Claim boundary

This is a cluster-aware uncertainty extension of an exploratory paper-derived
development analysis. It does not create donor-level effective n, independent
validation, a protected lockbox receipt, a no-author reproduction, adoption,
or `scientific_submission_ready`.
