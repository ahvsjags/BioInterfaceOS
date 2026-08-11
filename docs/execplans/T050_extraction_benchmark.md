# T050: Run extraction benchmark and error analysis

## Purpose

Measure extraction quality, calibration, and error taxonomy across the committed fixture modalities and report whether the G2 automatic-field threshold is met.

## Preconditions

T048 and T049 are DONE. Gold-auto admission criteria, exclusions, review packets, and consensus evidence are available.

## Non-goals

This task will not claim expert validation without signed review imports, use locked-test payloads, or tune thresholds on the evaluation rows.

## Interfaces and invariants

Metrics are computed from explicit expected-vs-predicted fixture rows with modality/material/year strata, confidence calibration, numeric/entity/arm/evidence error taxonomy, and a model card. Every error retains a source locator and reason. G2 status is explicit and gates automatic-field use.

## Implementation plan

1. Define benchmark fixtures and a versioned expected-answer schema.
2. Compute numeric, entity, arm, evidence, agreement, recall, precision, and calibration metrics by stratum.
3. Emit an error taxonomy and model card with G2 pass/fail decision.
4. Add biointerfaceos benchmark extraction and focused tests.
5. Run full acceptance gates and append evidence to the task ledger.

## Validation

- UV_OFFLINE=1 uv lock --check
- UV_OFFLINE=1 uv sync --frozen --python 3.11
- UV_OFFLINE=1 make check
- biointerfaceos benchmark extraction
- biointerfaceos review export --sample stratified
- biointerfaceos data validate gold-auto --fixture
- biointerfaceos state validate
- git diff --check
- metric, calibration, taxonomy, stratum, and G2 assertions

## Failure recovery

Narrow automatic fields or increase review when G2 fails. Preserve benchmark rows and all error explanations; do not promote low-confidence predictions.

## Outputs

Benchmark metrics, calibration report, error taxonomy, model card, fixture/tests, CLI integration, this ExecPlan, state advancement, and task-ledger evidence.

## Completion evidence

T050 completed on 2026-08-12 in `/ibex/user/xup0a/BioInterfaceOS`. The implementation commit is `d538457`. The fixture contains 8 rows across numeric, entity, arm, and evidence modalities; 4 rows are correct and 4 are intentional errors. The automatic threshold is 0.85, yielding 4 eligible rows, precision 1.0, recall 1.0, calibration error 0.055, and G2 `PASS`.

The full offline gate passed with 194 tests, immutable release verification, asset and catalog checks, lockbox self-test, state validation, compileall, 23 append-only ledger validations, and `git diff --check`. The evidence record is sequence 46 in `reports/task_ledger.jsonl`; T051 is now the active task.
