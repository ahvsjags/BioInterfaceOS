# T099 Run mandatory model and data ablations

## Objective

Run the GOAL-mandated model and data ablation matrix across the frozen
BioInterfaceOS workflows, preserving the same budgets, splits, groups, leakage
controls, and uncertainty policies. Quantify which modules materially affect
supported claims and block any claim whose essential ablation is missing.

## Scope and constraints

- Use T078 calibrated uncertainty, T079 multimodal representations, T091 mediation,
  T093 symbolic laws, and T098 candidate audit packets as frozen inputs.
- Freeze the ablation matrix, primary metrics, paired comparison unit, split/group
  definitions, bootstrap budget, correction policy, and acceptable missing-data
  behavior before evaluation.
- Compare each full workflow with declared module removals or substitutions using
  the same development/held-out partitions and no retuning to ablation outcomes.
- Report paired effects, intervals, calibration/selective-risk changes, OOD and
  candidate-support changes, and explicit directionality; do not present a single
  p-value as ground truth.
- Keep all unsupported, failed, or insufficient ablations in an explicit ledger.
  Do not silently drop a missing ablation because it is inconvenient.
- Remain offline and fixture-backed: no network, credentials, raw download, locked
  payload, hidden targets, or post-hoc split changes.

## Planned implementation

1. Add `agents/robustness/ablations.v1.json` defining the full/ablated modules,
   metrics, paired units, intervals, leakage checks, and claim-blocking policy.
2. Add `tests/fixtures/robustness/ablations_fixture.json` with declared workflows,
   paired observations, uncertainty records, OOD groups, and missing-ablation cases.
3. Implement `src/biointerfaceos/ablation_workflow.py` with frozen split reuse,
   paired effects, bootstrap intervals, selective-risk/OOD summaries, and failure
   handling for unavailable ablations.
4. Expose `biointerfaceos robustness ablations --all` and emit the preregistered
   matrix, paired effect ledger, interval report, calibration/OOD summary,
   missingness/failure ledger, claim gate, lockbox scan, receipt, and manifest
   under `reports/robustness/ablations/`.
5. Add focused tests for same-split pairing, effect/interval reproducibility,
   leakage controls, missing-ablation blocking, and resume determinism.
6. Run focused tests and the complete lockfile, quality, data, release, state, and
   diff gates before recording T099.

## Acceptance criteria

- Every declared GOAL ablation runs under the same budget and splits, or is
  explicitly marked missing with its associated claim blocked.
- Paired effects and uncertainty intervals are reported for each available
  comparison; calibration, selective risk, and OOD sensitivity are included.
- No ablation reads held-out targets or changes candidate selection after seeing
  outcomes; all ledgers remain valid and reproducible.
- Full repository and immutable-release gates pass.

## Failure fallback

Block the associated claim/module when an essential ablation is unavailable or
leakage-controlled pairing fails. Preserve the full-model result as descriptive
only and narrow the supported claim set rather than lowering the ablation gate.
