# T063 Create canonical group keys

## Purpose

Create deterministic group keys for study, laboratory, paper family, material/formulation, bioenvironment, and date strata. The keys will support later split construction while preventing the same paper family or project from crossing train/validation boundaries.

## Preconditions

T030 family/study identities, T041 material resolution, T043 protocol ontology, T047 Silver records, and T057 PRIDE project QC are complete. Existing access/restriction states and evidence locators remain authoritative.

## Non-goals

This task will not freeze train/validation splits, infer unknown laboratory identities, cluster materials by an unreviewed similarity threshold, or use outcome values to define groups.

## Interfaces and invariants

Each row records canonical keys plus source IDs and evidence locators. Unknown lab is represented conservatively as `LAB_UNKNOWN:<family-or-project>`; paper family and project keys are never null for admitted rows. Group keys are deterministic, collision-audited, and derived only from identity/material/protocol/date metadata.

## Implementation plan

1. Hash and load sanitized family, material, protocol, Silver, and PRIDE project inputs.
2. Define fixture records covering repeated paper families, same project, resolved/ambiguous materials, unknown labs, bioenvironment, and dates.
3. Canonicalize identifiers and form stable group keys with explicit unknown handling.
4. Run collision and same-family/project containment audits; preserve review rows instead of forcing merges.
5. Emit group-key table, collision audit, review queue, deterministic receipt/log/manifest, tests, evidence, and state/ledger advancement.
6. Add `biointerfaceos split build-groups --fixture`.

## Validation

- `UV_OFFLINE=1 uv lock --check`
- `UV_OFFLINE=1 uv sync --frozen --python 3.11`
- `UV_OFFLINE=1 make check`
- `biointerfaceos split build-groups --fixture`
- deterministic keys, same paper/project containment, unknown-lab conservatism, and collision assertions
- no outcome leakage and no split freeze in this task
- assets, catalog, lockbox, release, state, compileall, and diff gates

## Failure recovery

If identity or material resolution is ambiguous, retain the broadest safe group key and add a review row. Never split an uncertain family or project merely to increase row count.

## Outputs

Canonical group-key table, collision audit, review queue, deterministic receipts/logs/manifests, focused tests, this ExecPlan, evidence report, and task-ledger/state advancement.
