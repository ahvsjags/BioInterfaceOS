# T195 strict-common-target execution plan

## Objective

Run the same leakage-controlled portability workflow as T193 on the exact
nine-accession intersection frozen by T192. This makes the strict common-target
claim executable without allowing target availability or held-out outcomes to
select the model.

## Frozen contract

- Target set: the nine accessions in the T192 registry.
- Outer split: leave one laboratory anchor out.
- Inner selection: leave one measurement batch out within development anchors.
- Primary endpoint: source-local within-batch rank Spearman, aggregated across
  held-out measurement batches.
- Models: constant mean, full sequence ridge and composition-only ridge.
- Uncertainty: 2,000 measurement-batch cluster bootstrap resamples.
- Negative control: 256 within-development-batch target permutations with the
  observed nested alpha held fixed.
- Cross-source abundance-scale pooling: prohibited.

## Acceptance

The run must produce a row-traceable ledger, predictions, batch and outer-fold
metrics, nested selections, paired ablation, permutation null, model
parameters, report and receipt. The receipt must retain exploratory evidence
semantics and `scientific_submission_ready=false`.

## Boundary

T195 does not turn laboratory anchors into donor-level independent cohorts. It
does not replace a non-author protected evaluator, an external scientific
reproduction, an external adoption record or a DOI archive receipt.
