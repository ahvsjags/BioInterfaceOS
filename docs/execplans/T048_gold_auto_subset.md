# T048: Build audited Gold-auto subset

## Purpose

Select an auditable Gold-auto subset from Silver using dual-extraction agreement, evidence resolution, confidence, and plausibility-QC gates while retaining reverse-trace provenance.

## Preconditions

T038 and T047 are DONE. Dual-path consensus, evidence resolution, Silver tables, and quarantine outputs are available.

## Non-goals

This task will not self-label expert gold, admit disagreement fields, bypass unresolved evidence, or repair values during subset selection.

## Interfaces and invariants

Every Gold-auto row must have deterministic inclusion criteria, a source record, evidence locators, consensus status, and a reverse-trace reference. Disagreements, low-confidence fields, unresolved locators, and critical-QC rows remain in Silver/review queues.

## Implementation plan

1. Inspect dual-path consensus, evidence table/conflict graph, Silver tables, and QC quarantine.
2. Define explicit Gold-auto admission thresholds and exclusion reasons.
3. Build a deterministic subset manifest and agreement report.
4. Verify primary keys, reverse tracing, and no expert-gold contamination.
5. Add biointerfaceos data build-gold-auto and focused tests.
6. Run the full acceptance gates and append evidence to the task ledger.

## Validation

- UV_OFFLINE=1 uv lock --check
- UV_OFFLINE=1 uv sync --frozen --python 3.11
- UV_OFFLINE=1 make check
- biointerfaceos data build-gold-auto --fixture
- biointerfaceos evidence trace --fixture
- biointerfaceos data validate silver --fixture
- biointerfaceos state validate
- git diff --check
- agreement, confidence, reverse-trace, exclusion, and expert-gold separation assertions

## Failure recovery

Keep excluded rows in Silver and retain explicit exclusion reasons. Do not promote disagreement or unresolved-evidence rows by default.

## Outputs

Gold-auto manifest, agreement report, exclusion queue, fixture/tests, CLI integration, this ExecPlan, state advancement, and task-ledger evidence.
