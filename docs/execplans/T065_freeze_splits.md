# T065 Freeze development train and validation splits

## Purpose

Freeze a deterministic development split manifest from canonical group keys, official dates, evidence availability, and duplicate audits. The manifest must keep paper families/projects/formulation duplicates together and preserve a feature blacklist that blocks identity leakage.

## Preconditions

T063 group keys, T064 duplicate clusters/cross-split audit, T015 lockbox firewall, and official source/date metadata are complete. Any unresolved collision or cross-split duplicate remains a blocker rather than being silently reassigned.

## Non-goals

This task will not inspect locked payloads, tune splits on outcomes, use paper/accession/author/layout/path features, or force underpowered groups into train/validation.

## Interfaces and invariants

Each row records study/paper/project/material/bioenvironment/date groups, split assignment, eligibility reason, evidence locator, and source/date hash. Development train dates are no later than 2023-12-31; validation dates are in 2024 in the fixture. Group constraints and duplicate clusters are hard constraints. Feature blacklist and split manifest hashes are frozen before downstream benchmark work.

## Implementation plan

1. Hash and load T063 group keys, T064 duplicate/collision audits, Silver dates, and lockbox policy metadata.
2. Define a sanitized split fixture with train/validation candidates, excluded later dates, unresolved collisions, and identity-like feature columns.
3. Apply date rule, group constraints, duplicate exclusion, and evidence availability without using outcomes.
4. Emit frozen split manifest, feature blacklist, exclusion ledger, leakage audit, deterministic receipt/log/manifest, tests, evidence, and state advancement.
5. Add `biointerfaceos split freeze-dev --fixture`.

## Validation

- `UV_OFFLINE=1 uv lock --check`
- `UV_OFFLINE=1 uv sync --frozen --python 3.11`
- `UV_OFFLINE=1 make check`
- `biointerfaceos split freeze-dev --fixture`
- train/validation date, group containment, duplicate, and feature-blacklist assertions
- no lockbox access, no outcome leakage, and reproducible split hash
- assets, catalog, lockbox, release, state, compileall, and diff gates

## Failure recovery

If a group has unresolved identity/date evidence, exclude it from the primary split and retain a review row. If any paper family/project/duplicate cluster crosses split, invalidate the candidate manifest and rebuild with a broader group.

## Outputs

Frozen development split manifest, feature blacklist, exclusion/leakage audit, deterministic receipts/logs/manifests, focused tests, this ExecPlan, evidence report, and task-ledger/state advancement.
