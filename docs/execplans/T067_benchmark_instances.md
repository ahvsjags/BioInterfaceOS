# T067 Build BioInterfaceBench task instances

## Purpose

Build development-only BioInterfaceBench task instances from validated Silver, corona, modality-link, and frozen split artifacts. Every instance must separate public inputs from hidden targets, attach group keys, preserve missingness, and validate the eight declared task families.

## Preconditions

T048 Gold-auto subset, T056 corona modules, T062 modality links, and T065/T066 split/audit artifacts are complete and approved. Hidden target semantics remain outside the public instance layer.

## Non-goals

This task will not train models, expose hidden targets, change split assignments, or create instances from locked payloads. Underpowered tasks remain pilot/excluded with explicit reasons.

## Interfaces and invariants

Each instance records task ID/family, public input fields, hidden-target reference/hash, split, group keys, evidence locator, missingness, and schema version. Public inputs cannot contain target fields or hidden target bytes. Minimum size/missingness decisions are explicit for E1/C1/U1/S1/B1/CF1/D1/A1.

## Implementation plan

1. Hash and load T048 Gold-auto, T056 modules, T062 links, and T065 frozen split/audit inputs.
2. Define sanitized task fixtures for eight task families with public/hidden separation and group keys.
3. Validate schema, target isolation, group attachment, split membership, and task-size/missingness gates.
4. Emit public instance files, hidden target registry, coverage/eligibility audit, deterministic receipt/log/manifest, tests, evidence, and state advancement.
5. Add `biointerfaceos benchmark build --dev --fixture`.

## Validation

- `UV_OFFLINE=1 uv lock --check`
- `UV_OFFLINE=1 uv sync --frozen --python 3.11`
- `UV_OFFLINE=1 make check`
- `biointerfaceos benchmark build --dev --fixture`
- eight task-family schema and target-isolation assertions
- group-key/split/missingness/size audit and no locked-payload access
- assets, catalog, lockbox, release, state, compileall, and diff gates

## Failure recovery

If an instance is underpowered or leaks a target field, exclude it from the primary benchmark and preserve the audit row. Never repair leakage by modifying hidden targets or split labels.

## Outputs

Public benchmark instances, hidden target registry, coverage/eligibility audit, deterministic receipts/logs/manifests, focused tests, this ExecPlan, evidence report, and task-ledger/state advancement.
