# T121: Freeze estimands, independent units and empirical analysis plan

## Purpose

Turn the admitted real-data registry into a pre-analysis contract that prevents outcome-driven changes to units, splits, models, uncertainty reporting and missing-data handling.

## Preconditions

T120 is complete. The current registry contains one real, open development study with 14 released GUV-level observations and explicit source lineage.

## Non-goals

Do not fit a predictive or causal model, calculate an outcome effect, declare a confirmatory result, or unlock benchmark/model/lockbox claims.

## Interfaces and invariants

- New command required by the task graph: `python -m biointerfaceos stats validate-plan --strict`.
- Plan must define primary independent unit, estimand, minimum effective sample size, grouping rules, split design, model-selection nesting, uncertainty intervals, multiplicity, missingness, exclusions and claim boundary.
- The one-study source must be marked as development-only; any external/held-out group is unavailable rather than fabricated.
- Frozen plan artifacts must be immutable and carry `DEVELOPMENT_OBSERVATION` / `EXPLORATORY` metadata.

## Implementation plan

1. Inspect the empirical registry fields and identify the GUV as the sole currently available independent unit.
2. Create a versioned estimand registry and analysis plan with explicit “not estimable yet” entries for cross-study and external-validation quantities.
3. Add a strict validator that rejects outcome values, model performance, undeclared unit changes, missing policies, result wording and attempts to designate the development study as held out.
4. Add tests for the pass case and negative mutations; produce an immutable planning receipt.
5. On acceptance, unlock only T122; do not alter the scientific submission boundary.

## Progress

- [x] 2026-08-12 — Inspected T120 coverage: one study, one laboratory and 14 source-local GUV units; no held-out study exists.
- [x] 2026-08-12 — Wrote the versioned plan with source-local descriptive scope and explicit unavailable study-held-out transport estimand.
- [x] 2026-08-12 — Implemented `EmpiricalAnalysisPlanWorkflow`, strict CLI, immutable receipt and positive/negative tests.
- [x] 2026-08-12 — Validated on KAUST with format, lint, typing, five focused tests and isolated command execution.

## Discoveries

- A single real study can support source-local unit definition and planning, but cannot support study-held-out selection, cluster-aware intervals or external evaluation. The plan therefore encodes these as unavailable, not zero or passing values.

## Decisions

- Preserve the released GUV as the primary unit and retain study as the grouping key for every later cross-study procedure.
- Freeze a Holm family, no-imputation rule, nested group-CV design and study-clustered interval protocol now; their execution is prohibited until the stated minimum study coverage is met.

## Validation

- `python -m biointerfaceos stats validate-plan --strict` must pass without accessing any model-result artifact.
- Focused tests demonstrate rejection of an outcome/performance field before schema validation can hide the evidence-boundary violation.
- The isolated public-release audit remains `PASS_PUBLIC_RELEASE_AUDIT`; plan and empirical records are controlled and excluded from the public software replay.

## Failure recovery

Keep the task in planning scope if the present source cannot support a required quantity. Declare it unavailable; never derive a result from fixtures or invented groups.

## Outputs

- `data/empirical/R2_ANALYSIS_PLAN.json` and `docs/data/R2_EMPIRICAL_ANALYSIS_PLAN.md`.
- `src/biointerfaceos/empirical_analysis_plan_workflow.py`, CLI, tests and the immutable planning receipt.

## Completion note

T121 is complete. Its receipt declares `outcome_analysis_run=false`, `model_fitted=false`, `independent_validation=false` and `scientific_submission_ready=false`. T122 may now acquire additional independent real studies and construct a held-out benchmark, but no empirical performance claim is yet available.
