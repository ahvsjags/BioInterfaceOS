# T051: Publish data coverage and missingness audit

## Purpose

Publish a reproducible coverage and missingness audit over the immutable Silver release and the search registry, using independent-unit counts and explicit bias warnings.

## Preconditions

T047, T050, and T029 are complete. The Silver release, extraction benchmark, and search registry are fixture-backed, hashed, and locally queryable.

## Non-goals

This task will not fabricate observations, pad missing groups with pseudo-replicates, or infer coverage from duplicated rows. It will not promote unreviewed Gold-auto fields into expert gold.

## Interfaces and invariants

The audit will report coverage by study, lab, material, species, endpoint, date, and evidence locator. Independent units will be counted from stable study/sample keys, missingness will remain explicit, and every warning will carry a traceable source or rule.

## Implementation plan

1. Define a versioned coverage fixture and independent-unit counting rules.
2. Build coverage tables and a missingness model from Silver plus the search registry.
3. Emit bias warnings and gap-prioritization outputs without imputing values.
4. Add `biointerfaceos report data-coverage` and focused tests.
5. Run the full offline gate, validate the frozen release, and append evidence.

## Validation

- `UV_OFFLINE=1 uv lock --check`
- `UV_OFFLINE=1 uv sync --frozen --python 3.11`
- `UV_OFFLINE=1 make check`
- `biointerfaceos report data-coverage`
- `biointerfaceos data validate silver --fixture`
- `biointerfaceos state validate`
- `git diff --check`
- independent-unit, missingness, bias-warning, and no-imputation assertions

## Failure recovery

Trigger targeted search or reduce scope when coverage is inadequate. Preserve the underlying rows and report missingness; never replace gaps with pseudo-replicates.

## Outputs

Coverage tables, missingness model, bias warnings, focused tests, this ExecPlan, state advancement, and task-ledger evidence.
