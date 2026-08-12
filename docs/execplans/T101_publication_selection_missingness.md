# T101 Assess publication selection and missingness bias

## Objective

Assess how publication selection, reporting missingness, and evidence-grade
availability could distort study effects and supported design claims. Compare
multiple plausible selection/missingness models and report assumption-sensitive
conclusions without treating p-value scraping as ground truth.

## Scope and constraints

- Use T047 study effects, T071 protocol/evidence metadata, T091 mediation,
  T093 symbolic laws, and T100 OOD/group-key outputs as frozen inputs.
- Freeze selection variables, missingness mechanisms, sensitivity weights, study
  clusters, evidence-grade strata, and estimands before model fitting.
- Compare at least complete-case, inverse-probability-weighted, pattern-mixture,
  and bounded selection-bias scenarios with the same study clusters and declared
  bootstrap budget.
- Keep publication date, sample size, significance, and evidence fields separate;
  do not scrape p-values as ground truth or tune thresholds to recover a desired
  conclusion.
- Preserve missing/ambiguous records and show how each plausible model changes
  effects, intervals, calibration, and claim language. Narrow claims when models
  disagree materially.
- Remain offline and fixture-backed: no network, credentials, raw download,
  locked payload, hidden targets, or post-hoc source inclusion.

## Planned implementation

1. Add `agents/robustness/bias.v1.json` defining selection/missingness variables,
   clustered estimands, sensitivity models, intervals, and claim gates.
2. Add `tests/fixtures/robustness/bias_fixture.json` with study effects, missing
   fields, evidence grades, sample sizes, selection indicators, and counterfactual
   sensitivity scenarios.
3. Implement `src/biointerfaceos/bias_workflow.py` with clustered complete-case,
   IPW, pattern-mixture, and bounded selection-bias comparisons plus missingness
   ledgers and assumption audits.
4. Expose `biointerfaceos robustness bias` and emit selection preregistration,
   missingness audit, model comparison, sensitivity intervals, claim gate,
   lockbox scan, receipt, and manifest under `reports/robustness/bias/`.
5. Add focused tests for cluster preservation, missingness mechanism coverage,
   model disagreement, p-value separation, and resume determinism.
6. Run focused tests and the complete lockfile, quality, data, release, state, and
   diff gates before recording T101.

## Acceptance criteria

- Multiple plausible selection/missingness models run on the same clustered data.
- Assumptions, effects, intervals, and model disagreement are reported explicitly.
- Missing/ambiguous records remain visible; no p-value scraping is presented as
  ground truth.
- Claim language is downgraded when selection/missingness sensitivity is material.
- Full repository and immutable-release gates pass.

## Failure fallback

Use the most conservative bounded selection-bias result, narrow applicability and
evidence wording, and retain unresolved missingness as an explicit limitation.
