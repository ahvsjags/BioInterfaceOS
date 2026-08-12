# T123: Real paired model runs, ablations and OOD evaluation

## Purpose

Use real, compatible, study-grouped benchmark data to determine whether any declared model or module effect survives paired ablations and out-of-distribution evaluation.

## Preconditions

T122 is complete, but its three study-held-out items are heterogeneous raw-cell locator tasks. They are not yet a compatible biological prediction target, and this limitation is a precondition rather than a result.

## Non-goals

Do not convert deterministic locator resolution into a causal or biological model, manufacture labels, reuse fixture runs, infer unavailable cohorts, or describe protocol completion as robustness or generalisation.

## Interfaces and invariants

- Required command: `python -m biointerfaceos model evaluate-real --strict`.
- Inputs must be a frozen compatible target, raw source-level predictions, paired full/ablated configurations, declared seeds, study-level OOD groups, negative controls and overlap/effective-n records.
- Any model output must retain `DEVELOPMENT_OBSERVATION` / `EXPLORATORY` status until an independent evaluator executes T124.
- No module effect is accepted without paired runs on identical source groups/seeds and explicit uncertainty.

## Implementation plan

1. Audit whether a common target with adequate effective n exists across the T122 sources.
2. If not, register the incompatibility and enlarge the raw-data registry before any model training.
3. Freeze compatible target, configurations, seeds, ablation matrix, external cohort definition and negative controls.
4. Run paired models only after the above freeze; retain raw predictions and group-level uncertainty.
5. Implement strict evaluator and failure tests, preserving unavailable states instead of backfilling fixture values.

## Progress

- [x] Compatibility and effective-n audit. The immutable strict gate found no
  compatible endpoint/unit across the three T122 study-held-out items; all
  candidate endpoint groups have one study, one laboratory and effective n=1.
- [x] Source-candidate expansion audit. Three openly licensed, raw table packages
  were checksum- and header-verified, but the declared DLS metrics are
  hydrodynamic mean, Z-average, and an unspecified statistic. They were not
  combined into a target.
- [x] Public-source discovery replay. A fresh, licence- and asset-level screening
  checked two 2024 records and reserved one post-freeze record without consuming
  it as development evidence. The 2024 Z-average workbook contains only
  Mean +/- SEM summaries and no matched biological-condition protocol; the
  other releases a figure index but no numerical DLS table.
- [ ] Compatible target freeze.
- [ ] Paired model/ablation/OOD execution.
- [ ] Strict receipt and negative-control audit.

## Discoveries

- The T122 source-locator benchmark must not be reused as a scientific model target.
- The first source-expansion batch reaches three distinct studies/laboratories,
  but it still lacks an identical source-declared size statistic. The B5 landing
  page also does not state an institutional laboratory affiliation; the Y5 DLS
  worksheet omits its biological condition; and DG3 publishes source-level mean
  ± SD rows rather than matched raw replicate rows.

## Decisions

- Do not fit a model or invent ablation/OOD outputs from the source-locator
  benchmark. T123 remains active until a compatible, pre-frozen cross-study
  target is admitted.
- Do not harmonize source labels by assumption. A shared `nm` unit does not
  convert "hydrodynamic mean", "Z-average", and an unspecified hydrodynamic
  statistic into one endpoint.
- Keep post-freeze source files outside the development scope. Their
  landing-page metadata is not converted into an external validation result.

## Validation

- Strict evaluation must reject heterogeneous targets, fixture payloads, mismatched seeds/groups, absent raw predictions, undeclared OOD cohorts and missing negative controls.
- 2026-08-12: `python -m biointerfaceos model evaluate-real --strict` audited
  three sources and three endpoint/unit groups, found zero compatible targets,
  and wrote the explicit blocked receipt without fitting a model.
- Regression: the compatibility gate tests cover strict-mode enforcement,
  current blocked-state accounting, and receipt-tamper rejection.
- 2026-08-12: `python -m biointerfaceos model audit-source-candidates --strict`
  checks the three source bundles and records the explicit non-admission
  decision in `reports/review_round_2/real_model_source_candidates/v1.1.0/`.
- 2026-08-12: `python -m biointerfaceos model audit-source-discovery --strict`
  records three newly screened public records in
  `reports/review_round_2/real_model_source_discovery/v1.0.0/`; it preserves
  zero admissions and does not retrieve the reserved lockbox content.

## Failure recovery

If a compatible real target cannot be assembled, record a blocked data-coverage state and return to source admission. Keep all effect/robustness/generalisation claims disabled.

## Outputs

- Compatibility report; frozen target/configuration/split manifests; paired predictions; ablations; OOD and negative-control audit; receipt.
- Current compatibility-only output:
  `reports/review_round_2/real_model_compatibility/v1.1.0/`.

## Completion note

Pending.
