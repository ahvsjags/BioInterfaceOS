# R4-T200 statistical closure

T200 closes the reporting gaps identified by the multi-agent statistical review
without refitting a model or changing the frozen T197/T198 inputs.

## Completed

- T197 has a deterministic 2,000-resample measurement-batch cluster interval for every outer-fold/model/metric combination. Constant-prediction Spearman remains explicitly undefined.
- The estimand contract names the analysis population, independent unit, prediction row, primary aggregation, primary contrast, secondary metrics and claim boundary for T197 and T198.
- The T197 three-fold negative-control family is reported with Holm step-down adjusted values. All fold/model/threshold/secondary results remain descriptive and exploratory.
- T198 missingness is stratified by biological unit, clinical group and particle, with positive, `AUTHOR_NA`, explicit-zero, batch qualification and threshold-retention counts.
- The T198 threshold grid remains a descriptive sensitivity; threshold 10 is the only predeclared primary setting and no threshold is presented as confirmatory.

## Receipt

```text
R4_T200_STATISTICAL_CLOSURE_VERIFY_VALID
t197_fold_intervals=27
t198_strata=148
t198_threshold_strata=1184
estimand_frozen=true
multiplicity_policy_frozen=true
missingness_stratified=true
scientific_submission_ready=false
```

Machine-readable artifacts are in
`reports/review_round_4/t200_statistical_closure/v1.0.0/` and the CLI entry
points are:

- `biointerfaceos data evaluate-r4-t200-statistical-closure --strict`
- `biointerfaceos data verify-r4-t200-statistical-closure --strict`

This closes statistical reporting completeness for the paper-attached
exploratory analyses. It does not create independent biological validation, a
protected lockbox receipt, a no-author reproduction, external adoption, DOI
archival evidence or scientific submission readiness.
