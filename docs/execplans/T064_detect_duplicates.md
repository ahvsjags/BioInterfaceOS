# T064 Detect formulation and semantic near-duplicates

## Purpose

Detect exact, composition, structure, and text near-duplicates among resolved materials/formulations, retaining ambiguous neighbors in a manual queue and preventing cross-split duplicates from being treated as independent observations.

## Preconditions

T041 material/formulation resolution and T063 canonical group keys are complete. Material entities, formulation fractions, structures, normalized text, paper-family keys, project keys, and split labels are frozen inputs for this audit.

## Non-goals

This task will not merge ambiguous trade names, use split labels to tune similarity thresholds, delete records, or freeze final train/validation splits.

## Interfaces and invariants

Every duplicate edge records method (`exact`, `composition`, `structure`, or `text`), threshold/version, input IDs, evidence, and review status. Exact and high-confidence composition/structure duplicates are clustered conservatively; semantic text neighbors remain reviewable. Thresholds are declared before scoring and cross-split duplicates are surfaced as blockers.

## Implementation plan

1. Hash and load T041 material registry, T063 group-key table, and a sanitized formulation/text fixture.
2. Freeze method-specific thresholds independent of split labels and inject exact, composition, structure, text, and ambiguous cases.
3. Compute pairwise duplicate edges with method provenance and cluster only safe edges.
4. Audit clusters against paper-family/project group keys and emit cross-split duplicate blockers.
5. Emit duplicate clusters, edge table, manual review queue, cross-split audit, deterministic receipt/log/manifest, tests, evidence, and state advancement.
6. Add `biointerfaceos split detect-duplicates --fixture`.

## Validation

- `UV_OFFLINE=1 uv lock --check`
- `UV_OFFLINE=1 uv sync --frozen --python 3.11`
- `UV_OFFLINE=1 make check`
- `biointerfaceos split detect-duplicates --fixture`
- exact/composition/structure/text edge and threshold assertions
- cross-split duplicate detection and no split-label threshold tuning
- assets, catalog, lockbox, release, state, compileall, and diff gates

## Failure recovery

If structure or semantic evidence is insufficient, keep the records separate and place the edge in manual review. If a high-confidence duplicate crosses split boundaries, block split freezing and broaden the group rather than dropping one record silently.

## Outputs

Duplicate clusters, duplicate-edge table, manual review queue, cross-split audit, deterministic receipts/logs/manifests, focused tests, this ExecPlan, evidence report, and task-ledger/state advancement.
