# T045: Implement physical and statistical plausibility checks

## Purpose

Run deterministic plausibility QC over normalized experiment records, flagging impossible fractions/signs/units, duplicate sample counts, SEM/SD confusion candidates, range anomalies, and injected errors while measuring false positives.

## Preconditions

T040, T041, T043, and T044 are DONE. Normalized units, material/formulation, protocol, and endpoint records are available.

## Non-goals

This task will not silently correct source values, reinterpret ambiguous error bars, or treat a warning as an accepted scientific result.

## Interfaces and invariants

Each QC flag retains record/field identity, severity, rule ID, observed value, threshold or rationale, and source locator. Critical errors are quarantined; noncritical warnings carry a weight. Injected-error fixtures are separated from clean controls so false-positive rates are measurable.

## Implementation plan

1. Define QC rule, flag, severity, quarantine, and false-positive metric schemas.
2. Build clean and injected-error fixtures covering fraction/sign/unit/range/duplicate/SEM-SD anomalies.
3. Implement deterministic physical and statistical checks with explicit thresholds.
4. Emit critical quarantine and noncritical warning outputs without modifying raw values.
5. Measure injected-error recall and clean-control false positives.
6. Add biointerfaceos qc records --fixture --strict, focused tests, and full acceptance gates.

## Progress

- [ ] Define QC schemas and rule registry.
- [ ] Implement physical/statistical checks and severity handling.
- [ ] Measure injected-error recall and false positives.
- [ ] Run acceptance gates and record completion evidence.

## Validation

- UV_OFFLINE=1 uv lock --check
- UV_OFFLINE=1 uv sync --frozen --python 3.11
- UV_OFFLINE=1 make check
- biointerfaceos qc records --fixture --strict
- biointerfaceos assets verify
- biointerfaceos lockbox self-test
- biointerfaceos state validate
- git diff --check
- injected-error recall, clean-control false positives, critical quarantine, and warning-weight assertions

## Failure recovery

Preserve raw values and evidence locators. Quarantine critical records; keep noncritical warnings separate and never rewrite normalized source values.

## Outputs

QC rules, flags, quarantine records, false-positive metrics, fixtures/tests, CLI integration, this ExecPlan, state advancement, and task-ledger evidence.
