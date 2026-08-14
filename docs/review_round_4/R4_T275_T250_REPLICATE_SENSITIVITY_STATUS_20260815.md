# R4-T275: T250 technical-replicate sensitivity

## Purpose

T275 audits the public paper-derived T250 route after the primary T273 reanalysis exposed a technical-replicate weighting concern. It identifies duplicate source/batch/canonical-target groups and compares the original endpoint with a target-equalized endpoint obtained by collapsing those duplicate rows.

## Claim boundary

This is a post-fit endpoint sensitivity analysis. It does not refit the pre-registered model with replicate-aware weights, and it is not an independent validation. The result can quantify whether the observed endpoint is sensitive to the duplicate rows, but it cannot close the replicate-aware model-execution requirement by itself.

## Acceptance record

- `refit_status`: `NOT_REFIT`
- `scientific_submission_ready`: `false`
- expected duplicate scope: `PXD064962_UCD_EVENT`
- required outputs: `replicate_sensitivity.csv`, `duplicate_technical_replicate_groups.csv`, and the canonical JSON report

The execution found 112 duplicate technical-replicate groups and 112 extra rows, all in the UCD event source. For the two sequence models, target equalization changed the batch-mean Spearman endpoint by 0.0000 in three outer folds and +0.0055 in one outer fold; the corresponding MAE/RMSE sensitivity is reported in the CSV. Constant-prediction Spearman is retained as undefined, matching the T250 endpoint policy.

The T250 route remains source-conditional and analysis-only where redistribution rights are incomplete. The T273 biological-unit-primary route remains the primary author-side result. External lockbox evaluation, no-author reproduction, external adoption, and authenticated DOI read-back remain open gates.
