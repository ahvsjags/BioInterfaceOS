# T049: Generate consensus and expert review packets

## Purpose

Export blinded, stratified review packets for disagreement, unresolved evidence, high-impact, and excluded fields while preserving exact candidate values and source locators.

## Preconditions

T048 is DONE. Gold-auto exclusions, consensus review, evidence review, and Silver tables are available.

## Non-goals

This task will not fabricate human sign-off, admit expert gold without a signed import, or expose locked-test payloads.

## Interfaces and invariants

Every packet has a stable packet ID, blinded context, exact question, candidate values, evidence locators, reason for review, annotation schema, and sign-off fields. Sampling is deterministic and stratified by reason/field.

## Implementation plan

1. Inspect Gold-auto exclusions, consensus/evidence review queues, and high-impact rows.
2. Define packet, annotation-guide, and signed-import schemas.
3. Generate deterministic stratified packets and a review coverage report.
4. Verify blinded context, locator completeness, no locked-test access, and no expert-gold promotion.
5. Add biointerfaceos review export --sample stratified and focused tests.
6. Run full acceptance gates and append evidence to the task ledger.

## Validation

- UV_OFFLINE=1 uv lock --check
- UV_OFFLINE=1 uv sync --frozen --python 3.11
- UV_OFFLINE=1 make check
- biointerfaceos review export --sample stratified
- biointerfaceos evidence trace --fixture
- biointerfaceos state validate
- git diff --check
- packet schema, stratification, blinding, locator, sign-off, and no-promotion assertions

## Failure recovery

Keep source rows in Silver/Gold-auto exclusions and regenerate packets deterministically. Do not create signed expert labels from unsigned files.

## Outputs

Review packets, annotation guide, sign-off schema, coverage report, fixture/tests, CLI integration, this ExecPlan, state advancement, and task-ledger evidence.
